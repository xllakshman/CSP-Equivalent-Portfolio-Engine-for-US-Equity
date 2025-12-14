import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="CSP-Equivalent Portfolio Engine (for US Equity)",
    layout="wide"
)

st.title("📊 CSP-Equivalent Portfolio Engine (India-Legal)")
st.caption("Rules-based | 200 DMA anchored | Partial profit booking | Cash-aware")

# =====================================================
# STRATEGY CONFIG (SINGLE SOURCE OF TRUTH)
# =====================================================
SELL_L1 = 0.15   # +15% above 200 DMA
SELL_L2 = 0.20   # +20%
SELL_L3 = 0.30   # +30%

SELL_L1_PCT = 0.25   # sell 25%
SELL_L2_PCT = 0.25   # sell another 25%

BUY_ZONE_LOW = 0.92   # 8% below 200 DMA
BUY_ZONE_HIGH = 0.97  # 3% below 200 DMA
DEEP_BUY = 0.90       # aggressive buy
NEAR_DMA = 0.03       # ±3%

# =====================================================
# LOAD PORTFOLIO CSV
# =====================================================
@st.cache_data
def load_portfolio():
    try:
        df = pd.read_csv("data/portfolio.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data/portfolio.csv: {e}")
        st.stop()

portfolio = load_portfolio()

required_cols = {"ticker", "shares", "avg_cost", "sector"}
if not required_cols.issubset(set(portfolio.columns)):
    st.error("CSV must contain: ticker, shares, avg_cost, sector")
    st.stop()

portfolio["ticker"] = portfolio["ticker"].str.upper()

# =====================================================
# DATA FETCH
# =====================================================
@st.cache_data(ttl=3600)
def fetch_price_data(ticker):
    return yf.download(ticker, period="1y", interval="1d", progress=False)

@st.cache_data(ttl=3600)
def fetch_nasdaq():
    data = yf.download("^IXIC", period="1y", interval="1d", progress=False)
    close = data["Close"]
    dma = close.rolling(200).mean().iloc[-1]
    price = close.iloc[-1]
    return (price - dma) / dma

nasdaq_dist = fetch_nasdaq()

# =====================================================
# DECISION ENGINE
# =====================================================
def csp_equivalent_decision(price, dma):
    dist = (price - dma) / dma

    # ---- SELL LOGIC (STAGGERED) ----
    if dist >= SELL_L3:
        return "HOLD CORE", 0.0, "Extreme extension; stop selling"

    elif dist >= SELL_L2:
        return "SELL PARTIAL", SELL_L2_PCT, ">20% above 200 DMA"

    elif dist >= SELL_L1:
        return "SELL PARTIAL", SELL_L1_PCT, ">15% above 200 DMA"

    # ---- BUY LOGIC ----
    elif abs(dist) <= NEAR_DMA:
        return "SMALL BUY", 0.0, "Near 200 DMA"

    elif BUY_ZONE_LOW <= price / dma <= BUY_ZONE_HIGH:
        return "ACCUMULATE", 0.0, "Inside virtual CSP buy zone"

    elif price < dma * DEEP_BUY:
        return "AGGRESSIVE BUY", 0.0, "Deep discount to 200 DMA"

    # ---- DEFAULT ----
    else:
        return "WAIT", 0.0, "No edge"

# =====================================================
# RUN ENGINE
# =====================================================
results = []

for _, row in portfolio.iterrows():
    ticker = row["ticker"]
    data = fetch_price_data(ticker)

    if data.empty or len(data) < 200:
        continue

    close = data["Close"]
    price = float(close.iloc[-1])
    dma_200 = float(close.rolling(200).mean().iloc[-1])

    action, sell_pct, reason = csp_equivalent_decision(price, dma_200)

    shares_held = row["shares"]
    shares_to_sell = round(shares_held * sell_pct, 4)

    dist_pct = (price - dma_200) / dma_200 * 100

    # Market correlation context
    if nasdaq_dist > 0.12 and action.startswith("SELL"):
        reason += " | Market-wide tech extension"

    results.append({
        "Ticker": ticker,
        "Sector": row["sector"],
        "Shares Held": shares_held,
        "Shares to Sell": shares_to_sell,
        "Avg Cost": round(row["avg_cost"], 2),
        "Current Price": round(price, 2),
        "200 DMA": round(dma_200, 2),
        "Dist from 200DMA %": round(dist_pct, 2),
        "Action": action,
        "Reason": reason
    })

final_df = pd.DataFrame(results)

# =====================================================
# UI
# =====================================================
st.subheader("📌 Portfolio Action Engine")

st.dataframe(
    final_df.sort_values("Dist from 200DMA %"),
    use_container_width=True,
    column_config={
        "Shares to Sell": st.column_config.NumberColumn(
            help="Calculated using staggered profit booking"
        ),
        "Reason": st.column_config.TextColumn(width="large")
    }
)

# =====================================================
# CONTEXT PANELS
# =====================================================
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🧠 Strategy Rules")
    st.markdown("""
- Partial sells at **+15% / +20%**
- Never fully exit secular winners
- Buy only near or below 200 DMA
- Cash is a valid position
- No forced rotation
""")

with col2:
    st.markdown("### 🌍 Market Context")
    st.metric(
        label="NASDAQ distance from 200 DMA",
        value=f"{round(nasdaq_dist * 100, 2)}%",
        delta="Extended" if nasdaq_dist > 0.12 else "Normal"
    )

# =====================================================
# CSV PREVIEW
# =====================================================
with st.expander("📄 Portfolio Source (data/portfolio.csv)"):
    st.dataframe(portfolio, use_container_width=True)

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
