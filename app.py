import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Eurorama v5.9", page_icon="🖼️")

if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""

st.title("🖼️ Kalkulator Eurorama v5.9")

# Stałe
MARZA = 1.50
VAT = 1.23
DEFAULT_FILE = "cennik.csv"

def clean_code(x):
    if pd.isna(x): return ""
    val = str(x).strip().lower()
    if val.endswith('.0'): val = val[:-2]
    return val

# Funkcja super-bezpiecznego wczytywania CSV
def load_csv_safe(file_source):
    # Lista kodowań do wypróbowania
    encodings = ['utf-8', 'cp1250', 'iso-8859-2']
    
    for enc in encodings:
        try:
            # sep=None i engine='python' sprawiają, że pandas sam zgaduje czy to , czy ; czy tabulator
            return pd.read_csv(file_source, header=None, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
        except:
            continue
    raise Exception("Nie udało się rozpoznać formatu pliku CSV. Spróbuj zapisać go jako XLSX.")

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
        if (isinstance(source, str) and source.endswith('.csv')) or (not isinstance(source, str) and source.name.endswith('.csv')):
            df_raw = load_csv_safe(source)
        else:
            df_raw = pd.read_excel(source, header=None)
        
        db = {}
        # Domyślne ceny jeśli nie znajdzie w pliku
        s_netto, h_netto = 43.0, 30.0

        for _, row in df_raw.iterrows():
            try:
                # Sprawdzamy czy wiersz ma dane (co najmniej kod i cenę)
                if len(row) < 3: continue
                
                k = clean_code(row[0])
                if not k or "kolumna" in k or "profil" in k: continue
                
                # Pobranie ceny (kolumna 3 -> indeks 2)
                c_raw = str(row[2]).replace(',', '.').replace(' zł', '').strip()
                c = float(c_raw)

                # Specyficzne dla Szkła i HDF
                if 'szkło' in k or 'szklo' in k:
                    s_netto = c
                    continue
                if 'hdf' in k:
                    h_netto = c
                    continue
                
                # Szerokość listwy (kolumna 5 -> indeks 4)
                sz = 0.0
                if len(row) >= 5 and pd.notna(row[4]):
                    sz = float(str(row[4]).replace(',', '.'))
                
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
                    # Obliczenia: (Obwód + 8x szerokość) * cena
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * item['szer'])) / 100
                    cena_r = (obwod_m * item['cena']) * MARZA * VAT
                    
                    # Szkło + HDF
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
        st.error(f"Wystąpił problem: {e}")
else:
    st.info("👈 Wgraj plik lub dodaj 'cennik.csv' do GitHub'a.")
