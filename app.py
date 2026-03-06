import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Eurorama v5.8", page_icon="🖼️")

if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""

st.title("🖼️ Kalkulator Eurorama v5.8")

# Stałe
MARZA = 1.50
VAT = 1.23
DEFAULT_FILE = "cennik.csv"

def clean_code(x):
    if pd.isna(x): return ""
    val = str(x).strip().lower()
    if val.endswith('.0'): val = val[:-2]
    return val

# Funkcja bezpiecznego wczytywania CSV (obsługa polskich znaków)
def load_csv_safe(file_source):
    try:
        # Próba standardowa (UTF-8)
        return pd.read_csv(file_source, header=None, encoding='utf-8')
    except UnicodeDecodeError:
        # Próba dla polskiego Excela (Windows-1250)
        return pd.read_csv(file_source, header=None, encoding='cp1250', sep=None, engine='python')

# --- LOGIKA WCZYTYWANIA ---
st.sidebar.header("Baza Danych")
uploaded_file = st.sidebar.file_uploader("Wgraj nowy cennik", type=['csv', 'xlsx', 'ods'])

source = None
if uploaded_file:
    source = uploaded_file
elif os.path.exists(DEFAULT_FILE):
    source = DEFAULT_FILE
    st.sidebar.info("✅ Korzystam z zapisanego cennika")

if source:
    try:
        # Rozpoznanie typu pliku i wczytanie
        if isinstance(source, str) or source.name.endswith('.csv'):
            df_raw = load_csv_safe(source)
        else:
            df_raw = pd.read_excel(source, header=None)
        
        db = {}
        s_netto, h_netto = 43.0, 30.0

        for _, row in df_raw.iterrows():
            try:
                k = clean_code(row[0])
                if not k or "kolumna" in k or "profil" in k: continue
                
                # Szukamy cen dodatków
                if 'szkło' in k or 'szklo' in k:
                    s_netto = float(str(row[2]).replace(',', '.'))
                    continue
                if 'hdf' in k:
                    h_netto = float(str(row[2]).replace(',', '.'))
                    continue
                
                # Dane ramy
                c = float(str(row[2]).replace(',', '.'))
                sz = float(str(row[4]).replace(',', '.')) if len(row) > 4 and pd.notna(row[4]) else 0.0
                db[k] = {"cena": c, "szer": sz}
            except: continue

        st.sidebar.success(f"Baza: {len(db)} kodów")
        st.sidebar.write(f"Szkło: {s_netto} zł | HDF: {h_netto} zł")
        
        # --- INTERFEJS WYCENY ---
        st.write("---")
        komenda = st.text_input("Podaj kod i wymiary:", key="input_val", placeholder="Mów lub pisz...")
        
        c1, c2 = st.columns(2)
        wycen_btn = c1.button("🚀 WYCENA", use_container_width=True)
        nowa_btn = c2.button("🧹 NOWA WYCENA", on_click=reset_fields, use_container_width=True)

        if (wycen_btn or (st.session_state.input_val and not nowa_btn)) and st.session_state.input_val:
            liczby = re.findall(r'\d+', st.session_state.input_val)
            if len(liczby) >= 2:
                kod_u = liczby[0].lower()
                szer = float(liczby[1])
                wys = float(liczby[2]) if len(liczby) > 2 else szer
                
                if kod_u in db:
                    item = db[kod_u]
                    # Obliczenia
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * item['szer'])) / 100
                    cena_r = (obwod_m * item['cena']) * MARZA * VAT
                    m2 = (szer * wys) / 10000
                    cena_c = cena_r + (m2 * (s_netto + h_netto) * MARZA * VAT)
                    
                    st.divider()
                    st.subheader(f"Wynik dla kodu: {kod_u.upper()}")
                    res1, res2 = st.columns(2)
                    res1.metric("SAMA RAMA", f"{cena_r:.2f} zł")
                    res2.metric("PEŁNA OPRAWA", f"{cena_c:.2f} zł")
                    st.caption(f"Wymiar: {szer}x{wys}cm | Listwa: {item['szer']}cm")
                else:
                    st.error(f"Nie znaleziono kodu {kod_u}")
            
    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")
else:
    st.info("👈 Wgraj plik lub dodaj 'cennik.csv' do GitHub'a.")
