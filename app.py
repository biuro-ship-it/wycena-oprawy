import streamlit as st
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="Eurorama Kalkulator", page_icon="🖼️")

st.title("🖼️ Kalkulator Oprawy Eurorama")

# Stałe
MARZA = 1.50
VAT = 1.23

# --- 1. WGRYWANIE CENNIKA ---
uploaded_file = st.sidebar.file_uploader("Wgraj cennik ODS/XLSX", type=['ods', 'xlsx'])

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine='odf' if uploaded_file.name.endswith('.ods') else None)
    # Mapowanie kolumn (Kolumna 0: Kod, 2: Cena, 4: Szerokość)
    df = df.iloc[:, [0, 2, 4]]
    df.columns = ['Kod', 'Cena', 'Szerokosc']
    df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
    
    # Pobranie cen szkła i HDF
    cena_szkla = df[df['Kod'].str.contains("SZKŁO|SZKLO", na=False)]['Cena'].values
    cena_hdf = df[df['Kod'].str.contains("HDF", na=False)]['Cena'].values
    
    s_netto = cena_szkla[0] if len(cena_szkla) > 0 else 25.0
    h_netto = cena_hdf[0] if len(cena_hdf) > 0 else 15.0
    
    st.sidebar.success(f"Cennik załadowany! Szkło: {s_netto}zł, HDF: {h_netto}zł")

    # --- 2. WEJŚCIE DANYCH ---
    # Streamlit na telefonie świetnie obsługuje dyktowanie tekstu bezpośrednio w polu tekstowym
    komenda = st.text_input("Podaj kod i wymiary (np. 3045 50 60)", placeholder="Kliknij ikonę mikrofonu na klawiaturze telefonu i mów")

    if komenda:
        import re
        liczby = re.findall(r'\d+', komenda)
        
        if len(liczby) >= 2:
            kod = liczby[0]
            szer = float(liczby[1])
            wys = float(liczby[2]) if len(liczby) > 2 else szer
            
            # Szukanie w bazie
            row = df[df['Kod'] == kod.upper()]
            if not row.empty:
                c_netto = float(row.iloc[0]['Cena'])
                l_szer = float(row.iloc[0]['Szerokosc'])
                
                # OBLICZENIA
                obwod_m = ((2 * szer) + (2 * wys) + (8 * l_szer)) / 100
                cena_rama = (obwod_m * c_netto) * MARZA * VAT
                
                m2 = (szer * wys) / 10000
                cena_calosc = cena_rama + (m2 * (s_netto + h_netto) * MARZA * VAT)
                
                # WYŚWIETLANIE
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"### 🟦 RAMA\n# {round(cena_rama, 2)} zł")
                with col2:
                    st.error(f"### 🟥 CAŁOŚĆ\n# {round(cena_calosc, 2)} zł")
                    
                st.caption(f"Detale: Kod {kod}, Wymiary {szer}x{wys}cm, Listwa {l_szer}cm szerokości.")
            else:
                st.warning(f"Nie znaleziono kodu: {kod}")
else:
    st.info("👈 Proszę wgrać plik z cennikiem w panelu bocznym.")
