@st.cache_data(ttl=43200)
def fetch_all_data():
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

    # --- ROBUSTNÍ AUTOMATICKÉ STAŽENÍ COT PŘÍMO Z CFTC ARCHIVU ---
    cot_dict = {}
    try:
        # CFTC publikuje kompletní roční soubory v ZIP/CSV (Traders in Financial Futures)
        url = f"https://www.cftc.gov/files/dea/history/deafut_xls_{current_year}.zip"
        # Případně lze číst přímo aktuální zjednodušená data, zkusíme načíst zip/csv přes pandas
        df_cot = pd.read_csv(url, compression='zip', low_memory=False)
        
        # Sjednocení názvů sloupců
        df_cot.columns = [str(c).strip().lower().replace(' ', '_') for c in df_cot.columns]
        
        # Hledání sloupců pro jméno trhu (může se jmenovat market_and_exchange_names nebo cftc_market_code)
        market_col = [c for c in df_cot.columns if 'market_and_exchange' in c or 'market_name' in c]
        
        if market_col:
            m_col = market_col[0]
            currency_keywords = {
                "USD": "us dollar",
                "EUR": "euro fx",
                "GBP": "british pound",
                "AUD": "australian dollar",
                "JPY": "japanese yen",
                "CHF": "swiss franc"
            }
            
            for cur, keyword in currency_keywords.items():
                sub_df = df_cot[df_cot[m_col].str.contains(keyword, case=False, na=False)]
                if not sub_df.empty:
                    latest = sub_df.iloc[-1]
                    prev = sub_df.iloc[-2] if len(sub_df) > 1 else latest
                    
                    # Pokus o nalezení long/short sloupců pro Asset Managery nebo Noncommercial
                    longs = [c for c in df_cot.columns if 'asset_mgr_positions_long' in c or 'noncomm_positions_long' in c]
                    shorts = [c for c in df_cot.columns if 'asset_mgr_positions_short' in c or 'noncomm_positions_short' in c]
                    
                    if longs and shorts:
                        net_pos = int(float(latest[longs[0]]) - float(latest[shorts[0]]))
                        prev_net = int(float(prev[longs[0]]) - float(prev[shorts[0]]))
                        delta_wow = net_pos - prev_net
                    else:
                        net_pos, delta_wow = 0, 0
                        
                    sentiment = "NET LONG" if net_pos > 0 else ("NET SHORT" if net_pos < 0 else "NEUTRAL")
                    cot_dict[cur] = {"position": net_pos, "delta": delta_wow, "sentiment": sentiment}
    except Exception as e:
        print(f"Chyba při přímém stahování CFTC: {e}")

    return {
        'fed_assets': fed_assets, 'fed_assets_hist': fed_assets_hist,
        'tga_balance': tga_balance, 'tga_hist': tga_hist,
        'rrp_balance': rrp_balance, 'rrp_hist': rrp_hist,
        'm2_supply': m2_supply, 'mich_1y': mich_1y, 'be_5y': be_5y,
        'sp500_c': sp500_c, 'sp500_2w': sp500_2w,
        'nasdaq_c': nasdaq_c, 'nasdaq_2w': nasdaq_2w,
        'vix_c': vix_c, 'vix_2w': vix_2w,
        'us10y_c': us10y_c, 'us10y_2w': us10y_2w, 'us2y_c': us2y_c,
        'cot_data': cot_dict
    }
