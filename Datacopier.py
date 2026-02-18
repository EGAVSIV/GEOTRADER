import pandas as pd
import os, random, time, logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from tvDatafeed import TvDatafeed, Interval

# =====================================================
# CONFIG
# =====================================================
MAX_WORKERS = 2
BARS = 4000

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    filename="tv_skip_reasons.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# =====================================================
# BASE PATHS
# =====================================================
BASE_DIR = "market_data"

BUCKET_PATHS = {
    "broader_index": os.path.join(BASE_DIR, "broader_index"),
    "sector_index": os.path.join(BASE_DIR, "sector_index"),
    "fno": os.path.join(BASE_DIR, "fno"),
}

# =====================================================
# LOCAL FNO SOURCE FOLDERS
# =====================================================
LOCAL_FNO_PATHS = {
    "15m": "stock_data_15",
    "1H": "stock_data_1H",
    "D": "stock_data_D",
    "W": "stock_data_W",
    "M": "stock_data_M",
}

# =====================================================
# TIMEFRAMES
# =====================================================
TIMEFRAMES = {
    "15m": Interval.in_15_minute,
    "1H": Interval.in_1_hour,
    "D": Interval.in_daily,
    "W": Interval.in_weekly,
    "M": Interval.in_monthly,
}

# =====================================================
# ENSURE OUTPUT STRUCTURE
# =====================================================
for bucket, path in BUCKET_PATHS.items():
    for tf in TIMEFRAMES.keys():
        os.makedirs(os.path.join(path, tf), exist_ok=True)

# =====================================================
# BROADER & SECTOR LIST
# =====================================================
broader_index = [
    'NIFTY','BANKNIFTY','CNXMIDCAP','CNXSMALLCAP','CNX500',
    'CNXFINANCE','NIFTYJR','CNX100','NIFTY_TOP_10_EW'
]

sector_index = [
    'CNXREALTY','CNXPSUBANK','CNXMETAL','CNXIT','CNXSERVICE',
    'CNXPSE','CNXCONSUMPTION','CNXINFRA','CNXENERGY','CNXAUTO',
    'CNXFMCG','CNXPHARMA'
]

# =====================================================
# AUTO-DETECT FNO SYMBOLS FROM PARQUET FILES
# =====================================================
def get_fno_symbols():
    symbols = set()

    for folder in LOCAL_FNO_PATHS.values():
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.endswith(".parquet"):
                    symbols.add(file.replace(".parquet", ""))

    return list(symbols)

fno_symbols = get_fno_symbols()

# =====================================================
# SYMBOL BUCKET MAP
# =====================================================
SYMBOL_BUCKET = {}

for s in broader_index:
    SYMBOL_BUCKET[s] = "broader_index"

for s in sector_index:
    SYMBOL_BUCKET[s] = "sector_index"

for s in fno_symbols:
    SYMBOL_BUCKET[s] = "fno"

ALL_SYMBOLS = list(SYMBOL_BUCKET.keys())

# =====================================================
# INDICATORS
# =====================================================
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_bollinger(close, period=20, std=2):
    mid = close.rolling(period).mean()
    dev = close.rolling(period).std()
    upper = mid + std * dev
    lower = mid - std * dev
    width = (upper - lower) / mid
    return upper, mid, lower, width


def calc_cpr(df):
    prev = df.shift(1)
    pivot = (prev['high'] + prev['low'] + prev['close']) / 3
    bc = (prev['high'] + prev['low']) / 2
    tc = (pivot * 2) - bc
    width = (tc - bc) / pivot
    return pivot, bc, tc, width


def calc_camarilla(df):
    prev = df.shift(1)
    rng = prev['high'] - prev['low']
    h3 = prev['close'] + rng * 1.1 / 4
    h4 = prev['close'] + rng * 1.1 / 2
    l3 = prev['close'] - rng * 1.1 / 4
    l4 = prev['close'] - rng * 1.1 / 2
    return h3, h4, l3, l4

# =====================================================
# WORKER FUNCTION
# =====================================================
def process_symbol(symbol):

    bucket = SYMBOL_BUCKET[symbol]
    base_path = BUCKET_PATHS[bucket]

    # 🔵 TV FETCH FOR BROADER & SECTOR
    if bucket in ["broader_index", "sector_index"]:

        try:
            tv = TvDatafeed()
        except Exception as e:
            return f"❌ {symbol} TV init failed: {e}"

        for tf, interval in TIMEFRAMES.items():

            try:
                df = tv.get_hist(
                    symbol=symbol,
                    exchange="NSE",
                    interval=interval,
                    n_bars=BARS
                )
            except Exception as e:
                print(f"❌ {symbol} {tf} fetch error: {e}")
                continue

            if df is None or df.empty:
                print(f"⚠️ Empty TV data: {symbol} {tf}")
                continue

            df = df.sort_index().tail(BARS)

            df["rsi_14"] = calc_rsi(df["close"])
            df["bb_upper"], df["bb_middle"], df["bb_lower"], df["bb_width"] = \
                calc_bollinger(df["close"])
            df["cpr_pivot"], df["cpr_bc"], df["cpr_tc"], df["cpr_width"] = \
                calc_cpr(df)
            df["cam_h3"], df["cam_h4"], df["cam_l3"], df["cam_l4"] = \
                calc_camarilla(df)

            df["symbol"] = symbol
            df["timeframe"] = tf
            df["bucket"] = bucket

            save_path = os.path.join(base_path, tf, f"{symbol}.parquet")
            df.to_parquet(save_path)

            print(f"✅ TV Saved: {symbol} {tf}")

        return f"✅ {symbol} updated [TV]"

    # 🟢 FNO FROM LOCAL FILES
    else:

        for tf, folder in LOCAL_FNO_PATHS.items():

            source_file = os.path.join(folder, f"{symbol}.parquet")

            if not os.path.exists(source_file):
                continue

            df = pd.read_parquet(source_file)

            if "datetime" in df.columns:
                df["datetime"] = pd.to_datetime(df["datetime"])
                df = df.set_index("datetime")

            df = df.sort_index().tail(BARS)

            df["rsi_14"] = calc_rsi(df["close"])
            df["bb_upper"], df["bb_middle"], df["bb_lower"], df["bb_width"] = \
                calc_bollinger(df["close"])
            df["cpr_pivot"], df["cpr_bc"], df["cpr_tc"], df["cpr_width"] = \
                calc_cpr(df)
            df["cam_h3"], df["cam_h4"], df["cam_l3"], df["cam_l4"] = \
                calc_camarilla(df)

            df["symbol"] = symbol
            df["timeframe"] = tf
            df["bucket"] = "fno"

            save_path = os.path.join(base_path, tf, f"{symbol}.parquet")
            df.to_parquet(save_path)

            print(f"✅ FNO Saved: {symbol} {tf}")

        return f"✅ {symbol} updated [LOCAL FNO]"

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":

    print("\n🚀 Hybrid Collector Started\n")

    start = time.time()

    symbols = ALL_SYMBOLS.copy()
    random.shuffle(symbols)

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_symbol, s) for s in symbols]
        for f in as_completed(futures):
            print(f.result())

    elapsed = int(time.time() - start)
    print(f"\n✅ Completed in {elapsed} seconds\n")
