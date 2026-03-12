import streamlit as st
import pandas as pd
import re
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Eurorama - Kalkulator", page_icon="🖼️", layout="wide")

# --- PARAMETRY I STAŁE ---
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
HASLO_ADMINA = "Daniel"  # <--- ZMIEŃ TO HASŁO NA WŁASNE

# Style CSS dla lepszego wyglądu
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; text-align: center; padding: 10px; border-top: 1px solid #ddd; z-index: 100; }
    </style>
    """, unsafe_allow_html=True)

st.title("🖼️ Eurorama Twój Dostawca Ram")

# --- FUNKCJE POMOCNICZE ---
def clean_code(x):
    if pd.isna(x) or str(x).strip() == "": return ""
    val = str(x).strip().lower()
    if val.endswith('.0'): val = val[:-2]
    return val

def load_data(source):
    encodings = ['utf-8', 'cp1250', 'iso-8859-2']
    for enc in encodings:
        try:
            return pd.read_csv(source, header=None, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
        except: continue
    return pd.read_excel(source, header=None)

# --- PANEL ADMINISTRACYJNY (HASŁO) ---
st.sidebar.header("🔐 Panel Admina")
haslo_input = st.sidebar.text_input("Hasło dostępu", type="password")

if haslo_input == HASLO_ADMINA:
    st.sidebar.success("Zalogowano pomyślnie")
    uploaded_file = st.sidebar.file_uploader("Zaktualizuj cennik (CSV/XLSX)", type=['csv', 'xlsx'])
    if uploaded_file:
        with open(DEFAULT_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.info("Plik zapisany jako bazowy cennik.")
else:
    if haslo_input != "":
        st.sidebar.error("Błędne hasło")

# --- ŁADOWANIE CENNIKA ---
source = DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None
db = {}

if source:
    try:
        df_raw = load_data(source)
        for _, row in df_raw.iterrows():
            try:
                k = clean_code(row[0])
                if not k or "kolumna" in k or "profil" in k: continue
                # Kolumna 2: Cena mb listwa | Kolumna 3: Cena mb rama | Kolumna 4: Szerokość profilu
                c_listwa = float(str(row[2]).replace(',', '.').strip())
                c_rama = float(str(row[3]).replace(',', '.').strip())
                szer = float(str(row[4]).replace(',', '.').strip()) if len(row) > 4 else 0.0
                db[k] = {"cena_listwa": c_listwa, "cena_rama": c_rama, "szer": szer}
            except: continue
    except Exception as e:
        st.error(f"Problem z bazą: {e}")

# --- INTERFEJS WYCENY ---
if db:
    # 1. Wprowadzanie danych
    st.subheader("🛠️ Parametry oprawy")
    col_inp1, col_inp2 = st.columns(2)
    
    with col_inp1:
        komenda = st.text_input("Dyktuj kod i wymiary (np. 34 50x60)", placeholder="Kod i wymiary w cm...")
    
    with col_inp2:
        st.write("Dostosuj marże [%]:")
        cm1, cm2 = st.columns(2)
        marza_listwa = cm1.number_input("Marża Listwa", value=50)
        marza_rama = cm2.number_input("Marża Rama", value=35)

    with st.expander("➕ Koszty dodatkowe (np. szkło, transport)"):
        cad1, cad2 = st.columns(2)
        dodatek1 = cad1.number_input("Dodatek do listwy [zł]", value=0.0)
        dodatek2 = cad2.number_input("Dodatek do ramy [zł]", value=0.0)

    # 2. Obliczenia
    if komenda:
        liczby = re.findall(r'\d+', komenda)
        if len(liczby) >= 2:
            kod_u = liczby[0].lower().lstrip('0') or "0"
            szer_ob = float(liczby[1])
            wys_ob = float(liczby[2]) if len(liczby) > 2 else szer_ob
            
            if kod_u in db:
                item = db[kod_u]
                
                # MATERIAŁY
                total_mb = ((2 * szer_ob) + (2 * wys_ob) + (8 * item['szer'])) / 100
                total_m2 = (szer_ob * wys_ob) / 10000
                
                st.success(f"### Obliczenia dla: Profil {kod_u.upper()} | {szer_ob} x {wys_ob} cm")
                
                # Wyświetlanie ilości materiału
                m_col1, m_col2 = st.columns(2)
                m_col1.write(f"📏 **Potrzebna listwa:** {total_mb:.2f} mb")
                m_col2.write(f"⬜ **Powierzchnia obrazu:** {total_m2:.3f} m²")

                # KALKULACJE CENOWE
                # Ceny u producenta + VAT 23%
                prod_listwa_brutto = (total_mb * item['cena_listwa']) * VAT
                prod_rama_brutto = (total_mb * item['cena_rama']) * VAT
                
                # Ceny końcowe (z marżą i dodatkami)
                final_listwa = (prod_listwa_brutto * (1 + marza_listwa/100)) + dodatek1
                final_rama = (prod_rama_brutto * (1 + marza_rama/100)) + dodatek2

                st.divider()
                
                # TABELA WYNIKÓW
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    st.subheader("📦 Opcja: SAMA LISTWA")
                    st.write(f"Cena producenta (z VAT): **{prod_listwa_brutto:.2f} zł**")
                    st.metric("DO ZAPŁATY (Twoja cena)", f"{final_listwa:.2f} zł", delta=f"Marża {marza_listwa}%")
                    
                with res_col2:
                    st.subheader("🖼️ Opcja: GOTOWA RAMA")
                    st.write(f"Cena producenta (z VAT): **{prod_rama_brutto:.2f} zł**")
                    st.metric("DO ZAPŁATY (Twoja cena)", f"{final_rama:.2f} zł", delta=f"Marża {marza_rama}%")
            else:
                st.error(f"Nie znaleziono kodu {kod_u} w bazie.")
else:
    st.warning("Zaloguj się do panelu admina i wgraj plik cennik.csv")

# --- STOPKA ---
st.markdown(f"""
    <div class="footer">
        <p>📞 Zadzwoń do nas: <b>15 876 30 16</b></p>
    </div>
    """, unsafe_allow_html=True)
