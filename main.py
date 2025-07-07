import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

# Title
st.title("📊 Ranked Stock Analysis Matrix")

# Ticker list
tickers = {
    "KNR Constructions": "KNRCON.NS",
    "Jyoti Resins": "JYOTIRES.NS",
    "Maharashtra Seamless": "MAHSEAMLES.NS",
    "Vesuvius India": "VESUVIUS.NS",
    "Gujarat Pipavav": "GPPL.NS",
    "India Glycols": "INDIAGLYCO.NS",
    "Avantel": "AVANTEL.NS",
    "Gulf Oil Lubricants": "GULFOILLUB.NS",
    "Poddar Pigments": "PODDARMENT.NS",
    "DCX Systems": "DCXINDIA.NS"
}

# Constants
risk_free_rate = 0.065
market_risk_premium = 0.06
assumed_eps_growth = 0.21

@st.cache_data(ttl=3600)
def fetch_stock_data():
    results = []

    for name, symbol in tickers.items():
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            roe = info.get("returnOnEquity")
            pe_ratio = info.get("trailingPE")
            industry_pe = info.get("forwardPE")  # Simulating as Industry PE
            pb_ratio = info.get("priceToBook")
            de_ratio = info.get("debtToEquity")
            dividend_yield = info.get("dividendYield")
            market_cap = info.get("marketCap")
            current_price = info.get("currentPrice")
            beta = info.get("beta", 1.0)

            cost_of_equity = risk_free_rate + beta * market_risk_premium
            peg_ratio = (pe_ratio / (assumed_eps_growth * 100)) if (pe_ratio and assumed_eps_growth) else None
            roe_percent = roe * 100 if roe else None
            roe_spread = roe_percent - (cost_of_equity * 100) if roe_percent else None

            results.append({
                "Company": name,
                "P/E": pe_ratio,
                "Industry P/E": industry_pe,
                "PEG": peg_ratio,
                "ROE (%)": roe_percent,
                "CoE (%)": cost_of_equity * 100,
                "ROE - CoE (%)": roe_spread,
                "P/B": pb_ratio,
                "D/E": de_ratio,
                "Dividend Yield (%)": dividend_yield * 100 if dividend_yield else None,
                "Market Cap (₹ Cr)": market_cap / 1e7 if market_cap else None,
                "Price (₹)": current_price
            })

        except Exception as e:
            st.warning(f"Error fetching data for {name}: {e}")

    return pd.DataFrame(results)

# Fetch and process data
df = fetch_stock_data()

if df.empty:
    st.error("Failed to fetch stock data.")
    st.stop()

# Ranking
scored_df = df.copy()

for col in ["PEG", "P/E", "P/B", "D/E"]:
    scored_df[f"{col}_score"] = scored_df[col].rank(ascending=True)

for col in ["ROE - CoE (%)", "Dividend Yield (%)"]:
    scored_df[f"{col}_score"] = scored_df[col].rank(ascending=False)

score_columns = [col for col in scored_df.columns if col.endswith("_score")]
scored_df["Total Score"] = scored_df[score_columns].sum(axis=1)
scored_df["Rank"] = scored_df["Total Score"].rank(method="min").astype(int)
scored_df = scored_df.sort_values("Rank")

# Display table
display_cols = [
    "Rank", "Company", "P/E", "Industry P/E", "PEG", "ROE (%)", "CoE (%)", "ROE - CoE (%)",
    "P/B", "D/E", "Dividend Yield (%)", "Market Cap (₹ Cr)", "Price (₹)"
]

st.dataframe(scored_df[display_cols].set_index("Rank"), use_container_width=True)

# Factor-wise score explanation
st.subheader("📌 Factor Scoring Explanation")
explanation = pd.DataFrame([
    {"Factor": "PEG", "Ideal": "< 1", "Explanation": "Lower PEG indicates undervaluation relative to growth."},
    {"Factor": "P/E", "Ideal": "Low vs industry", "Explanation": "Lower P/E suggests better value."},
    {"Factor": "Industry P/E", "Ideal": "—", "Explanation": "For comparison with company P/E."},
    {"Factor": "P/B", "Ideal": "Low", "Explanation": "Lower P/B indicates potential undervaluation."},
    {"Factor": "D/E", "Ideal": "< 1", "Explanation": "Lower D/E means lower financial risk."},
    {"Factor": "ROE - CoE (%)", "Ideal": "> 0", "Explanation": "ROE above CoE indicates value creation."},
    {"Factor": "Dividend Yield (%)", "Ideal": "> 1%", "Explanation": "Higher yield is attractive for income investors."}
])

st.dataframe(explanation, use_container_width=True)

# Summary Section
def generate_summary(row):
    positives = []
    cautions = []
    if row['PEG'] is not None and row['PEG'] < 1:
        positives.append("✔ PEG < 1")
    else:
        cautions.append("⚠ PEG ≥ 1 or unavailable")

    if row['ROE - CoE (%)'] is not None and row['ROE - CoE (%)'] > 0:
        positives.append("✔ ROE exceeds Cost of Equity")
    else:
        cautions.append("⚠ ROE ≤ CoE")

    if row['D/E'] is not None and row['D/E'] < 1:
        positives.append("✔ Low Debt-to-Equity")
    else:
        cautions.append("⚠ High Debt")

    if row['Dividend Yield (%)'] is not None and row['Dividend Yield (%)'] > 1:
        positives.append("✔ Healthy Dividend Yield")

    return positives, cautions

st.subheader("📝 Summary & Caution for Each Company")

for i, row in scored_df.iterrows():
    st.markdown(f"### {row['Company']} (Rank {row['Rank']})")
    positives, cautions = generate_summary(row)

    st.markdown("**✅ Positives:**")
    for pos in positives:
        st.markdown(f"- {pos}")

    if cautions:
        st.markdown("**⚠ Cautions:**")
        for c in cautions:
            st.markdown(f"- {c}")

# Last updated timestamp
st.caption(f"🔄 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
