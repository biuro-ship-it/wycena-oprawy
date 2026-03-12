import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Eurorama Twój Dostawca Ram", page_icon="🖼️", layout="wide")

# --- 2. PARAMETRY I LOGO ---
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
LOGO_FILE = "logo.png" # Wrzuć plik logo.png na GitHub
HASLO_ADMINA = "Admin123"

if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

def clear_data():
    st.session_state.input_text = ""

# Stylizacja CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; text-align: center; padding: 10px; border-top: 2px solid #1e3a8a; z-index: 100; color: #333; }
    .footer b { color: #1e3a8a; }
    .price-card { border: 1px solid #ddd; padding: 20px; border-radius: 15px; background: #fff; }
    </style>
    """, unsafe_allow_html=True)

# Wyświetlanie Logo
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=200)

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

# --- 4. FUNKCJE ---
def load_db():
    if not os.path.exists(DEFAULT_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_FILE, header=None, sep=None, engine='python', encoding='cp1250')
        data = {}
        for _, row in df.iterrows():
            try:
                k = str(row[0]).strip().lower()
                if k.endswith('.0'): k = k[:-2]
                data[k] = {"cl": float(str(row[2]).replace(',','.')), "cr": float(str(row[3]).replace(',','.')), "sz": float(str(row[4]).replace(',','.'))}
            except: continue
        return data
    except: return None

def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arial', '', 'C:/Windows/Fonts/arial.ttf', unicode=True) # Standardowo Streamlit używa czcionek systemowych, w chmurze użyjemy domyślnych
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "WYCENA OPRAWY - EURORAMA", ln=True, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Data: {data['data']}", ln=True)
    pdf.cell(0, 10, f"Listwa: {data['kod']}", ln=True)
    pdf.cell(0, 10, f"Format: {data['format']} cm", ln=True)
    pdf.cell(0, 10, f"Opcja: {data['opcja']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"DO ZAPŁATY: {data['cena']} PLN", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'I', 10)
    pdf.multi_cell(0, 10, f"Uwagi: {data['uwagi']}")
    return pdf.output()

db = load_db()

# --- 5. INTERFEJS GŁÓWNY ---
st.header("Eurorama Twój Dostawca Ram")

with st.container():
    c_a, c_b = st.columns([2, 1])
    with c_a:
        user_input = st.text_input("Podaj kod i wymiary (np. 34 50 60)", key="input_text")
    with c_b:
        wycena_data = st.date_input("Data wyceny", date.today())

m_cols = st.columns(2)
m_l = m_cols[0].number_input("Marża Listwa [%]", value=50)
m_r = m_cols[1].number_input("Marża Rama [%]", value=35)

with st.expander("💰 Dodatki i Uwagi"):
    e_col1, e_col2 = st.columns(2)
    extra_l = e_col1.number_input("Dodatek Listwa [zł]", value=0.0)
    extra_r = e_col2.number_input("Dodatek Rama [zł]", value=0.0)
    uwagi = st.text_area("Uwagi do zamówienia", placeholder="Np. termin realizacji, rodzaj szkła...")

b_col1, b_col2 = st.columns(2)
do_calc = b_col1.button("🚀 WYCEŃ", type="primary")
b_col2.button("🧹 NOWA WYCENA", on_click=clear_data)

# --- 6. WYNIKI ---
if do_calc and st.session_state.input_text:
    if db:
        nums = re.findall(r'\d+', st.session_state.input_text)
        if len(nums) >= 2:
            kod = nums[0].lower()
            szer, wys = float(nums[1]), (float(nums[2]) if len(nums) > 2 else float(nums[1]))
            
            if kod in db:
                item = db[kod]
                mb = ((2*szer)+(2*wys)+(8*item['sz']))/100
                m2 = (szer*wys)/10000
                
                c_p_l = (mb * item['cl']) * VAT
                c_p_r = (mb * item['cr']) * VAT
                f_l = round((c_p_l * (1 + m_l/100)) + extra_l, 2)
                f_r = round((c_p_r * (1 + m_r/100)) + extra_r, 2)

                st.info(f"Materiał: {mb:.2f} mb | Powierzchnia: {m2:.4f} m²")
                
                res_l, res_r = st.columns(2)
                
                # OPCJA LISTWA
                with res_l:
                    st.markdown(f"<div class='price-card'><h3>📦 LISTWA</h3><h2>{f_l} zł</h2></div>", unsafe_allow_html=True)
                    if st.button("Wybierz Listwę"):
                        msg = f"Eurorama: Wycena z dnia {wycena_data}. Listwa {kod.upper()}, {szer}x{wys}cm. Do zaplaty: {f_l}zl. Uwagi: {uwagi}"
                        st.text_area("Treść do SMS:", value=msg)
                        pdf_bytes = generate_pdf({'data': wycena_data, 'kod': kod.upper(), 'format': f"{szer}x{wys}", 'opcja': 'Sama Listwa', 'cena': f_l, 'uwagi': uwagi})
                        st.download_button("📥 Pobierz PDF", data=pdf_bytes, file_name=f"wycena_{kod}.pdf", mime="application/pdf")

                # OPCJA RAMA
                with res_r:
                    st.markdown(f"<div class='price-card'><h3>🖼️ W RAMIE</h3><h2>{f_r} zł</h2></h2></div>", unsafe_allow_html=True)
                    if st.button("Wybierz Ramę"):
                        msg = f"Eurorama: Wycena z dnia {wycena_data}. Rama {kod.upper()}, {szer}x{wys}cm. Do zaplaty: {f_r}zl. Uwagi: {uwagi}"
                        st.text_area("Treść do SMS:", value=msg)
                        pdf_bytes = generate_pdf({'data': wycena_data, 'kod': kod.upper(), 'format': f"{szer}x{wys}", 'opcja': 'Gotowa Rama', 'cena': f_r, 'uwagi': uwagi})
                        st.download_button("📥 Pobierz PDF", data=pdf_bytes, file_name=f"wycena_{kod}.pdf", mime="application/pdf")
            else: st.error("Brak kodu")
        else: st.warning("Podaj kod i wymiary")

st.markdown(f"<div class='footer'><p>📞 Zadzwoń do nas: <b>15 876 30 16</b></p></div>", unsafe_allow_html=True)
