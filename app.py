import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
import urllib.parse

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="EuroRama Ekspert v9.6", page_icon="🖼️", layout="wide")

# Stałe
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
LOGO_FILE = "logo.png"
HASLO_ADMINA = "Admin123" # Twoje hasło

# --- 2. OBSŁUGA LINKÓW (URL PARAMETERS) ---
params = st.query_params

def get_param(key, default):
    try:
        return float(params.get(key, default))
    except:
        return float(default)

# --- 3. PAMIĘĆ SESJI ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'calc_results' not in st.session_state:
    st.session_state.calc_results = None
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None

def reset_app():
    st.session_state.calc_results = None
    st.session_state.selected_option = None
    st.rerun()

# --- 4. DESIGN (DARK MODE COMFORT) ---
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .stSelectbox div[data-baseweb="select"] { background-color: #1e1e1e !important; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #1e1e1e !important; color: #ffffff !important; border: 1px solid #333 !important;
    }
    .price-card {
        border: 2px solid #0e63d1; padding: 25px; border-radius: 15px; background-color: #1e1e1e;
        color: #ffffff; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .history-card {
        background-color: #252525; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 4px solid #0e63d1;
    }
    .sms-btn {
        display: inline-block; padding: 12px 24px; background-color: #28a745; color: white !important;
        text-decoration: none; border-radius: 10px; font-weight: bold; width: 100%; text-align: center; margin-top: 10px;
    }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #121212; text-align: center; padding: 10px; border-top: 2px solid #0e63d1; z-index: 100; color: #ffffff; }
    h1, h2, h3, p, label, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNKCJE ---
def load_db():
    if not os.path.exists(DEFAULT_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_FILE, header=None, sep=None, engine='python', encoding='cp1250', on_bad_lines='skip')
        data = {}
        for _, row in df.iterrows():
            try:
                k = str(row[0]).strip().lower()
                if k == "" or "profil" in k or "kolumna" in k: continue
                if k.endswith('.0'): k = k[:-2]
                data[k] = {"cl": float(str(row[2]).replace(',','.')), "cr": float(str(row[3]).replace(',','.')), "sz": float(str(row[4]).replace(',','.'))}
            except: continue
        return data
    except: return None

def create_pdf_bytes(d):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(LOGO_FILE): pdf.image(LOGO_FILE, x=10, y=8, w=40)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(0, 15, "POTWIERDZENIE WYCENY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 10, f"Data wyceny: {d['data']}", ln=True, align='R')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12); pdf.cell(0, 10, "Szczegóły zamówienia:", ln=True)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"- Kod listwy: {d['kod']}", ln=True)
    pdf.cell(0, 10, f"- Format obrazu: {d['format']} cm", ln=True)
    pdf.cell(0, 10, f"- Wybrana opcja: {d['opcja']}", ln=True)
    if d['dodatki_text']: pdf.cell(0, 10, f"- Dodatki: {d['dodatki_text']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 16); pdf.set_text_color(14, 99, 209)
    pdf.cell(0, 15, f"KWOTA DO ZAPŁATY: {d['cena']} PLN", ln=True, align='L')
    pdf.set_text_color(0, 0, 0); pdf.ln(5); pdf.set_font("Helvetica", 'I', 10)
    uwagi_clean = d['uwagi'].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, f"Uwagi: {uwagi_clean}")
    pdf.ln(20); pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 10, "Dziękujemy za wybranie EuroRama!", align='C')
    return bytes(pdf.output())

db = load_db()

# --- 6. PANEL BOCZNY (TWOJE USTAWIENIA) ---
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_container_width=True)

st.sidebar.header("⚙️ Twój Profil Cenowy")
c_szklo = st.sidebar.number_input("Szkło [zł/m2]", value=get_param('gs', 43.0))
c_antyr = st.sidebar.number_input("Antyreflex [zł/m2]", value=get_param('as', 85.0))
c_tyl = st.sidebar.number_input("Tył / HDF [zł/m2]", value=get_param('bs', 30.0))
c_min = st.sidebar.number_input("Cena min. [zł]", value=get_param('mi', 25.0))

st.sidebar.subheader("Twoje Stałe Marże")
def_m_l = st.sidebar.number_input("Marża Listwa [%]", value=int(get_param('ml', 50)))
def_m_r = st.sidebar.number_input("Marża Rama [%]", value=int(get_param('mr', 35)))

if st.sidebar.button("💾 Zapisz ustawienia w linku"):
    new_params = {
        'gs': c_szklo, 'as': c_antyr, 'bs': c_tyl, 'mi': c_min,
        'ml': def_m_l, 'mr': def_m_r
    }
    st.query_params.from_dict(new_params)
    st.sidebar.success("Zapisano! Skopiuj adres URL i dodaj do zakładek.")

st.sidebar.divider()
st.sidebar.header("🔐 Admin")
pw = st.sidebar.text_input("Hasło", type="password")
if pw == HASLO_ADMINA:
    up = st.sidebar.file_uploader("Wgraj cennik", type=['csv'])
    if up:
        with open(DEFAULT_FILE, "wb") as f: f.write(up.getbuffer())
        st.sidebar.success("Baza zaktualizowana!")

# --- 7. GŁÓWNY INTERFEJS ---
st.header("EuroRama Twój Dostawca Ram")

if not db:
    st.error("Proszę wgrać plik cennik.csv w panelu admina.")
