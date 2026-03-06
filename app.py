import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Eurorama Kalkulator", page_icon="🖼️")

# Inicjalizacja pamięci dla pól tekstowych
if 'input_val' not in st.session_state:
    st.session_state.input_val = ""

def reset_fields():
    st.session_state.input_val = ""

st.title("🖼️ Kalkulator Eurorama v5.3")

# Stałe
MARZA = 1.50
VAT = 1.23

# Pomocnicza funkcja do czyszczenia kodów
def clean_code(x):
    if pd.isna(x): return ""
    try:
        # Usuwa .0 jeśli kod jest liczbą
        if isinstance(x, (float, int)):
            return str(int(x)).strip().upper()
    except: pass
    return str(x).strip().upper()

# --- 1. PANEL BOCZNY: CENNIK ---
st.sidebar.header("Baza Danych")
uploaded_file = st.sidebar.file_uploader("Wgraj plik cennika (ODS/XLSX)", type=['ods', 'xlsx'])

if uploaded_file:
    try:
        # Wczytanie pliku bez nagłówków, żeby uniknąć błędu nazw
        engine = 'odf' if uploaded_file.name.endswith('.ods') else None
        df_raw = pd.read_excel(uploaded_file, engine=engine, header=None)
        
        # Tworzymy czystą tabelę na podstawie Twoich wytycznych:
        # Kolumna 1 (0): Kod | Kolumna 3 (2): Cena | Kolumna 5 (4): Szerokość
        clean_data = []
        for _, row in df_raw.iterrows():
            try:
                k = clean_code(row[0])
                # Próba odczytu ceny z 3. kolumny (indeks 2)
                c = float(str(row[2]).replace(',', '.'))
                # Próba odczytu szerokości z 5. kolumny (indeks 4)
                sz = float(str(row[4]).replace(',', '.')) if pd.notna(row[4]) else 0.0
                
                if k:
                    clean_data.append({"KOD": k, "CENA": c, "SZER": sz})
            except:
                continue # Pomiń wiersze, które nie są danymi (np. nagłówki tekstowe)

        df = pd.DataFrame(clean_data)
        
        # Wyciąganie stawek za szkło i HDF
        s_netto = df[df['KOD'].str.contains("SZKŁO|SZKLO", na=False)]['CENA'].mean() or 25.0
        h_netto = df[df['KOD'].str.contains("HDF", na=False)]['CENA'].mean() or 15.0
        
        st.sidebar.success(f"Załadowano {len(df)} kodów")
        st.sidebar.info(f"Szkło: {s_netto} zł | HDF: {h_netto} zł")

        # --- 2. GŁÓWNY PANEL: WYCENA ---
        komenda = st.text_input(
            "Wpisz kod i wymiary (np. 2020 50 60)", 
            key="input_val",
            placeholder="Kliknij mikrofon na klawiaturze i mów"
        )

        c1, c2 = st.columns(2)
        wycen_btn = c1.button("🚀 WYCENA", use_container_width=True)
        nowa_btn = c2.button("🧹 NOWA WYCENA", on_click=reset_fields, use_container_width=True)

        if wycen_btn and komenda:
            liczby = re.findall(r'\d+', komenda)
            if len(liczby) >= 2:
                kod_user = str(liczby[0]).upper()
                szer = float(liczby[1])
                wys = float(liczby[2]) if len(liczby) > 2 else szer
                
                # Szukanie kodu (różne warianty)
                search = df[df['KOD'].isin([kod_user, "0"+kod_user, kod_user.lstrip('0')])]
                
                if not search.empty:
                    item = search.iloc[0]
                    # Logika: Obwód + 8x szerokość
                    obwod_m = ((2 * szer) + (2 * wys) + (8 * item['SZER'])) / 100
                    cena_r = (obwod_m * item['CENA']) * MARZA * VAT
                    
                    # Logika: Szkło i HDF
                    m2 = (szer * wys) / 10000
                    cena_c = cena_r + (m2 * (s_netto + h_netto) * MARZA * VAT)
                    
                    st.divider()
                    st.subheader(f"Wynik dla kodu: {item['KOD']}")
                    res_c1, res_c2 = st.columns(2)
                    res_c1.metric("SAMA RAMA", f"{cena_r:.2f} zł")
                    res_c2.metric("PEŁNA OPRAWA", f"{cena_c:.2f} zł")
                    st.caption(f"Wymiary: {szer}x{wys} cm | Szerokość listwy: {item['SZER']} cm")
                else:
                    st.error(f"Nie znaleziono kodu {kod_user} w cenniku.")
            else:
                st.warning("Podaj minimum kod i szerokość obrazu.")

    except Exception as e:
        st.error(f"Wystąpił błąd podczas przetwarzania pliku: {e}")
else:
    st.info("👈 Aby rozpocząć, wgraj plik cennika w panelu bocznym.")
