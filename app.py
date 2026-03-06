import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Eurorama v5.7", page_icon="🖼️")

if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""

st.title("🖼️ Kalkulator Eurorama v5.7")

# Stałe
MARZA = 1.50
VAT = 1.23
DEFAULT_FILE = "cennik.csv"  # Nazwa pliku, który wrzucisz na GitHub

def clean_code(x):
    if pd.isna(x): return ""
    val = str(x).strip().lower()
    if val.endswith('.0'): val = val[:-2]
    return val

# --- LOGIKA WCZYTYWANIA ---
st.sidebar.header("Baza Danych")
uploaded_file = st.sidebar.file_uploader("Wgraj nowy cennik (opcjonalnie)", type=['csv', 'xlsx', 'ods'])

# Wybór źródła danych: albo wgrany plik, albo plik z GitHuba
source = None
if uploaded_file:
    source = uploaded_file
elif os.path.exists(DEFAULT_FILE):
    source = DEFAULT_FILE
    st.sidebar.info("✅ Korzystam z zapisanego cennika")

if source:
    try:
        if isinstance(source, str): # Jeśli czytamy z pliku na GitHub
            df_raw = pd.read_csv(source, header=None)
        elif source.name.endswith('.csv'):
            df_raw = pd.read_csv(source, header=None)
        else:
            df_raw = pd.read_excel(source, header=None)
        
        db = {}
        s_netto, h_netto = 43.0, 30.0

        for _, row in df_raw.iterrows():
            try:
                k = clean_code(row[0])
                if not k or "kolumna" in k or "profil" in k: continue
                if 'szkło' in k or 'szklo' in k:
                    s_netto = float(str(row[2]).replace(',', '.'))
                    continue
                if 'hdf' in k:
                    h_netto = float(str(row[2]).replace(',', '.'))
                    continue
                c = float(str(row[2]).replace(',', '.'))
                sz = float(str(row[4]).replace(',', '.')) if len(row) > 4 and pd.notna(row[4]) else 0.0
                db[k] = {"cena": c, "szer": sz}
            except: continue

        st.sidebar.success(f"Baza: {len(db)} kodów")
        
        # --- INTERFEJS WYCENY ---
        st.write("---")
        komenda = st.text_input("Podaj kod i wymiary:", key="input_val", placeholder="Mów lub pisz...")
        
        c1, c2 = st.columns(2)
        if c1.button("🚀 WYCENA", use_container_width=True) and komenda:
            liczby = re.findall(r'\d+', komenda)
            if len(liczby) >= 2:
                kod_u = liczby[0].lower()
                szer, wys = float(liczby[1]), float(liczby[2]) if len(liczby) > 2 else float(liczby[1])
                
                if kod_u in db:
                    item = db[kod_u]
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * item['szer'])) / 100
                    cena_r = (obwod_m * item['cena']) * MARZA * VAT
                    cena_c = cena_r + ((szer * wys) / 10000 * (s_netto + h_netto) * MARZA * VAT)
                    
                    st.divider()
                    st.subheader(f"Wycena: {kod_u.upper()}")
                    res_c1, res_c2 = st.columns(2)
                    res_c1.metric("SAMA RAMA", f"{cena_r:.2f} zł")
                    res_c2.metric("PEŁNA OPRAWA", f"{cena_c:.2f} zł")
                else:
                    st.error(f"Brak kodu {kod_u}")
        
        c2.button("🧹 NOWA", on_click=reset_fields, use_container_width=True)

    except Exception as e:
        st.error(f"Błąd: {e}")
else:
    st.info("👈 Wgraj plik lub dodaj 'cennik.csv' do swojego GitHub'a.")
