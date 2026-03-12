import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import date

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Eurorama Twój Dostawca Ram", page_icon="🖼️", layout="wide")

# --- 2. PARAMETRY I STYLE ---
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
LOGO_FILE = "logo.png"
HASLO_ADMINA = "Admin123"

if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

def clear_data():
    st.session_state.input_text = ""

# NOWA STYLIZACJA (SZARE TŁO, CZARNA CZCIONKA)
st.markdown("""
    <style>
    .stApp {
        background-color: #f4f4f4;
    }
    .main {
        color: #000000;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        font-weight: bold;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #ffffff;
        text-align: center;
        padding: 10px;
        border-top: 2px solid #1e3a8a;
        z-index: 100;
        color: #000000;
    }
    .price-card {
        border: 1px solid #cccccc;
        padding: 20px;
        border-radius: 15px;
        background-color: #e9ecef;
        color: #000000;
        margin-bottom: 10px;
    }
    .price-card h3, .price-card h2, .price-card p {
        color: #000000 !important;
    }
    h1, h2, h3, p, label, .stMarkdown {
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Wyświetlanie Logo
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=250)

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

# --- 4. FUNKCJE POMOCNICZE ---
def load_db():
    if not os.path.exists(DEFAULT_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_FILE, header=None, sep=None, engine='python', encoding='cp1250')
        data = {}
        for _, row in df.iterrows():
            try:
                k = str(row[0]).strip().lower()
                if k.endswith('.0'): k = k[:-2]
                data[k] = {
                    "cl": float(str(row[2]).replace(',','.')), 
                    "cr": float(str(row[3]).replace(',','.')), 
                    "sz": float(str(row[4]).replace(',','.'))
                }
            except: continue
        return data
    except: return None

def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "WYCENA OPRAWY - EURORAMA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Data: {data['data']}", ln=True)
    pdf.cell(0, 10, f"Kod listwy: {data['kod']}", ln=True)
    pdf.cell(0, 10, f"Format: {data['format']} cm", ln=True)
    pdf.cell(0, 10, f"Opcja: {data['opcja']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"DO ZAPLATY: {data['cena']} PLN", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", '', 10)
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
    uwagi = st.text_area("Uwagi do zamówienia")

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
