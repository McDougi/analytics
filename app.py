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

    # Spolehlivé stahování sazeb a meziroční inflace
    fred_series_mapping = {
        "USD": {"rate": "FEDFUNDS", "cpi": "CPIAUCSL"},
        "EUR": {"rate": "IR3TIB01EZM156N", "cpi": "CP0000EZM159NR"},
        "GBP": {"rate": "IUDSOIA", "cpi": "GBRCPIALLMINMEI"},
        "AUD": {"rate": "IR3TIB01AUM156N", "cpi": "AUSCPIALLQINMEI"},
        "JPY": {"rate": "IR3TIB01JPM156N", "cpi": "JPNCPIALLMINMEI"},
        "CHF": {"rate": "IR3TIB01CHM156N", "cpi": "CHECPIALLMINMEI"}
    }

    macro_global = {}
    for cur, ids in fred_series_mapping.items():
        try:
            rate_val, _ = get_fred(ids["rate"])
            _, cpi_hist = get_fred(ids["cpi"])
            
            # Ošetření výpočtu inflace podle frekvence dat (měsíční vs čtvrtletní)
            if cpi_hist is not None and len(cpi_hist) >= 12:
                # Pokud jde o čtvrtletní data (např. Austrálie), bereme posun o 4 období zpět (QoY)
                shift_val = 4 if cur == "AUD" else 12
                cpi_yoy = ((cpi_hist.iloc[-1] - cpi_hist.iloc[-shift_val]) / cpi_hist.iloc[-shift_val]) * 100
            else:
                cpi_yoy = 2.0
                
            macro_global[cur] = {
                "rate": round(rate_val, 2) if rate_val else 0.0,
                "cpi": round(cpi_yoy, 2)
            }
        except Exception:
            macro_global[cur] = {"rate": 0.0, "cpi": 2.0}

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

    # Robustní načtení aktuálních CoT dat z přímého CSV odkazu CFTC pro daný rok
    cot_dict = {}
    try:
        cot_url = f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{current_year}.zip"
        df_cot = pd.read_csv(cot_url, compression='zip', low_memory=False)
        df_cot.columns = [str(c).strip().lower().replace(' ', '_') for c in df_cot.columns]
        
        market_col = [c for c in df_cot.columns if 'market_and_exchange' in c or 'market_name' in c]
        if market_col:
            m_col = market_col[0]
            currency_keywords = {
                "USD": "us dollar", "EUR": "euro fx", "GBP": "british pound", 
                "AUD": "australian dollar", "JPY": "japanese yen", "CHF": "swiss franc"
            }
            for cur, keyword in currency_keywords.items():
                sub_df = df_cot[df_cot[m_col].str.contains(keyword, case=False, na=False)]
                if not sub_df.empty:
                    latest = sub_df.iloc[-1]
                    prev = sub_df.iloc[-2] if len(sub_df) > 1 else latest
                    
                    longs = [c for c in df_cot.columns if 'asset_mgr_positions_long' in c]
                    shorts = [c for c in df_cot.columns if 'asset_mgr_positions_short' in c]
                    
                    if longs and shorts:
                        net_pos = int(float(latest[longs[0]]) - float(latest[shorts[0]]))
                        prev_net = int(float(prev[longs[0]]) - float(prev[shorts[0]]))
                        delta_wow = net_pos - prev_net
                    else:
                        net_pos, delta_wow = 0, 0
                        
                    sentiment = "NET LONG" if net_pos > 0 else ("NET SHORT" if net_pos < 0 else "NEUTRAL")
                    cot_dict[cur] = {"position": net_pos, "delta": delta_wow, "sentiment": sentiment}
    except Exception as e:
        print(f"Chyba CoT: {e}")

    return {
        'fed_assets': fed_assets, 'fed_assets_hist': fed_assets_hist,
        'tga_balance': tga_balance, 'tga_hist': tga_hist,
        'rrp_balance': rrp_balance, 'rrp_hist': rrp_hist,
        'm2_supply': m2_supply, 'mich_1y': mich_1y, 'be_5y': be_5y,
        'sp500_c': sp500_c, 'sp500_2w': sp500_2w,
        'nasdaq_c': nasdaq_c, 'nasdaq_2w': nasdaq_2w,
        'vix_c': vix_c, 'vix_2w': vix_2w,
        'us10y_c': us10y_c, 'us10y_2w': us10y_2w, 'us2y_c': us2y_c,
        'macro_global': macro_global,
        'cot_data': cot_dict
    }
