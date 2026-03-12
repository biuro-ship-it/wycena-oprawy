import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import date
import urllib.parse

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Eurorama v8.6", page_icon="🖼️", layout="wide")

VAT = 1.23
DEFAULT_FILE = "cennik.csv"
LOGO_FILE = "logo.png"
HASLO_ADMINA = "Admin123"

# Inicjalizacja pamięci sesji
if 'calc_done' not in st.session_state: st.session_state.calc_done = False
if 'results' not in st.session_state: st.session_state.results = {}
if 'input_text' not in st.session_state: st.session_state.input_text = ""
if 'notes' not in st.session_state: st.session_state.notes = ""

def reset_all():
    st.session_state.calc_done = False
    st.session_state.results = {}
    st.session_state.input_text = ""
    st.session_state.notes = ""

# --- 2. STYLIZACJA (DARK MODE) ---
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e; color: #ffffff; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #2d2d2d !important; color: #ffffff !important; border: 1px solid #444 !important;
    }
    .price-card {
        border: 2px solid #0e63d1; padding: 20px; border-radius: 15px; background-color: #2d2d2d;
        color: #ffffff; text-align: center; margin-bottom: 10px;
    }
    .sms-btn {
        display: inline-block; padding: 10px 20px; background-color: #25d366; color: white !important;
        text-decoration: none; border-radius: 10px; font-weight: bold; width: 100%; text-align: center;
    }
    h1, h2, h3, p, label, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# Wyświetlanie Logo na start
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=250)

# --- 3. FUNKCJE ---
def load_db():
    if not os.path.exists(DEFAULT_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_FILE, header=None, sep=None, engine='python', encoding='cp1250', on_bad_lines='skip')
        data = {}
        for _, row in df.iterrows():
            try:
                k = str(row[0]).strip().lower()
                if k == "" or "profil" in k: continue
                if k.endswith('.0'): k = k[:-2]
                data[k] = {"cl": float(str(row[2]).replace(',','.')), "cr": float(str(row[3]).replace(',','.')), "sz": float(str(row[4]).replace(',','.'))}
            except: continue
        return data
    except: return None

def create_pdf(d):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "WYCENA OPRAWY - EURORAMA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("helvetica", '', 12)
    pdf.cell(0, 10, f"Data: {d['data']}", ln=True)
    pdf.cell(0, 10, f"Kod listwy: {d['kod']}", ln=True)
    pdf.cell(0, 10, f"Format: {d['format']} cm", ln=True)
    pdf.cell(0, 10, f"Opcja: {d['opcja']}", ln=True)
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, f"DO ZAPLATY: {d['cena']} PLN", ln=True)
    pdf.ln(10)
    pdf.set_font("helvetica", 'I', 10)
    pdf.multi_cell(0, 10, f"Uwagi: {d['uwagi']}")
    return pdf.output()

db = load_db()

# --- 4. PANEL ADMINA ---
st.sidebar.header("🔐 Admin")
pw = st.sidebar.text_input("Hasło", type="password")
if pw == HASLO_ADMINA:
    up = st.sidebar.file_uploader("Wgraj cennik CSV", type=['csv'])
    if up:
        with open(DEFAULT_FILE, "wb") as f: f.write(up.getbuffer())
        st.sidebar.success("Plik zapisany!")

# --- 5. INTERFEJS GŁÓWNY ---
st.header("Eurorama Twój Dostawca Ram")

col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    user_input = st.text_input("Kod i wymiary (np. 34 50 60)", key="input_text")
with col_in2:
    wycena_date = st.date_input("Data wyceny", date.today())

m_col1, m_col2 = st.columns(2)
mar_l = m_col1.number_input("Marża Listwa [%]", value=50)
mar_r = m_col2.number_input("Marża Rama [%]", value=35)

with st.expander("💰 Dodatki i Uwagi"):
    ex_l = st.number_input("Dodatek Listwa [zł]", value=0.0)
    ex_r = st.number_input("Dodatek Rama [zł]", value=0.0)
    # Zapisujemy uwagi do session_state, by nie zniknęły przy wyborze opcji
    st.session_state.notes = st.text_area("Uwagi do wyceny", value=st.session_state.notes)

