import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

st.title("\U0001F4CA Ranked Stock Analysis Matrix with ROE, ROIC, and WACC")

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

risk_free_rate = 0.065
market_risk_premium = 0.06
assumed_eps_growth = 0.21
assumed_cost_of_debt = 0.08


@st.cache_data(ttl=3600)
def fetch_stock_data():
    results = []

    for name, symbol in tickers.items():
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            financials = stock.financials
            cashflow = stock.cashflow

            net_income = None
            cfo = None

            for label in financials.index:
                if "net income" in label.lower():
                    ni_series = financials.loc[label].dropna()
                    if not ni_series.empty:
                        net_income = ni_series.iloc[0]
                        break

            for label in cashflow.index:
                if "operating" in label.lower() and "activities" in label.lower():
                    cfo_series = cashflow.loc[label].dropna()
                    if not cfo_series.empty:
                        cfo = cfo_series.iloc[0]
                        break

            earnings_quality = cfo >= net_income if net_income and cfo else None

            roe = info.get("returnOnEquity")
            pe_ratio = info.get("trailingPE")
            industry_pe = info.get("forwardPE")
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

            ebit = info.get("ebit") or info.get("ebitda")
            tax_rate = info.get("taxRate", 0.25)

            nopat = ebit * (1 - tax_rate) if ebit else None
            total_debt = info.get("totalDebt", 0)
            total_equity = info.get("totalStockholderEquity", 0)
            invested_capital = total_debt + total_equity

            roic = (nopat / invested_capital) * 100 if nopat and invested_capital else None

            equity_weight = total_equity / invested_capital if invested_capital else 0
            debt_weight = total_debt / invested_capital if invested_capital else 0
            wacc = (equity_weight * cost_of_equity) + (
                        debt_weight * assumed_cost_of_debt * (1 - tax_rate)) if invested_capital else None
            roic_spread = roic - (wacc * 100) if roic and wacc else None

            results.append({
                "Company": name,
                "P/E": pe_ratio,
                "Industry P/E": industry_pe,
                "PEG": peg_ratio,
                "ROE (%)": roe_percent,
                "CoE (%)": cost_of_equity * 100,
                "ROE - CoE (%)": roe_spread,
                "ROIC (%)": roic,
                "WACC (%)": wacc * 100 if wacc else None,
                "ROIC - WACC (%)": roic_spread,
                "P/B": pb_ratio,
                "D/E": de_ratio,
                "Dividend Yield (%)": dividend_yield * 100 if dividend_yield else None,
                "Market Cap (₹ Cr)": market_cap / 1e7 if market_cap else None,
                "Price (₹)": current_price,
                "Earnings Quality (CFO ≥ Net Profit)": "✔" if earnings_quality else "✖" if earnings_quality is not None else "N/A",
                "Earnings Quality Score": 1 if earnings_quality else 0 if earnings_quality is not None else None
            })

        except Exception as e:
            st.warning(f"Error fetching data for {name}: {e}")

    return pd.DataFrame(results)


df = fetch_stock_data()

if df.empty:
    st.error("Failed to fetch stock data.")
    st.stop()

scored_df = df.copy()

for col in ["PEG", "P/E", "P/B", "D/E"]:
    scored_df[f"{col}_score"] = scored_df[col].rank(ascending=True)

for col in ["ROE - CoE (%)", "ROIC - WACC (%)", "Dividend Yield (%)"]:
    scored_df[f"{col}_score"] = scored_df[col].rank(ascending=False)

scored_df["Earnings Quality Score_score"] = scored_df["Earnings Quality Score"]

scored_df["Total Score"] = (
    scored_df[[col for col in scored_df.columns if col.endswith("_score")]].sum(axis=1)
)

scored_df = scored_df[scored_df["Total Score"].notna()].copy()
scored_df["Rank"] = scored_df["Total Score"].rank(method="min").astype("Int64")
scored_df = scored_df.sort_values("Rank")

display_cols = [
    "Rank", "Company", "P/E", "Industry P/E", "PEG", "ROE (%)", "CoE (%)", "ROE - CoE (%)",
    "ROIC (%)", "WACC (%)", "ROIC - WACC (%)",
    "P/B", "D/E", "Dividend Yield (%)", "Earnings Quality (CFO ≥ Net Profit)", "Market Cap (₹ Cr)", "Price (₹)"
]

st.dataframe(scored_df[display_cols].set_index("Rank"), use_container_width=True)

st.subheader("\U0001F4CC Factor Scoring Explanation")
explanation = pd.DataFrame([
    {"Factor": "PEG", "Ideal": "< 1", "Explanation": "Lower PEG indicates undervaluation relative to growth."},
    {"Factor": "P/E", "Ideal": "Low vs industry", "Explanation": "Lower P/E suggests better value."},
    {"Factor": "Industry P/E", "Ideal": "—", "Explanation": "For comparison with company P/E."},
    {"Factor": "P/B", "Ideal": "Low", "Explanation": "Lower P/B indicates potential undervaluation."},
    {"Factor": "D/E", "Ideal": "< 1", "Explanation": "Lower D/E means lower financial risk."},
    {"Factor": "ROE - CoE (%)", "Ideal": "> 0", "Explanation": "ROE above CoE indicates value creation."},
    {"Factor": "ROIC - WACC (%)", "Ideal": "> 0", "Explanation": "ROIC exceeding WACC indicates true value creation."},
    {"Factor": "Dividend Yield (%)", "Ideal": "> 1%",
     "Explanation": "Higher yield is attractive for income investors."},
    {"Factor": "Earnings Quality (CFO ≥ Net Profit)", "Ideal": "✔",
     "Explanation": "Good earnings quality when operating cash ≥ reported net income. Scoring: 1 if true, 0 otherwise."}
])

st.dataframe(explanation, use_container_width=True)


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

    if row['ROIC - WACC (%)'] is not None and row['ROIC - WACC (%)'] > 0:
        positives.append("✔ ROIC exceeds WACC")
    else:
        cautions.append("⚠ ROIC ≤ WACC")

    if row['D/E'] is not None and row['D/E'] < 1:
        positives.append("✔ Low Debt-to-Equity")
    else:
        cautions.append("⚠ High Debt")

    if row['Dividend Yield (%)'] is not None and row['Dividend Yield (%)'] > 1:
        positives.append("✔ Healthy Dividend Yield")

    if row["Earnings Quality (CFO ≥ Net Profit)"] == "✔":
        positives.append("✔ Strong Earnings Quality (CFO ≥ Net Profit)")
    elif row["Earnings Quality (CFO ≥ Net Profit)"] == "✖":
        cautions.append("⚠ Weak Earnings Quality (CFO < Net Profit)")

    return positives, cautions


st.subheader("\U0001F4DD Summary & Caution for Each Company")
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

st.caption(f"\U0001F504 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
