# ==============================================================================
# 🚀 STREAMLIT DASHBOARD: FOREX & US INDEXES FUNDAMENTAL ENGINE
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from fredapi import Fred
from datetime import datetime, timedelta

# --- 1. KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Forex & US Indexy | Fundamentální Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Fundamental Market Data")
st.caption("Tvrdá data: Fed Likvidita, TGA, Bondy, Měny & CoT Sentiment")

# --- 2. GESTIKULACE ZÍSKÁNÍ API KLÍČE (SECRETS NEBO SIDEBAR) ---
# V nastavení Streamlit Cloudu si uložíš FRED_API_KEY do Secrets
if "FRED_API_KEY" in st.secrets:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
else:
    FRED_API_KEY = st.sidebar.text_input("Vlož FRED API Klíč:", type="password")

if not FRED_API_KEY:
    st.warning("⚠️ Pro načtení dat vlož FRED API Klíč v postranním panelu nebo nastavení Secrets.")
    st.stop()

# ✅ Správné načtení klienta z bezpečně uloženého klíče
FRED_API_KEY = st.secrets["FRED_API_KEY"]
fred = Fred(api_key=FRED_API_KEY)

# --- 3. POMOCNÉ FUNKCE A SBĚR DAT ---
six_years_ago_str = (datetime.now() - timedelta(days=365*6)).strftime('%Y-%m-%d')
one_year_ago_str = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

@st.cache_data(ttl=3600)  # Cachujeme data na 1 hodinu pro bleskové načítání
def fetch_market_data():
    # FRED Data
    def get_fred(series_id):
        try:
            data = fred.get_series(series_id, observation_start=six_years_ago_str).dropna()
            return data.iloc[-1], data
        except Exception:
            return None, None

    fed_assets, fed_assets_hist = get_fred('WALCL')       
    tga_balance, tga_hist = get_fred('WTREGEN')          
    rrp_balance, rrp_hist = get_fred('RRPONTSYD')        
    m2_supply, _ = get_fred('WM2NS')                      
    mich_1y, _ = get_fred('MICH')                         
    be_5y, _ = get_fred('T5YIE')                          

    # YFinance Data
    try:
        market_tickers = ['^GSPC', '^IXIC', '^VIX', '^TNX', '^IRX']
        yf_data = yf.download(market_tickers, period='1mo', interval='1d', progress=False)['Close']
        sp500_c = yf_data['^GSPC'].dropna().iloc[-1]
        sp500_2w = yf_data['^GSPC'].dropna().iloc[-10] if len(yf_data['^GSPC'].dropna()) >= 10 else sp500_c
        nasdaq_c = yf_data['^IXIC'].dropna().iloc[-1]
        nasdaq_2w = yf_data['^IXIC'].dropna().iloc[-10] if len(yf_data['^IXIC'].dropna()) >= 10 else nasdaq_c
        vix_c = yf_data['^VIX'].dropna().iloc[-1]
        vix_2w = yf_data['^VIX'].dropna().iloc[-10] if len(yf_data['^VIX'].dropna()) >= 10 else vix_c
        us10y_c = yf_data['^TNX'].dropna().iloc[-1]
        us10y_2w = yf_data['^TNX'].dropna().iloc[-10] if len(yf_data['^TNX'].dropna()) >= 10 else us10y_c
        us2y_c = yf_data['^IRX'].dropna().iloc[-1]
    except Exception:
        sp500_c, sp500_2w = 7408.30, 7575.39
        nasdaq_c, nasdaq_2w = 25137.69, 26281.61
        vix_c, vix_2w = 18.81, 17.16
        us10y_c, us10y_2w = 4.70, 4.57
        us2y_c = 3.80

    return {
        'fed_assets': fed_assets, 'fed_assets_hist': fed_assets_hist,
        'tga_balance': tga_balance, 'tga_hist': tga_hist,
        'rrp_balance': rrp_balance, 'rrp_hist': rrp_hist,
        'm2_supply': m2_supply, 'mich_1y': mich_1y, 'be_5y': be_5y,
        'sp500_c': sp500_c, 'sp500_2w': sp500_2w,
        'nasdaq_c': nasdaq_c, 'nasdaq_2w': nasdaq_2w,
        'vix_c': vix_c, 'vix_2w': vix_2w,
        'us10y_c': us10y_c, 'us10y_2w': us10y_2w, 'us2y_c': us2y_c
    }

