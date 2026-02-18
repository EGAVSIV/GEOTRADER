import streamlit as st
import pandas as pd
import os
import plotly.express as px
import time
import base64
from datetime import timedelta
import pytz


# =====================================================
# CONFIG
# =====================================================
BASE_PATH = os.path.dirname(__file__)
ICON_PATH = os.path.join(BASE_PATH, "Assets", "BG11.png")

if os.path.exists(ICON_PATH):
    st.set_page_config(
        page_title="Market Dashboard",
        layout="wide",
        page_icon=ICON_PATH
    )
else:
    st.set_page_config(
        page_title="Market Dashboard",
        layout="wide"
    )

IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# MANUAL REFRESH BUTTON (NO AUTO REFRESH)
# =====================================================
st.sidebar.button("🔄 Refresh Data")  # pressing this reruns the script

# =====================================================
# BACKGROUND IMAGE
# =====================================================
def set_bg_image(image_path: str):
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

bg_path = os.path.join(BASE_PATH, "Assets", "BG11.png")
if os.path.exists(bg_path):
    set_bg_image(bg_path)

# =====================================================
# PATHS (DEFINE BEFORE FIRST USE)
# =====================================================
BASE_DIR = "market_data"
BROADER_PATH = os.path.join(BASE_DIR, "broader_index", "D")
SECTOR_PATH  = os.path.join(BASE_DIR, "sector_index", "D")
FNO_PATH     = os.path.join(BASE_DIR, "fno", "D")

for p in [BROADER_PATH, SECTOR_PATH, FNO_PATH]:
    if not os.path.exists(p):
        st.error(f"Missing data folder: {p}")
        st.stop()

SECTOR_MAP_FILE = os.path.join(BASE_PATH, "market_data", "FNOSECTOR.xlsx")
if not os.path.exists(SECTOR_MAP_FILE):
    st.error("❌ FNOSECTOR.xlsx not found inside market_data folder")
    st.stop()

sector_map = pd.read_excel(SECTOR_MAP_FILE)




# =====================================================
# HELPERS
# =====================================================
def pct_change_last_two(path):
    df = pd.read_parquet(path).sort_index()
    if len(df) < 2:
        return None
    p, c = df["close"].iloc[-2], df["close"].iloc[-1]
    return round(((c - p) / p) * 100, 2)

def load_bucket(folder):
    rows = []

    for f in sorted(os.listdir(folder)):
        if not f.endswith(".parquet"):
            continue

        symbol = f.replace(".parquet", "")
        path = os.path.join(folder, f)

        change = 0.0  # DEFAULT (important)

        try:
            df = pd.read_parquet(path).sort_index()

            if (
                len(df) >= 2 and
                "close" in df.columns and
                pd.notna(df["close"].iloc[-1]) and
                pd.notna(df["close"].iloc[-2])
            ):
                p = df["close"].iloc[-2]
                c = df["close"].iloc[-1]
                if p != 0:
                    change = round(((c - p) / p) * 100, 2)

        except Exception:
            pass  # still keep sector with 0.0

        rows.append({
            "Symbol": symbol,
            "Change": change
        })

    return pd.DataFrame(rows)


def sector_color(value, max_pos, min_neg):
    # Positive → Green shades
    if value >= 0:
        intensity = value / max_pos if max_pos != 0 else 0
        return f"rgba(0, 180, 0, {0.35 + 0.65 * intensity})"
    # Negative → Red shades
    else:
        intensity = value / min_neg if min_neg != 0 else 0
        return f"rgba(220, 0, 0, {0.35 + 0.65 * intensity})"


def load_fno_daily_change(fno_path):
    rows = []

    for file in os.listdir(fno_path):
        if not file.endswith(".parquet"):
            continue

        symbol = file.replace(".parquet", "")
        path = os.path.join(fno_path, file)

        try:
            df = pd.read_parquet(path).sort_index()
            if len(df) < 2:
                continue

            prev_close = df["close"].iloc[-2]
            curr_close = df["close"].iloc[-1]

            if pd.isna(prev_close) or pd.isna(curr_close) or prev_close == 0:
                continue

            change = round(((curr_close - prev_close) / prev_close) * 100, 2)

            rows.append({
                "Symbol": symbol,
                "Change": change
            })

        except Exception:
            pass

    return pd.DataFrame(rows)
