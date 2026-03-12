import streamlit as st
import pandas as pd
import re
import os

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Eurorama Twój Dostawca Ram", page_icon="🖼️", layout="wide")

# --- 2. PARAMETRY I HASŁO ---
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
HASLO_ADMINA = "Admin123"  # <--- TWOJE HASŁO

# Inicjalizacja pamięci sesji
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

# POPRAWIONA FUNKCJA CZYSZCZENIA
def clear_data():
    st.session_state.input_text = ""
    # st.rerun() został usunięty, bo Streamlit sam odświeży stronę po wyjściu z tej funkcji

# Stylizacja CSS
st.markdown("""
    <style>
    .main { background-color: #f1f3f6; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    
    .footer { 
        position: fixed; 
        left: 0; 
        bottom: 0; 
        width: 100%; 
        background-color: white; 
        text-align: center; 
        padding: 10px; 
        border-top: 2px solid #1e3a8a; 
        z-index: 100; 
        color: #333; 
    }
    .footer b { color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. PANEL ADMINISTRACYJNY ---
st.sidebar.header("🔐 Panel Administracyjny")
pass_input = st.sidebar.text_input("Hasło", type="password")

if pass_input == HASLO_ADMINA:
    st.sidebar.success("Dostęp przyznany")
    up_file = st.sidebar.file_uploader("Wgraj nowy cennik (CSV)", type=['csv'])
    if up_file:
        with open(DEFAULT_FILE, "wb") as f:
            f.write(up_file.getbuffer())
        st.sidebar.info("Cennik zaktualizowany!")
elif pass_input != "":
    st.sidebar.error("Błędne hasło")

# --- 4. ŁADOWANIE DANYCH ---
def load_db():
    if not os.path.exists(DEFAULT_FILE):
        return None
    try:
        df = pd.read_csv(DEFAULT_FILE, header=None, sep=None, engine='python', encoding='cp1250')
        data = {}
        for _, row in df.iterrows():
            try:
                k = str(row[0]).strip().lower()
                if k.endswith('.0'): k = k[:-2]
                c_l = float(str(row[2]).replace(',', '.'))
                c_r = float(str(row[3]).replace(',', '.'))
                sz = float(str(row[4]).replace(',', '.'))
                data[k] = {"cl": c_l, "cr": c_r, "sz": sz}
            except: continue
        return data
    except: return None

db = load_db()

# --- 5. INTERFEJS GŁÓWNY ---
st.header("🖼️ Eurorama Twój Dostawca Ram")

with st.container():
    col_a, col_b = st.columns([2, 1])
    with col_a:
        # Podpinamy session_state bezpośrednio pod pole
        user_input = st.text_input("Podaj kod i wymiary (np. 34 50 60)", key="input_text")
    
    with col_b:
        st.write("Marże [%]:")
        m_cols = st.columns(2)
        m_l = m_cols[0].number_input("Listwa", value=50)
        m_r = m_cols[1].number_input("Rama", value=35)

with st.expander("💰 Dodatkowe koszty (opcjonalnie)"):
    add_cols = st.columns(2)
    extra_l = add_cols[0].number_input("Koszt do listwy [zł]", value=0.0)
    extra_r = add_cols[1].number_input("Koszt do ramy [zł]", value=0.0)

# PRZYCISKI
btn_col1, btn_col2 = st.columns(2)
do_calc = btn_col1.button("🚀 WYCEŃ", type="primary")
do_clear = btn_col2.button("🧹 NOWA WYCENA", on_click=clear_data)

# --- 6. OBLICZENIA I WYNIKI ---
if do_calc and st.session_state.input_text:
    if not db:
        st.error("Błąd: Cennik nie został wgrany.")
    else:
        nums = re.findall(r'\d+', st.session_state.input_text)
        if len(nums) >= 2:
            kod = nums[0].lower()
            szer = float(nums[1])
            wys = float(nums[2]) if len(nums) > 2 else szer
            
            if kod in db:
                item = db[kod]
                mb_pot = ((2 * szer) + (2 * wys) + (8 * item['sz'])) / 100
                m2_pow = (szer * wys) / 10000
                
                st.info(f"### Dane materiałowe: {kod.upper()} | {szer}x{wys} cm")
                m_res1, m_res2 = st.columns(2)
                m_res1.write(f"📏 **Potrzebna listwa:** {mb_pot:.2f} mb")
                m_res2.write(f"⬜ **Powierzchnia obrazu:** {m2_pow:.4f} m²")

                # Kalkulacja
                c_p_l = (mb_pot * item['cl']) * VAT
                c_p_r = (mb_pot * item['cr']) * VAT
                
                c_k_l = (c_p_l * (1 + m_l/100)) + extra_l
                c_k_r = (c_p_r * (1 + m_r/100)) + extra_r

                st.divider()
                res_l, res_r = st.columns(2)
                with res_l:
                    st.markdown("### 📦 CENA: LISTWA")
                    st.write(f"Producent (+VAT): {c_p_l:.2f} zł")
                    st.success(f"## **DO ZAPŁATY: {c_k_l:.2f} zł**")
                with res_r:
                    st.markdown("### 🖼️ CENA: W RAMIE")
                    st.write(f"Producent (+VAT): {c_p_r:.2f} zł")
                    st.error(f"## **DO ZAPŁATY: {c_k_r:.2f} zł**")
            else:
                st.error(f"Nie znaleziono kodu {kod}")

# --- 7. STOPKA ---
st.markdown(f"""
    <div class="footer">
        <p style="margin:0; font-size:1.1em;">📞 Zadzwoń do nas: <b>15 876 30 16</b></p>
    </div>
    """, unsafe_allow_html=True)