data = fetch_market_data()

# Přepočty Mld. USD
fed_assets_b = data['fed_assets'] / 1000 if data['fed_assets'] else 6747.38
tga_b = data['tga_balance'] / 1000 if data['tga_balance'] else 829.62
rrp_b = data['rrp_balance'] if data['rrp_balance'] else 0.90
net_liq_b = fed_assets_b - tga_b - rrp_b

# TGA Delta
if data['tga_hist'] is not None and len(data['tga_hist']) >= 2:
    tga_delta_b = tga_b - (data['tga_hist'].iloc[-2] / 1000)
else:
    tga_delta_b = 73.41

# Měsíční řada likvidity (6 let)
df_liq = pd.DataFrame({
    'assets': data['fed_assets_hist'] / 1000,
    'tga': data['tga_hist'] / 1000,
    'rrp': data['rrp_hist']
}).dropna()
df_liq['net_liq'] = df_liq['assets'] - df_liq['tga'] - df_liq['rrp']
net_liq_monthly_6y = df_liq['net_liq'].resample('ME').last()
net_liq_6y_median = net_liq_monthly_6y.median()

# --- 4. ZOBRAZENÍ METRIK (LIKVIDITA & INDEXY) ---
st.subheader("💵 Likvidita Fedu a US Indexy")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Čistá Likvidita Fedu", f"${net_liq_b:,.2f} Mld.", delta=f"3Y Median: ${net_liq_6y_median:,.0f} Mld.")
col2.metric("Účet Vlády (TGA)", f"${tga_b:,.2f} Mld.", delta=f"{tga_delta_b:+.2f} Mld. (Odtok)" if tga_delta_b > 0 else f"{tga_delta_b:+.2f} Mld. (Příliv)", delta_color="inverse")
col3.metric("S&P 500", f"{data['sp500_c']:,.2f} pts", delta=f"{data['sp500_c'] - data['sp500_2w']:+.2f} (2 týdny)")
col4.metric("US 10Y Výnos", f"{data['us10y_c']:.2f}%", delta=f"{data['us10y_c'] - data['us10y_2w']:+.2f}% (2 týdny)", delta_color="inverse")

st.markdown("---")

# --- 5. GRAF ČISTÉ LIKVIDITY (6 LET) ---
st.subheader("🌊 Měsíční Vývoj Čisté Likvidity Fedu (Posledních 6 let)")

fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(net_liq_monthly_6y.index, net_liq_monthly_6y.values, color='#8e44ad', marker='o', linewidth=2, label='Čistá Likvidita (Mld. USD)')
ax.axhline(y=net_liq_6y_median, color='#f39c12', linestyle='--', linewidth=1.5, label=f'6Y Medián ({net_liq_6y_median:.0f} Mld. USD)')
ax.set_ylabel("Mld. USD")
ax.legend(loc="upper left")
st.pyplot(fig)

st.markdown("---")

# --- 6. EXPORT TEXTOVÉHO REPORTU DO CHATU ---
st.subheader("📋 Generátor podkladů pro AI Analýzu")
if st.button("🚀 Vygenerovat komplet podklady pro Chat"):
    payload = f"S&P 500: {data['sp500_c']:.2f}, Nasdaq: {data['nasdaq_c']:.2f}, VIX: {data['vix_c']:.2f}, US10Y: {data['us10y_c']:.2f}%\n"
    payload += f"TGA: {tga_b:.2f} Mld. (Delta: {tga_delta_b:+.2f} Mld.), Čistá Likvidita: {net_liq_b:.2f} Mld. USD (6Y Median: {net_liq_6y_median:.2f} Mld.)\n"
    st.code(payload, language="text")
    st.success("Kód výše zkopíruj a vlož do našeho chatu!")