df_fno_all = load_fno_daily_change(FNO_PATH)

top5 = df_fno_all.sort_values("Change", ascending=False).head(5)
bottom5 = df_fno_all.sort_values("Change").head(5)

# =====================================================
# RUNNING TICKERS : QUOTES / FNO GAINERS / FNO LOSERS
# =====================================================

# =====================================================
# TOP HEADER : LOGO (LEFT) + RUNNING TICKERS (RIGHT)
# =====================================================

col_logo, col_ticker = st.columns([0.22, 0.78])

with col_logo:
    logo_path = os.path.join(BASE_PATH, "Assets", "BG11.png")

    if os.path.exists(logo_path):
        st.image(logo_path, width=220)
    else:
        st.warning("Logo not found")



if "quotes_rendered" not in st.session_state:
    st.session_state.quotes_rendered = False

with col_ticker:

    # =====================================================
    # QUOTES — RENDER ONLY ONCE (NO RESTART)
    # =====================================================
    if not st.session_state.quotes_rendered:

        quotes = [
         
            
            "याद रखना कमजोर हम नहीं, हमारा वक्त है",
            "अगर जिंदगी बदलनी है तो सबसे पहले सोच बदलो",
            "खुद पर भरोसा रखो, यही सबसे बड़ी ताकत है",
            "संघर्ष जितना बड़ा होगा, जीत उतनी ही शानदार होगी",
            "खामोशी से मेहनत करो, शोर खुद बन जाएगा",
            "हार तब होती है जब मान लिया जाए",
            "हमारी समस्या का समाधान सिर्फ हमारे पास है, दूसरों के पास तो सिर्फ सुझाव है",
      
        ]

        quote_text = "    ⏩    ".join(quotes)

        st.markdown(
            f"""
            <style>
            .quotes-wrap {{
                width: 100%;
                overflow: hidden;
                padding: 14px 18px;
                margin-bottom: 8px;
                border-radius: 10px;
                background: linear-gradient(90deg, #141E30, #243B55);
                color: white;
                font-size: 22px;
                font-weight: 700;
            }}

            .quotes-ticker {{
                white-space: nowrap;
                animation: quotesScroll 35s linear infinite;
            }}

            @keyframes quotesScroll {{
                0% {{ transform: translateX(100%); }}
                100% {{ transform: translateX(-100%); }}
            }}
            </style>

            <div class="quotes-wrap">
                <div class="quotes-ticker">📜 {quote_text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 🔒 LOCK IT
        st.session_state.quotes_rendered = True

    # =====================================================
    # GAINERS / LOSERS — CAN RE-RENDER FREELY
    # =====================================================
    if not df_fno_all.empty:
        top5 = df_fno_all.sort_values("Change", ascending=False).head(5)
        bottom5 = df_fno_all.sort_values("Change").head(5)
    else:
        top5 = bottom5 = []

    gainers_text = " | ".join(
        [f"{r.Symbol} +{r.Change}%" for r in top5.itertuples()]
    )

    losers_text = " | ".join(
        [f"{r.Symbol} {r.Change}%" for r in bottom5.itertuples()]
    )

    st.markdown(
        f"""
        <style>
        .ticker-wrap {{
            width: 100%;
            overflow: hidden;
            padding: 10px 16px;
            margin-bottom: 6px;
            border-radius: 10px;
            font-weight: 700;
        }}

        .gainers {{
            background: #e6fff2;
            color: #0a7d3b;
            font-size: 19px;
        }}

        .gainers-ticker {{
            white-space: nowrap;
            animation: gainersScroll 9s linear infinite;
        }}

        @keyframes gainersScroll {{
            0% {{ transform: translateX(100%); }}
            100% {{ transform: translateX(-100%); }}
        }}

        .losers {{
            background: #fff0f0;
            color: #b00020;
            font-size: 19px;
        }}

        .losers-ticker {{
            white-space: nowrap;
            animation: losersScroll 9s linear infinite;
        }}

        @keyframes losersScroll {{
            0% {{ transform: translateX(100%); }}
            100% {{ transform: translateX(-100%); }}
        }}
        </style>

        <div class="ticker-wrap gainers">
            <div class="gainers-ticker">🟢 FNO TOP GAINERS → {gainers_text}</div>
        </div>

        <div class="ticker-wrap losers">
            <div class="losers-ticker">🔴 FNO TOP LOSERS → {losers_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")



if not df_fno_all.empty:
    df_fno_plot = (
        pd.concat([top5, bottom5])
        .sort_values("Change")
        .reset_index(drop=True)
    )
else:
    df_fno_plot = pd.DataFrame(columns=["Symbol", "Change"])

max_pos = df_fno_plot["Change"].max()
min_neg = df_fno_plot["Change"].min()

df_fno_plot["Color"] = df_fno_plot["Change"].apply(
    lambda x: sector_color(x, max_pos, min_neg)
)




# =====================================================
# LOAD DATA
# =====================================================
df_broader = load_bucket(BROADER_PATH)
max_pos_b = df_broader["Change"].max()
min_neg_b = df_broader["Change"].min()

df_broader["Color"] = df_broader["Change"].apply(
    lambda x: sector_color(x, max_pos_b, min_neg_b)
)

df_sector  = load_bucket(SECTOR_PATH)

if df_sector.empty:
    st.warning("⚠️ No valid sector parquet files found")
    st.stop()

max_positive = df_sector["Change"].max()
min_negative = df_sector["Change"].min()

df_sector["Color"] = df_sector["Change"].apply(
    lambda x: sector_color(x, max_positive, min_negative)
)

df_fno     = load_bucket(FNO_PATH)

# =====================================================
# ADVANCE / DECLINE (FNO)
# =====================================================
adv = (df_fno["Change"] > 0).sum()
dec = (df_fno["Change"] < 0).sum()
unch = (df_fno["Change"] == 0).sum()

df_ad = pd.DataFrame({
    "Type": ["Advance", "Decline", "Unchanged"],
    "Count": [adv, dec, unch]
})

# =====================================================
# SECTOR → STOCK MAPPING
# =====================================================
# =====================================================
# LOAD SECTOR → STOCK MAPPING (ROBUST)
# =====================================================


# Normalize column names
sector_map.columns = (
    sector_map.columns
    .astype(str)
    .str.strip()
    .str.lower()
)

# Detect columns automatically
stock_col = None
sector_col = None

for col in sector_map.columns:
    if "stock" in col:
        stock_col = col
    if "sector" in col:
        sector_col = col

if stock_col is None or sector_col is None:
    st.error(
        f"❌ Invalid Excel format.\n\n"
        f"Found columns: {list(sector_map.columns)}\n\n"
        f"Expected columns containing words: 'stock' and 'sector'"
    )
    st.stop()

# Rename to standard names
sector_map = sector_map.rename(
    columns={stock_col: "Stock", sector_col: "Sector"}
)

# Handle multi-sector stocks
sector_map["Sector"] = sector_map["Sector"].astype(str).str.split(",")
sector_map = sector_map.explode("Sector")
sector_map["Sector"] = sector_map["Sector"].str.strip()





# =====================================================
# UI
# =====================================================
st.title("📊 Market Dashboard")



col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 1.2])


