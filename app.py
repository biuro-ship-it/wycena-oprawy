import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Eurorama v6.1", page_icon="🖼️", layout="centered")

# Inicjalizacja pamięci sesji (dla przycisku Nowa Wycena)
if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""

st.title("🖼️ Kalkulator Eurorama v6.1")

# Stałe
MARZA = 1.50
VAT = 1.23
DEFAULT_FILE = "cennik.csv" # Wrzuć plik o tej nazwie na GitHub, aby ładował się sam

def clean_code(x):
    if pd.isna(x) or str(x).strip() == "": return ""
    val = str(x).strip().lower()
    if val.endswith('.0'): val = val[:-2] # Usuwa .0 z kodów liczbowych
    return val

# Funkcja bezpiecznego wczytywania CSV
def load_data(source):
    encodings = ['utf-8', 'cp1250', 'iso-8859-2']
    for enc in encodings:
        try:
            # Automatyczne wykrywanie separatora (, lub ;)
            return pd.read_csv(source, header=None, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
        except: continue
    return pd.read_excel(source, header=None)

# --- ŁADOWANIE DANYCH ---
st.sidebar.header("Baza Danych")
uploaded_file = st.sidebar.file_uploader("Zmień cennik (CSV/XLSX)", type=['csv', 'xlsx', 'ods'])

source = uploaded_file if uploaded_file else (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None)

if source:
    try:
        df_raw = load_data(source)
        db = {}
        s_netto, h_netto = 0.0, 0.0

        for _, row in df_raw.iterrows():
            try:
                # Kolumna 0: Kod | Kolumna 2: Cena | Kolumna 4: Szerokość
                k = clean_code(row[0])
                if not k or "kolumna" in k or "profil" in k: continue

                # Pobranie ceny i czyszczenie znaków
                c_raw = str(row[2]).replace(',', '.').replace(' zł', '').strip()
                c = float(c_raw)

                # Wyłapywanie cen Szkła i HDF
                if 'szkło' in k or 'szklo' in k:
                    s_netto = c
                    continue
                if 'hdf' in k:
                    h_netto = c
                    continue
                
                # Szerokość (Indeks 4)
                sz = float(str(row[4]).replace(',', '.')) if len(row) > 4 and pd.notna(row[4]) else 0.0
                db[k] = {"cena": c, "szer": sz}
            except: continue

        if source == DEFAULT_FILE:
            st.sidebar.success("✅ Wczytano automatycznie cennik.csv")
        else:
            st.sidebar.success(f"✅ Wczytano {len(db)} pozycji")
        
        st.sidebar.write(f"Ceny netto: Szkło **{s_netto}** zł, HDF **{h_netto}** zł")

        # --- INTERFEJS WYCENY ---
        st.write("---")
        komenda = st.text_input("Podaj kod i wymiary (np. 34 50 60):", key="input_val", placeholder="Dyktuj lub wpisz...")

        c1, c2 = st.columns(2)
        wycen_btn = c1.button("🚀 WYCENA", use_container_width=True)
        nowa_btn = c2.button("🧹 NOWA WYCENA", on_click=reset_fields, use_container_width=True)

        input_text = st.session_state.input_val
        if (wycen_btn or (input_text and not nowa_btn)) and input_text:
            liczby = re.findall(r'\d+', input_text)
            if len(liczby) >= 2:
                kod_u = liczby[0].lower().lstrip('0') or "0"
                szer = float(liczby[1])
                wys = float(liczby[2]) if len(liczby) > 2 else szer
                
                if kod_u in db:
                    item = db[kod_u]
                    
                    # LOGIKA 1: SAMA RAMA (Niebieska)
                    # (Obwód + 8x szerokość na skosy) / 100 * Cena * Marża * VAT
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * item['szer'])) / 100
                    cena_rama = (obwod_m * item['cena']) * MARZA * VAT
                    
                    # LOGIKA 2: PEŁNA OPRAWA (Czerwona)
                    # Cena ramy + (Powierzchnia m2 * CenaSzkła+HDF * Marża * VAT)
                    m2 = (szer * wys) / 10000
                    cena_dodatki = (m2 * (s_netto + h_netto) * MARZA * VAT)
                    cena_calosc = cena_rama + cena_dodatki
                    
                    st.divider()
                    st.subheader(f"Wycena: Profil {kod_u.upper()}")
                    res1, res2 = st.columns(2)
                    res1.metric("SAMA RAMA", f"{cena_rama:.2f} zł")
                    res2.metric("PEŁNA OPRAWA", f"{cena_calosc:.2f} zł")
                    st.caption(f"Detale: Obraz {szer}x{wys}cm | Szerokość profilu: {item['szer']}cm")
                else:
                    st.error(f"Brak kodu {kod_u} w bazie. Sprawdź cennik.")
            else:
                st.warning("Wpisz kod i przynajmniej jeden wymiar (np: 34 50 60).")

    except Exception as e:
        st.error(f"Błąd krytyczny pliku: {e}")
else:
    st.info("👈 Wgraj plik cennika w panelu bocznym lub dodaj 'cennik.csv' do swojego GitHub'a.")
