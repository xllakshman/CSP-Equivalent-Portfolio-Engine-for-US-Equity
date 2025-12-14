import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Portfolio Command Center",
    layout="wide"
)

st.title("📊 Portfolio Command Center")
st.caption(
    "Rules-based investing | India-legal CSP equivalent | "
    "200 DMA anchored | Risk-aware capital recycling"
)

# =====================================================
# STRATEGY CONFIG (CENTRAL CONTROL)
# =====================================================
SELL_L1 = 0.15
SELL_L2 = 0.20
SELL_L3 = 0.30

SELL_L1_PCT = 0.25
SELL_L2_PCT = 0.25

BUY_ZONE_LOW = 0.92
BUY_ZONE_HIGH = 0.97
DEEP_BUY = 0.90
NEAR_DMA = 0.03

NASDAQ_EXTREME = 0.12

# =====================================================
# DATA LOADERS
# =====================================================
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio.csv")
    df.columns = df.columns.str.strip().str.lower()
    df["ticker"] = df["ticker"].str.upper()
    return df

@st.cache_data
def load_top100():
    df = pd.read_csv("data/portfolio_top100.csv")
    df.columns = df.columns.str.strip().str.lower()
    df["ticker"] = df["ticker"].str.upper()
    return df

@st.cache_data(ttl=3600)
def fetch_price_data(ticker):
    return yf.download(ticker, period="1y", interval="1d", progress=False)

@st.cache_data(ttl=3600)
def fetch_nasdaq_dist():
    data = yf.download("^IXIC", period="1y", interval="1d", progress=False)
    if data is None or data.empty or len(data) < 200:
        return 0.0
    close = data["Close"]
    price = float(close.iloc[-1])
    dma = float(close.rolling(200).mean().iloc[-1])
    return float((price - dma) / dma)

# =====================================================
# STRATEGY ENGINE
# =====================================================
def csp_equivalent_decision(price, dma):
    dist = (price - dma) / dma

    if dist >= SELL_L3:
        return "HOLD CORE", 0.0, "Extreme extension"
    elif dist >= SELL_L2:
        return "SELL PARTIAL", SELL_L2_PCT, ">20% above 200 DMA"
    elif dist >= SELL_L1:
        return "SELL PARTIAL", SELL_L1_PCT, ">15% above 200 DMA"
    elif abs(dist) <= NEAR_DMA:
        return "SMALL BUY", 0.0, "Near 200 DMA"
    elif BUY_ZONE_LOW <= price / dma <= BUY_ZONE_HIGH:
        return "ACCUMULATE", 0.0, "Inside virtual CSP buy zone"
    elif price < dma * DEEP_BUY:
        return "AGGRESSIVE BUY", 0.0, "Deep discount to 200 DMA"
    else:
        return "WAIT", 0.0, "No edge"

# =====================================================
# LOAD DATA
# =====================================================
portfolio = load_portfolio()
top100_df = load_top100()
nasdaq_dist = fetch_nasdaq_dist()

tab1, tab2 = st.tabs([
    "📌 My Portfolio",
    "🤖🧬 Top 100 AI & Healthcare"
])

# =====================================================
# TAB 1 — PORTFOLIO
# =====================================================
with tab1:
    st.subheader("📌 Portfolio Execution Engine")

    results = []

    for _, row in portfolio.iterrows():
        data = fetch_price_data(row["ticker"])
        if data.empty or len(data) < 200:
            continue

        close = data["Close"]
        price = float(close.iloc[-1])
        dma = float(close.rolling(200).mean().iloc[-1])

        action, sell_pct, reason = csp_equivalent_decision(price, dma)

        if nasdaq_dist > NASDAQ_EXTREME and action.startswith("SELL"):
            reason += " | Market-wide extension"

        results.append({
            "Ticker": row["ticker"],
            "Sector": row["sector"],
            "Shares Held": row["shares"],
            "Shares to Sell": round(row["shares"] * sell_pct, 4),
            "Avg Cost": row["avg_cost"],
            "Current Price": round(price, 2),
            "200 DMA": round(dma, 2),
            "Dist from 200DMA %": round((price - dma) / dma * 100, 2),
            "Action": action,
            "Reason": reason
        })

    df_port = pd.DataFrame(results)

    st.dataframe(df_port, use_container_width=True)

    with st.expander("📘 How to use – Portfolio Tab"):
        st.markdown("""
**Purpose:** Execute disciplined actions on stocks you already own.

**Actions**
- **SELL PARTIAL** → Book profits, create cash
- **HOLD CORE** → Let secular winners run
- **SMALL BUY / ACCUMULATE** → Deploy calmly near fair value
- **WAIT** → Cash is a position

**Key Metric**
- **200 DMA**: Long-term valuation & risk anchor used by institutions
""")

