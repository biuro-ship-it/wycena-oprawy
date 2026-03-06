import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Eurorama Kalkulator", page_icon="🖼️")

# --- MECHANIZM RESETOWANIA ---
# Inicjalizacja klucza w pamięci sesji, jeśli nie istnieje
if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""
    # Streamlit automatycznie odświeży stronę po zmianie stanu

st.title("🖼️ Kalkulator Eurorama v5.2")

# --- PARAMETRY STAŁE ---
MARZA = 1.50
VAT = 1.23

def clean_code(x):
    if pd.isna(x): return ""
    try:
        if isinstance(x, (float, int)):
            return str(int(x)).strip().upper()
    except: pass
    return str(x).strip().upper()

# --- 1. BOCZNY PANEL: WGRYWANIE ---
st.sidebar.header("Ustawienia")
uploaded_file = st.sidebar.file_uploader("Wgraj cennik ODS/XLSX", type=['ods', 'xlsx'])

if uploaded_file:
    try:
        engine = 'odf' if uploaded_file.name.endswith('.ods') else None
        df_raw = pd.read_excel(uploaded_file, engine=engine, header=None)
        
        data = []
        for index, row in df_raw.iterrows():
            try:
                kod = clean_code(row[0])
                cena = float(str(row[2]).replace(',', '.'))
                szer = float(str(row[4]).replace(',', '.')) if pd.notna(row[4]) else 0.0
                if kod: data.append({"Kod": kod, "Cena": cena, "Szerokosc": szer})
            except: continue
        
        df = pd.DataFrame(data)
        
        # Pobranie stawek za szkło i HDF
        s_netto = df[df['Kod'].str.contains("SZKŁO|SZKLO", na=False)]['Cena'].mean() or 25.0
        h_netto = df[df['Kod'].str.contains("HDF", na=False)]['Cena'].mean() or 15.0
        
        st.sidebar.success(f"Baza aktywna: {len(df)} pozycji")

        # --- 2. GŁÓWNY PANEL: WPISYWANIE ---
        st.write("---")
        
        # Używamy st.text_input połączonego z session_state
        komenda = st.text_input(
            "Wpisz/Powiedz: Kod Szerokość Wysokość", 
            key="input_val", 
            placeholder="np. 2020 50 60"
        )

        col_btn1, col_btn2 = st.columns([1, 1])
        
        # Przycisk WYCENA
        wycen_pressed = col_btn1.button("🚀 WYCENA", use_container_width=True)
        
        # Przycisk NOWA WYCENA (czyści pola)
        col_btn2.button("🧹 NOWA WYCENA", on_click=reset_fields, use_container_width=True)

        if wycen_pressed and komenda:
            liczby = re.findall(r'\d+', komenda)
            
            if len(liczby) >= 2:
                kod_input = str(liczby[0]).upper()
                szer = float(liczby[1])
                wys = float(liczby[2]) if len(liczby) > 2 else szer
                
                # Szukanie kodu
                warianty = [kod_input, "0" + kod_input, kod_input.lstrip('0')]
                wynik = df[df['Kod'].isin(warianty)]
                
                if not wynik.empty:
                    p = wynik.iloc[0]
                    # Obliczenia
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * p['Szerokosc'])) / 100
                    c_rama = (obwod_m * p['Cena']) * MARZA * VAT
                    
                    m2 = (szer * wys) / 10000
                    c_calosc = c_rama + (m2 * (s_netto + h_netto) * MARZA * VAT)
                    
                    # WYNIKI
                    st.success(f"### Wynik dla kodu: **{p['Kod']}**")
                    r1, r2 = st.columns(2)
                    r1.metric("SAMA RAMA", f"{c_rama:.2f} zł")
                    r2.metric("PEŁNA OPRAWA", f"{c_calosc:.2f} zł")
                    st.caption(f"Wymiar: {szer}x{wys}cm | Listwa: {p['Szerokosc']}cm szerokości")
                else:
                    st.error(f"Nie znaleziono kodu: {kod_input}")
            else:
                st.warning("Podaj minimum kod i szerokość.")

    except Exception as e:
        st.error(f"Błąd cennika: {e}")
else:
    st.info("👈 Wgraj cennik w panelu bocznym.")