# =====================================================
# BROAD MARKET
# =====================================================
with col1:
    st.subheader("📈 Broad Market Indices")
    df_plot = df_broader.sort_values("Change")

    fig = px.bar(
        df_plot,
        x="Change",
        y="Symbol",
        orientation="h"
    )

    fig.update_traces(
        marker_color=df_plot["Color"]
    )

    fig.update_layout(
        height=420,
        xaxis_title="% Change",
        yaxis_title="",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


# =====================================================
# SECTOR PERFORMANCE + SELECTION
# =====================================================
with col2:
    st.subheader("🏭 Sector Performance")

    df_plot = (
        df_sector
        .sort_values("Change")
        .reset_index(drop=True)
    )

    fig = px.bar(
        df_plot,
        x="Change",
        y="Symbol",
        orientation="h"
    )

    fig.update_traces(
        marker_color=df_plot["Color"],
        hovertemplate="<b>%{y}</b><br>% Change: %{x}%<extra></extra>"
    )

    fig.update_yaxes(
        automargin=True,
        categoryorder="array",
        categoryarray=df_plot["Symbol"].tolist()
    )

    fig.update_layout(
        height=420,
        xaxis_title="% Change",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=220, r=20, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)




# =====================================================
# ADVANCE / DECLINE
# =====================================================
with col3:
    st.subheader("⚖️ Advance / Decline (FNO)")
    fig = px.pie(
        df_ad,
        names="Type",
        values="Count",
        hole=0.45,
        color="Type",
        color_discrete_map={
            "Advance": "#00C176",
            "Decline": "#FF4B4B",
            "Unchanged": "#B0BEC5"
        }
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("🔥 FNO Top 5 & Bottom 5")

    fig = px.bar(
        df_fno_plot,
        x="Change",
        y="Symbol",
        orientation="h"
    )

    fig.update_traces(
        marker_color=df_fno_plot["Color"],
        hovertemplate="<b>%{y}</b><br>% Change: %{x}%<extra></extra>"
    )

    fig.update_layout(
        height=420,
        xaxis_title="% Change",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=180, r=20, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
stock_col1, stock_col2, stock_col3, stock_col4 = st.columns([1.2, 1.2, 1, 1.2])

def sector_fno_bar(sector_name, title):
    stocks = sector_map[sector_map["Sector"] == sector_name]["Stock"].unique()
    df_sec = df_fno_all[df_fno_all["Symbol"].isin(stocks)]

    if df_sec.empty:
        st.warning("No FNO stocks mapped")
        return

    top5 = df_sec.sort_values("Change", ascending=False).head(5)
    bottom5 = df_sec.sort_values("Change").head(5)

    df_plot = (
        pd.concat([top5, bottom5])
        .sort_values("Change")
        .reset_index(drop=True)
    )

    max_pos = df_plot["Change"].max()
    min_neg = df_plot["Change"].min()

    df_plot["Color"] = df_plot["Change"].apply(
        lambda x: sector_color(x, max_pos, min_neg)
    )

    fig = px.bar(
        df_plot,
        x="Change",
        y="Symbol",
        orientation="h"
    )

    fig.update_traces(marker_color=df_plot["Color"])
    fig.update_layout(
        height=420,
        xaxis_title="% Change",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=160, r=20, t=40, b=40)
    )

    st.subheader(title)
    st.plotly_chart(fig, use_container_width=True)

# ✅ only once
sector_list = df_sector["Symbol"].tolist()

with stock_col1:
    sector_1 = st.selectbox("Sector 1", sector_list, key="sector_1")
    sector_fno_bar(sector_1, f"{sector_1} Stocks")

with stock_col2:
    sector_2 = st.selectbox("Sector 2", sector_list, key="sector_2")
    sector_fno_bar(sector_2, f"{sector_2} Stocks")

with stock_col3:
    sector_3 = st.selectbox("Sector 3", sector_list, key="sector_3")
    sector_fno_bar(sector_3, f"{sector_3} Stocks")

with stock_col4:
    sector_4 = st.selectbox("Sector 4", sector_list, key="sector_4")
    sector_fno_bar(sector_4, f"{sector_4} Stocks")


##################################################################



def closing_strength_streak(parquet_path, max_days=10):
    df = pd.read_parquet(parquet_path).sort_index()
    if len(df) < 2:
        return 0

    closes = df["close"].tail(max_days).values
    streak = 0

    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            streak += 1
        else:
            break

    return streak

def closing_weakness_streak(parquet_path, max_days=10):
    df = pd.read_parquet(parquet_path).sort_index()
    if len(df) < 2:
        return 0

    closes = df["close"].tail(max_days).values
    streak = 0

    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            streak += 1
        else:
            break

    return streak




# ---- calculate streaks ----
up_rows = []
down_rows = []

for file in os.listdir(FNO_PATH):
    if not file.endswith(".parquet"):
        continue

    symbol = file.replace(".parquet", "")
    path = os.path.join(FNO_PATH, file)

    up_streak = closing_strength_streak(path)
    down_streak = closing_weakness_streak(path)

    if up_streak >= 2:
        up_rows.append({
            "Symbol": symbol,
            "Strength": up_streak
        })

    if down_streak >= 2:
        down_rows.append({
            "Symbol": symbol,
            "Strength": down_streak
        })

# ---- SAFE DataFrames ----
df_up = pd.DataFrame(up_rows, columns=["Symbol", "Strength"])
df_down = pd.DataFrame(down_rows, columns=["Symbol", "Strength"])

df_up = df_up.sort_values("Strength", ascending=False)
df_down = df_down.sort_values("Strength", ascending=False)

# ---- UI ----
st.markdown("---")
st.subheader("🔥 Momentum Streaks (≥ 2 Days)")

up_col, down_col = st.columns(2)
NUM_COLS = 6

with up_col:
    st.markdown("### 🟢 Upside Momentum")
    if df_up.empty:
        st.info("No stocks with upside streak ≥ 2")
    else:
        cols = st.columns(NUM_COLS)
        for i, row in enumerate(df_up.itertuples()):
            with cols[i % NUM_COLS]:
                st.markdown(
                    f"""
                    <div style="
                        background-color:#00c48c;
                        padding:12px;
                        border-radius:8px;
                        text-align:center;
                        font-weight:bold;
                        color:black;
                    ">
                        {row.Symbol}<br>
                        <span style="font-size:20px;">{row.Strength}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

with down_col:
    st.markdown("### 🔴 Downside Momentum")
    if df_down.empty:
        st.info("No stocks with downside streak ≥ 2")
    else:
        cols = st.columns(NUM_COLS)
        for i, row in enumerate(df_down.itertuples()):
            with cols[i % NUM_COLS]:
                st.markdown(
                    f"""
                    <div style="
                        background-color:#ff6b6b;
                        padding:12px;
                        border-radius:8px;
                        text-align:center;
                        font-weight:bold;
                        color:black;
                    ">
                        {row.Symbol}<br>
                        <span style="font-size:20px;">{row.Strength}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

####################################################################################################################

def rsi_state(curr, prev):
    if curr > 60 and prev <= 60:
        return "CHANGE_NOW"
    if curr < 40 and prev >= 40:
        return "CHANGE_NOW"
    if curr > 60:
        return "BULLISH"
    if curr < 40:
        return "BEARISH"
    return "NEUTRAL"

def run_rsi_scanner():
    rows = []

    TF_MAP = {
        "30m": ("30 MIN", os.path.join(BASE_DIR, "fno", "30m")),
        "1H":  ("60 MIN", os.path.join(BASE_DIR, "fno", "1H")),
        "D":   ("DAY",    os.path.join(BASE_DIR, "fno", "D")),
    }

    # ---- 30m / 1H / DAY ----
    for _, (tf_label, tf_path) in TF_MAP.items():
        if not os.path.exists(tf_path):
            continue

        for file in os.listdir(tf_path):
            if not file.endswith(".parquet"):
                continue

            symbol = file.replace(".parquet", "")
            df = pd.read_parquet(os.path.join(tf_path, file)).sort_index()

            if len(df) < 2 or "rsi_14" not in df.columns:
                continue

            curr, prev = df["rsi_14"].iloc[-1], df["rsi_14"].iloc[-2]
            if pd.isna(curr) or pd.isna(prev):
                continue

            rows.append({
                "Symbol": symbol,
                "TF": tf_label,
                "RSI": round(curr, 2),
                "State": rsi_state(curr, prev)
            })

    # ---- WEEK & MONTH from DAILY ----
    daily_path = os.path.join(BASE_DIR, "fno", "D")
    if not os.path.exists(daily_path):
        return pd.DataFrame(rows)

    for file in os.listdir(daily_path):
        if not file.endswith(".parquet"):
            continue

        symbol = file.replace(".parquet", "")
        df = pd.read_parquet(os.path.join(daily_path, file)).sort_index()

        if len(df) < 30 or "rsi_14" not in df.columns:
            continue

        w = df.resample("W-FRI").last().dropna()
        if len(w) >= 2:
            rows.append({
                "Symbol": symbol,
                "TF": "WEEK",
                "RSI": round(w["rsi_14"].iloc[-1], 2),
                "State": rsi_state(w["rsi_14"].iloc[-1], w["rsi_14"].iloc[-2])
            })

        m = df.resample("ME").last().dropna()
        if len(m) >= 2:
            rows.append({
                "Symbol": symbol,
                "TF": "MONTH",
                "RSI": round(m["rsi_14"].iloc[-1], 2),
                "State": rsi_state(m["rsi_14"].iloc[-1], m["rsi_14"].iloc[-2])
            })

    return pd.DataFrame(rows)

st.markdown("---")
st.subheader("📊 RSI Scanner (Multi-Timeframe)")

df_rsi = run_rsi_scanner()

if df_rsi.empty:
    st.warning("No RSI data available")
else:
    states = ["BULLISH", "CHANGE_NOW", "NEUTRAL", "BEARISH"]
    tfs = ["30 MIN", "60 MIN", "DAY", "WEEK", "MONTH"]

    rules = {}
    cols = st.columns(4)

    for i, state in enumerate(states):
        with cols[i]:
            st.markdown(f"### {state}")
            for tf in tfs:
                if st.checkbox(f"{tf} {state}", key=f"{tf}_{state}"):
                    rules.setdefault(tf, set()).add(state)

    qualified = []
    for sym, grp in df_rsi.groupby("Symbol"):
        ok = True
        for tf, allowed in rules.items():
            row = grp[grp["TF"] == tf]
            if row.empty or row.iloc[0]["State"] not in allowed:
                ok = False
                break
        if ok:
            qualified.append(sym)

    df_final = df_rsi[df_rsi["Symbol"].isin(qualified)]

    if df_final.empty:
        st.info("No stocks match selected RSI conditions")
    else:
        st.dataframe(df_final, use_container_width=True, height=400)
#////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
def get_daily_levels(daily_df):
    prev = daily_df.iloc[-2]

    return {
        "day_high": prev["high"],
        "day_low": prev["low"],
        "cpr_tc": prev.get("cpr_tc"),
        "cpr_bc": prev.get("cpr_bc"),
        "cam_h4": prev.get("cam_h4"),
        "cam_l4": prev.get("cam_l4"),
    }


if "rolling_events" not in st.session_state:
    st.session_state.rolling_events = []

if "event_keys" not in st.session_state:
    st.session_state.event_keys = set()

def evaluate_first_break_intraday(symbol, tf, df_tf, daily_df, weekly_df):

    if len(df_tf) < 2 or "rsi_14" not in df_tf.columns:
        return None

    daily = get_daily_levels(daily_df)
    prev_week = weekly_df.iloc[-2]

    today = df_tf.index[-1].date()

    primary_triggered = False

    for i in range(1, len(df_tf)):
        prev = df_tf.iloc[i - 1]
        curr = df_tf.iloc[i]

        ts = curr["datetime"] if "datetime" in df_tf.columns else df_tf.index[i]

        # 🔒 ONLY TODAY’S CANDLES
        if ts.date() != today:
            continue

        prev_close = prev["close"]
        curr_close = curr["close"]

        reasons = []
        bull, bear = 0, 0

        # ==================================================
        # PRIMARY TRIGGERS (ONLY ONE ALLOWED)
        # ==================================================

        # ---- DAILY ----
        if prev_close < daily["day_high"] and curr_close > daily["day_high"]:
            bull += 1
            primary_triggered = True
            reasons.append(f"Daily High BO @ {ts.strftime('%H:%M')}")

        elif prev_close > daily["day_low"] and curr_close < daily["day_low"]:
            bear += 1
            primary_triggered = True
            reasons.append(f"Daily Low BD @ {ts.strftime('%H:%M')}")

        # ---- WEEKLY (ONLY IF DAILY NOT FIRED) ----
        elif prev_close < prev_week["high"] and curr_close > prev_week["high"]:
            bull += 1
            primary_triggered = True
            reasons.append(f"Weekly High BO @ {ts.strftime('%H:%M')}")

        elif prev_close > prev_week["low"] and curr_close < prev_week["low"]:
            bear += 1
            primary_triggered = True
            reasons.append(f"Weekly Low BD @ {ts.strftime('%H:%M')}")

        if not primary_triggered:
            continue  # 🔥 nothing important yet

        # ==================================================
        # CONFIRMATION TRIGGERS (SAME CANDLE ONLY)
        # ==================================================

        # RSI
        rsi_prev, rsi_curr = prev["rsi_14"], curr["rsi_14"]
        if rsi_prev < 60 and rsi_curr > 60:
            bull += 1
            reasons.append(f"RSI > 60 @ {ts.strftime('%H:%M')}")

        if rsi_prev > 40 and rsi_curr < 40:
            bear += 1
            reasons.append(f"RSI < 40 @ {ts.strftime('%H:%M')}")

        # Bollinger
        if "bb_upper" in df_tf.columns:
            if prev_close < prev["bb_upper"] and curr_close > curr["bb_upper"]:
                bull += 1
                reasons.append(f"BB Upper BO @ {ts.strftime('%H:%M')}")

        if "bb_lower" in df_tf.columns:
            if prev_close > prev["bb_lower"] and curr_close < curr["bb_lower"]:
                bear += 1
                reasons.append(f"BB Lower BD @ {ts.strftime('%H:%M')}")

        # CPR
        if daily["cpr_tc"] and prev_close < daily["cpr_tc"] and curr_close > daily["cpr_tc"]:
            bull += 1
            reasons.append(f"CPR TC BO @ {ts.strftime('%H:%M')}")

        if daily["cpr_bc"] and prev_close > daily["cpr_bc"] and curr_close < daily["cpr_bc"]:
            bear += 1
            reasons.append(f"CPR BC BD @ {ts.strftime('%H:%M')}")

        # Camarilla
        if daily["cam_h4"] and prev_close < daily["cam_h4"] and curr_close > daily["cam_h4"]:
            bull += 1
            reasons.append(f"Cam H4 BO @ {ts.strftime('%H:%M')}")

        if daily["cam_l4"] and prev_close > daily["cam_l4"] and curr_close < daily["cam_l4"]:
            bear += 1
            reasons.append(f"Cam L4 BD @ {ts.strftime('%H:%M')}")

        # ==================================================
        # FINAL DECISION (STRICT)
        # ==================================================
        if bull >= 2 and bull > bear:
            return {
                "symbol": symbol,
                "tf": tf,
                "signal": "BUY",
                "ts": ts,
                "reasons": reasons
            }

        if bear >= 2 and bear > bull:
            return {
                "symbol": symbol,
                "tf": tf,
                "signal": "SELL",
                "ts": ts,
                "reasons": reasons
            }

        # 🔒 STOP AFTER FIRST PRIMARY EVENT
        break

    return None



def run_intraday_scan():
    events = []

    for file in os.listdir(FNO_PATH):
        if not file.endswith(".parquet"):
            continue

        symbol = file.replace(".parquet", "")
        daily_df = pd.read_parquet(os.path.join(BASE_DIR, "fno", "D", file)).sort_index()
        weekly_df = daily_df.resample("W-FRI").agg({"high": "max", "low": "min"}).dropna()

        for tf in ["15m", "1H"]:
            path = os.path.join(BASE_DIR, "fno", tf, file)
            if not os.path.exists(path):
                continue

            df_tf = pd.read_parquet(path).sort_index()
            ev = evaluate_first_break_intraday(symbol, tf, df_tf, daily_df, weekly_df)


            if ev:
                key = f"{symbol}_{tf}_{ev['ts']}_{ev['signal']}"
                if key not in st.session_state.event_keys:
                    st.session_state.event_keys.add(key)
                    events.append(ev)

    return events

# =====================================================
# RUN INTRADAY SCAN & UPDATE ROLLING EVENTS
# =====================================================
new_events = run_intraday_scan()

if new_events:
    st.session_state.rolling_events.extend(new_events)

# -----------------------------------------------------
# KEEP ONLY LAST 7 DAYS (TIME-BASED, NOT COUNT-BASED)
# -----------------------------------------------------
from datetime import timedelta

cutoff = pd.Timestamp.now() - timedelta(days=7)

st.session_state.rolling_events = [
    ev for ev in st.session_state.rolling_events
    if ev["ts"] >= cutoff
]

st.markdown("---")
st.subheader("📡 Intraday Rolling Ticker (FNO – Last 7 Days)")

if not st.session_state.rolling_events:
    st.info("No intraday events yet")
else:
    for ev in sorted(st.session_state.rolling_events, key=lambda x: x["ts"], reverse=True):
        color = "#00c48c" if ev["signal"] == "BUY" else "#ff6b6b"

        ts = ev["ts"]
    # ts agar timezone‑aware UTC hai:
        if ts.tzinfo is not None:
            ts_ist = ts.astimezone(IST)
        else:
        # agar naive hai (no tz), treat as UTC then convert
            ts_ist = ts.replace(tzinfo=pytz.UTC).astimezone(IST)

        st.markdown(
            f"""
            <div style="
                border-left: 6px solid {color};
                background: #f9f9f9;
                padding: 10px;
                margin-bottom: 8px;
                border-radius: 6px;
            ">
                <b>{ts_ist.strftime('%d %b %H:%M')}</b>
                | <b>{ev['symbol']}</b>
                | {ev['tf']}
                | <b style="color:{color}">{ev['signal']}</b>
                <br>
                {"<br>".join("• " + r for r in ev["reasons"])}
            </div>
            """,
            unsafe_allow_html=True
        )