# =====================================================
# TAB 2 — TOP 100 ROTATION ENGINE
# =====================================================
with tab2:
    st.subheader("🤖🧬 Rotation Discovery Engine")

    col1, col2 = st.columns(2)

    with col1:
        universe = st.radio("Universe", ["All", "AI Focus", "Healthcare Focus"], horizontal=True)

    with col2:
        show_top10 = st.checkbox("Show Top 10 Only", value=True)

    results = []

    def score_price(dist):
        if dist <= -5: return 40
        if dist <= 0: return 30
        if dist <= 5: return 20
        if dist <= 10: return 10
        return 0

    def score_action(a):
        return {
            "AGGRESSIVE BUY": 25,
            "ACCUMULATE": 20,
            "SMALL BUY": 15,
            "WAIT": 5
        }.get(a, 0)

    for _, row in top100_df.iterrows():
        data = fetch_price_data(row["ticker"])
        if data.empty or len(data) < 200:
            continue

        close = data["Close"]
        price = float(close.iloc[-1])
        dma = float(close.rolling(200).mean().iloc[-1])
        dist_pct = (price - dma) / dma * 100

        action, _, reason = csp_equivalent_decision(price, dma)

        score = (
            score_price(dist_pct)
            + score_action(action)
            + (15 if row["growth_%_3y"] >= 15 else 5)
            + (15 if row["ai_exposure_score"] >= 70 else 5)
        )

        if nasdaq_dist > NASDAQ_EXTREME:
            score -= 15
            reason += " | Market overheated"

        score = max(0, min(100, score))

        results.append({
            "Ticker": row["ticker"],
            "Company": row["company name"],
            "Sector": row["sector"],
            "Rotation Score": score,
            "Action": action,
            "Dist from 200DMA %": round(dist_pct, 2),
            "Reason": reason
        })

    df_rot = pd.DataFrame(results).sort_values("Rotation Score", ascending=False)

    if universe == "AI Focus":
        df_rot = df_rot[df_rot["Sector"].str.lower() != "healthcare"]
    elif universe == "Healthcare Focus":
        df_rot = df_rot[df_rot["Sector"].str.lower() == "healthcare"]

    if show_top10:
        df_rot = df_rot.head(10)

    st.dataframe(df_rot, use_container_width=True)

    with st.expander("📘 How to use – Rotation Engine & Metrics"):
        st.markdown("""
### Rotation Score (0–100)

**A high Rotation Score means:** “This stock is currently one of the best places to deploy new capital, relative to other choices, given today’s market conditions.”
It does not mean:
- “This is the best stock”
- “This will go up tomorrow”
- “Sell everything else and buy this”

**Think of it as capital allocation priority, not prediction.**

**Composite signal combining:**
- **Price vs 200 DMA (40 pts)** – cheaper is better; Is the stock cheap relative to its own history?; Avoid buying streched stocks
- **Action strength (25 pts)** – BUY beats WAIT; Is the trend favorable without being overheated?; This ensures you’re entering when risk is asymmetric.
- **Growth (15 pts)** – sustained earnings expansion; Does the business have structural growth tailwinds? 3 year growth;
- **AI Exposure (15 pts)** – structural tailwind; Sustained growth → resilience; High AI exposure → secular demand; This avoids value traps and cyclical dead ends.
- **Market penalty (−15 pts)** – reduces risk during frothy markets; Is the market regime supportive?; This prevents forced rotation during frothy markets.

### How This Fits Your Whole System
- **Portfolio Tab answers:** “What should I reduce or hold?”
- **Rotation Tab answers:** “Where should I redeploy cash, if at all?”
- **A high Rotation Score means:** “If I must deploy capital, this is one of the least risky, highest-quality places to do it.”

### How to Interpret Score Ranges (IMPORTANT)
🟢 **80–100 → Strong Rotation Candidate**
- Stock is attractively priced
- Growth + AI tailwinds present
- Market risk is manageable
- Best use of fresh cash today
➡ **Action:** Consider deploying new capital

🟡 **65–79 → Conditional Candidate**
- Setup is good, but not perfect
- Either valuation or market regime is borderline
➡ **Action:** Watch closely / partial deployment

🟠 **40–64 → Neutral**
- No clear edge
- Either expensive or weak growth
➡ **Action:** WAIT

🔴 **Below 40 → Avoid for now**
- Overheated or low-quality setup
➡ **Action:** Do not rotate capital here

### How to use
1. Use **Portfolio tab** to generate cash
2. Use **Top-100 tab** to find rotation candidates
3. Focus on **Top 10 scores**
4. Deploy only when Action ≠ WAIT
""")

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