else:
    with st.container():
        r1_c1, r1_c2 = st.columns([2, 1])
        with r1_c1:
            codes = sorted(list(db.keys()))
            sel_code = st.selectbox("Kod listwy:", options=codes, index=0)
        with r1_c2:
            w_date = st.date_input("Data", datetime.now())

        r2_c1, r2_c2 = st.columns(2)
        with r2_c1: in_w = st.number_input("Szerokość [cm]", min_value=1.0, value=50.0)
        with r2_c2: in_h = st.number_input("Wysokość [cm]", min_value=1.0, value=60.0)

    with st.expander("📝 Dodatki i Uwagi"):
        c1, c2, c3 = st.columns(3)
        ch_sz = c1.checkbox("Szkło")
        ch_an = c2.checkbox("Antyreflex")
        ch_ty = c3.checkbox("Tył / HDF")
        ex_man = st.number_input("Inny koszt dodatkowy [zł]", value=0.0)
        u_notes = st.text_area("Uwagi do zamówienia")

    b1, b2 = st.columns(2)
    if b1.button("🚀 WYCEŃ", type="primary", use_container_width=True):
        item = db[sel_code]
        mb = ((2 * in_w) + (2 * in_h) + (8 * item['sz'])) / 100
        m2 = (in_w * in_h) / 10000
        
        d_netto = 0
        txt = []
        if ch_sz: d_netto += (m2 * c_szklo); txt.append("Szkło")
        if ch_an: d_netto += (m2 * c_antyr); txt.append("Antyreflex")
        if ch_ty: d_netto += (m2 * c_tyl); txt.append("Tył")
        
        # Obliczenia bazowe
        c_p_l = (mb * item['cl']) * VAT
        c_p_r = (mb * item['cr']) * VAT
        
        # Dodatki z marżą (używamy marż z panelu bocznego)
        f_d_l = (d_netto * VAT * (1 + def_m_l/100)) + ex_man
        f_d_r = (d_netto * VAT * (1 + def_m_r/100)) + ex_man
        
        # Cena końcowa (używamy marż z panelu bocznego)
        f_l = max(round(c_p_l * (1 + def_m_l/100) + f_d_l, 2), c_min)
        f_r = max(round(c_p_r * (1 + def_m_r/100) + f_d_r, 2), c_min)
        
        st.session_state.calc_results = {
            'kod': sel_code.upper(), 's': in_w, 'w': in_h, 'mb': mb, 'm2': m2,
            'prod_l': round(c_p_l, 2), 'prod_r': round(c_p_r, 2),
            'f_l': f_l, 'f_r': f_r, 'notes': u_notes, 'date': w_date,
            'dodatki_txt': ", ".join(txt) if txt else "Brak"
        }
        st.session_state.selected_option = None
        st.session_state.history.insert(0, f"{datetime.now().strftime('%H:%M')} - {sel_code.upper()} ({in_w}x{in_h}) -> {f_r} zł")

    if b2.button("🧹 NOWA WYCENA", use_container_width=True):
        reset_app()

# --- 8. WYNIKI ---
if st.session_state.calc_results:
    res = st.session_state.calc_results
    st.divider()
    st.markdown(f"📈 {res['mb']:.2f} mb | {res['s']}x{res['w']} cm | Dodatki: {res['dodatki_txt']}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='price-card'><h3>📦 LISTWA</h3><h2 style='color:#0e63d1'>{res['f_l']} zł</h2><p style='color:#888 !important; font-size:0.8em'>Producent: {res['prod_l']} zł</p></div>", unsafe_allow_html=True)
        if st.button("Wybierz Listwę", use_container_width=True): 
            st.session_state.selected_option = "Sama Listwa"; st.session_state.active_price = res['f_l']
    with c2:
        st.markdown(f"<div class='price-card'><h3>🖼️ W RAMIE</h3><h2 style='color:#0e63d1'>{res['f_r']} zł</h2><p style='color:#888 !important; font-size:0.8em'>Producent: {res['prod_r']} zł</p></div>", unsafe_allow_html=True)
        if st.button("Wybierz Ramę", use_container_width=True): 
            st.session_state.selected_option = "Gotowa Rama"; st.session_state.active_price = res['f_r']

    if st.session_state.selected_option:
        st.divider()
        sms = f"EuroRama: Wycena {res['date']}. {st.session_state.selected_option} {res['kod']}, {res['s']}x{res['w']}cm. Cena: {st.session_state.active_price}zł."
        ex1, ex2 = st.columns(2)
        with ex1:
            pdf_b = create_pdf_bytes({'data': res['date'], 'kod': res['kod'], 'format': f"{res['s']}x{res['w']}", 'opcja': st.session_state.selected_option, 'cena': st.session_state.active_price, 'uwagi': res['notes'], 'dodatki_text': res['dodatki_txt']})
            st.download_button("📥 PDF", data=pdf_b, file_name=f"wycena_{res['kod']}.pdf", mime="application/pdf", use_container_width=True)
        with ex2:
            st.markdown(f'<a href="sms:?body={urllib.parse.quote(sms)}" class="sms-btn">📱 SMS</a>', unsafe_allow_html=True)

if st.session_state.history:
    st.write("---"); st.subheader("🕒 Historia"); [st.markdown(f"<div class='history-card'>{h}</div>", unsafe_allow_html=True) for h in st.session_state.history[:5]]

st.markdown(f'<div class="footer"><p>📞 Zadzwoń: <b>15 876 30 16</b></p></div>', unsafe_allow_html=True)
