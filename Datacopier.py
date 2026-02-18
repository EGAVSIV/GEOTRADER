import pandas as pd
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from tvDatafeed import TvDatafeed, Interval

# =====================================================
# CONFIG
# =====================================================
MAX_WORKERS = 2
BARS = 4000

# =====================================================
# BASE PATH (AUTO-DETECT FOR GITHUB ACTIONS)
# =====================================================
BASE_PATH = /home/runner/work/Stock_Scanner_With_ASTA_Parameters/Stock_Scanner_With_ASTA_Parameters


MARKET_DATA_PATH = os.path.join(BASE_PATH, "market_data")

BUCKET_PATHS = {
    "broader_index": os.path.join(MARKET_DATA_PATH, "broader_index"),
    "sector_index": os.path.join(MARKET_DATA_PATH, "sector_index"),
    "fno": os.path.join(MARKET_DATA_PATH, "fno"),
}

# Ensure structure exists
for bucket in BUCKET_PATHS.values():
    os.makedirs(bucket, exist_ok=True)

# =====================================================
# FNO SOURCE FOLDERS (FROM REPO ROOT)
# =====================================================
LOCAL_FNO_PATHS = {
    "15m": os.path.join(BASE_PATH, "stock_data_15"),
    "1H": os.path.join(BASE_PATH, "stock_data_1H"),
    "D": os.path.join(BASE_PATH, "stock_data_D"),
    "W": os.path.join(BASE_PATH, "stock_data_W"),
    "M": os.path.join(BASE_PATH, "stock_data_M"),
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
# INDEX LIST
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
# AUTO DETECT FNO SYMBOLS
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


def add_indicators(df):
    df["rsi_14"] = calc_rsi(df["close"])
    return df

# =====================================================
# PROCESS FUNCTION
# =====================================================
def process_symbol(symbol, bucket):

    # ================================
    # FETCH FROM TRADINGVIEW
    # ================================
    if bucket in ["broader_index", "sector_index"]:

        try:
            tv = TvDatafeed()
        except Exception as e:
            return f"❌ TV init failed for {symbol}: {e}"

        for tf, interval in TIMEFRAMES.items():

            try:
                df = tv.get_hist(
                    symbol=symbol,
                    exchange="NSE",
                    interval=interval,
                    n_bars=BARS
                )
            except Exception as e:
                print(f"❌ {symbol} {tf} error: {e}")
                continue

            if df is None or df.empty:
                continue

            df = df.sort_index().tail(BARS)
            df = add_indicators(df)

            df["symbol"] = symbol
            df["timeframe"] = tf
            df["bucket"] = bucket

            save_folder = os.path.join(BUCKET_PATHS[bucket], tf)
            os.makedirs(save_folder, exist_ok=True)

            save_path = os.path.join(save_folder, f"{symbol}.parquet")
            df.to_parquet(save_path)

            print(f"✅ TV Saved: {symbol} {tf}")

        return f"✔ {symbol} done (TV)"

    # ================================
    # COPY FROM LOCAL FNO
    # ================================
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
            df = add_indicators(df)

            df["symbol"] = symbol
            df["timeframe"] = tf
            df["bucket"] = "fno"

            save_folder = os.path.join(BUCKET_PATHS["fno"], tf)
            os.makedirs(save_folder, exist_ok=True)

            save_path = os.path.join(save_folder, f"{symbol}.parquet")
            df.to_parquet(save_path)

            print(f"✅ FNO Saved: {symbol} {tf}")

        return f"✔ {symbol} done (FNO)"


# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":

    print("\n🚀 Data Copier Started\n")
    start = time.time()

    tasks = []

    # Add index tasks
    for s in broader_index:
        tasks.append((s, "broader_index"))

    for s in sector_index:
        tasks.append((s, "sector_index"))

    # Add FNO tasks
    for s in fno_symbols:
        tasks.append((s, "fno"))

    random.shuffle(tasks)

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_symbol, symbol, bucket)
            for symbol, bucket in tasks
        ]
        for f in as_completed(futures):
            print(f.result())

    elapsed = int(time.time() - start)
    print(f"\n✅ Completed in {elapsed} seconds\n")
