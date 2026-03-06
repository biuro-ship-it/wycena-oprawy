import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Eurorama v5.6", page_icon="🖼️")

# Inicjalizacja pamięci sesji (czyszczenie pól)
if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""

st.title("🖼️ Kalkulator Eurorama v5.6")

# Stałe (Marża i VAT)
MARZA = 1.50
VAT = 1.23

# Funkcja czyszcząca kody
def clean_code(x):
    if pd.isna(x): return ""
    # Usuwa .0 jeśli Excel zrobił z kodu liczbę
    val = str(x).strip().lower()
    if val.endswith('.0'): val = val[:-2]
    return val

# --- PANEL BOCZNY: CENNIK ---
st.sidebar.header("Baza Danych")
uploaded_file = st.sidebar.file_uploader("Wgraj plik (cennik eurorama.xlsx - Arkusz1.csv)", type=['csv', 'xlsx', 'ods'])

if uploaded_file:
    try:
        # Wczytanie CSV lub Excel
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None)
        
        db = {}
        s_netto = 43.0 # Domyślna cena szkła
        h_netto = 30.0 # Domyślna cena HDF

        for _, row in df_raw.iterrows():
            try:
                # Kolumna 0 to KOD/Nazwa
                k = clean_code(row[0])
                if not k or "kolumna" in k or "profil" in k: continue

                # Wyłapywanie cen Szkła i HDF
                if 'szkło' in k or 'szklo' in k:
                    s_netto = float(str(row[2]).replace(',', '.'))
                    continue
                if 'hdf' in k:
                    h_netto = float(str(row[2]).replace(',', '.'))
                    continue

                # Cena (Indeks 2), Szerokość (Indeks 4)
                c = float(str(row[2]).replace(',', '.'))
                sz = float(str(row[4]).replace(',', '.')) if len(row) > 4 and pd.notna(row[4]) else 0.0
                
                db[k] = {"cena": c, "szer": sz}
            except:
                continue

        st.sidebar.success(f"Baza: {len(db)} kodów")
        st.sidebar.info(f"Szkło: {s_netto} zł | HDF: {h_netto} zł")

        # --- GŁÓWNY PANEL: WYCENA ---
        komenda = st.text_input("Podaj kod i wymiary (np. 34 50 60):", key="input_val", placeholder="Mów lub pisz...")
        
        c1, c2 = st.columns(2)
        wycen_btn = c1.button("🚀 WYCENA", use_container_width=True)
        nowa_btn = c2.button("🧹 NOWA WYCENA", on_click=reset_fields, use_container_width=True)

        if wycen_btn and komenda:
            liczby = re.findall(r'\d+', komenda)
            if len(liczby) >= 2:
                kod_u = liczby[0].lower()
                szer = float(liczby[1])
                wys = float(liczby[2]) if len(liczby) > 2 else szer
                
                # Szukanie w bazie
                if kod_u in db:
                    item = db[kod_u]
                    
                    # Logika: Obwód + 8x szerokość (odpad na skosy)
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * item['szer'])) / 100
                    cena_rama = (obwod_m * item['cena']) * MARZA * VAT
                    
                    # Logika: Pole powierzchni m2
                    m2 = (szer * wys) / 10000
                    cena_calosc = cena_rama + (m2 * (s_netto + h_netto) * MARZA * VAT)
                    
                    # Wyświetlanie wyników
                    st.divider()
                    st.subheader(f"Wycena dla kodu: {kod_u.upper()}")
                    res_c1, res_c2 = st.columns(2)
                    res_c1.metric("SAMA RAMA", f"{cena_rama:.2f} zł")
                    res_c2.metric("PEŁNA OPRAWA", f"{cena_calosc:.2f} zł")
                    st.caption(f"Wymiary: {szer}x{wys} cm | Szerokość listwy: {item['szer']} cm")
                else:
                    st.error(f"Nie znaleziono kodu {kod_u} w bazie danych.")
            else:
                st.warning("Podaj minimum kod i szerokość obrazu.")

    except Exception as e:
        st.error(f"Błąd pliku: {e}")
else:
    st.info("👈 Wgraj plik cennika w panelu bocznym.")