c_btn1, c_btn2 = st.columns(2)
if c_btn1.button("🚀 WYCEŃ", type="primary"):
    if db:
        nums = re.findall(r'\d+', user_input)
        if len(nums) >= 2:
            k = nums[0].lower()
            s, w = float(nums[1]), (float(nums[2]) if len(nums) > 2 else float(nums[1]))
            if k in db:
                item = db[k]
                mb = ((2*s)+(2*w)+(8*item['sz']))/100
                c_p_l = (mb * item['cl']) * VAT
                c_p_r = (mb * item['cr']) * VAT
                
                st.session_state.results = {
                    'kod': k.upper(), 's': s, 'w': w, 'mb': mb,
                    'prod_l': round(c_p_l, 2), 'prod_r': round(c_p_r, 2),
                    'f_l': round((c_p_l * (1 + mar_l/100)) + ex_l, 2),
                    'f_r': round((c_p_r * (1 + mar_r/100)) + ex_r, 2)
                }
                st.session_state.calc_done = True
            else: st.error("Nie znaleziono kodu!")
        else: st.warning("Wpisz kod i wymiary!")

if c_btn2.button("🧹 NOWA WYCENA"):
    reset_all()
    st.rerun()

# --- 6. WYNIKI ---
if st.session_state.calc_done:
    res = st.session_state.results
    st.divider()
    st.write(f"📊 **Materiały:** {res['mb']:.2f} mb listwy | Profil: {res['kod']} | Format: {res['s']}x{res['w']} cm")
    
    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.markdown(f"""
            <div class='price-card'>
                <h3>📦 LISTWA</h3>
                <h2 style='color:#0e63d1'>{res['f_l']} zł</h2>
                <p style='font-size: 0.8em; color: #aaa;'>Hurt + VAT: {res['prod_l']} zł</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Wybierz Opcję Listwa", key="sel_l"):
            st.session_state.selected_opcja = "Listwa"
            st.session_state.final_price = res['f_l']

    with col_res2:
        st.markdown(f"""
            <div class='price-card'>
                <h3>🖼️ W RAMIE</h3>
                <h2 style='color:#0e63d1'>{res['f_r']} zł</h2>
                <p style='font-size: 0.8em; color: #aaa;'>Hurt + VAT: {res['prod_r']} zł</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Wybierz Opcję Rama", key="sel_r"):
            st.session_state.selected_opcja = "Rama"
            st.session_state.final_price = res['f_r']

    # PANEL EKSPORTU (Pojawia się po kliknięciu Wybierz)
    if 'selected_opcja' in st.session_state:
        st.success(f"### Wybrano: {st.session_state.selected_opcja}")
        
        # Przygotowanie SMS
        sms_body = f"Eurorama: Wycena {wycena_date}. {st.session_state.selected_opcja} {res['kod']}, {res['s']}x{res['w']}cm. Do zaplaty: {st.session_state.final_price}zl. Uwagi: {st.session_state.notes}"
        enc_sms = urllib.parse.quote(sms_body)
        
        ex_col1, ex_col2 = st.columns(2)
        with ex_col1:
            # Generowanie PDF
            pdf_payload = {
                'data': wycena_date, 'kod': res['kod'], 'format': f"{res['s']}x{res['w']}",
                'opcja': st.session_state.selected_opcja, 'cena': st.session_state.final_price, 
                'uwagi': st.session_state.notes
            }
            pdf_bytes = create_pdf(pdf_payload)
            st.download_button("📥 Pobierz PDF", data=pdf_bytes, file_name=f"wycena_{res['kod']}.pdf", mime="application/pdf", use_container_width=True)
        
        with ex_col2:
            # Przycisk SMS
            st.markdown(f'<a href="sms:?body={enc_sms}" class="sms-btn">📱 Wyślij SMS</a>', unsafe_allow_html=True)

st.markdown(f'<div class="footer"><p>📞 Zadzwoń: <b>15 876 30 16</b></p></div>', unsafe_allow_html=True)
