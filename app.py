import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
import urllib.parse

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="EuroRama Ekspert v9.3", page_icon="🖼️", layout="wide")

# Stałe
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
LOGO_FILE = "logo.png"
HASLO_ADMINA = "Admin123"

# --- 2. PAMIĘĆ SESJI ---
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

# --- 3. DESIGN ---
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
    .stCheckbox label { color: #ffffff !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNKCJE ---
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
                data[k] = {
                    "cl": float(str(row[2]).replace(',','.')), 
                    "cr": float(str(row[3]).replace(',','.')), 
                    "sz": float(str(row[4]).replace(',','.'))
                }
            except: continue
        return data
    except: return None

def create_pdf_bytes(d):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=10, y=8, w=40)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(0, 15, "POTWIERDZENIE WYCENY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 10, f"Data wyceny: {d['data']}", ln=True, align='R')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Szczegoly zamowienia:", ln=True)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"- Kod listwy: {d['kod']}", ln=True)
    pdf.cell(0, 10, f"- Format obrazu: {d['format']} cm", ln=True)
    pdf.cell(0, 10, f"- Wybrana opcja: {d['opcja']}", ln=True)
    if d['dodatki_text']:
        pdf.cell(0, 10, f"- Dodatki: {d['dodatki_text']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.set_text_color(14, 99, 209)
    pdf.cell(0, 15, f"KWOTA DO ZAPLATY: {d['cena']} PLN", ln=True, align='L')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'I', 10)
    uwagi_clean = d['uwagi'].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, f"Uwagi: {uwagi_clean}")
    pdf.ln(20)
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 10, "Dziekujemy za wybranie EuroRama!", align='C')
    return bytes(pdf.output())

db = load_db()

# --- 5. PANEL BOCZNY (USTAWIENIA CEN MATERIAŁÓW) ---
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_container_width=True)

st.sidebar.header("⚙️ Cennik materiałów (m²)")
cena_szklo = st.sidebar.number_input("Szkło zwykłe [zł/m2]", value=43.0)
cena_antyr = st.sidebar.number_input("Szkło Antyreflex [zł/m2]", value=85.0)
cena_tyl = st.sidebar.number_input("Tył / HDF [zł/m2]", value=30.0)
cena_min = st.sidebar.number_input("Cena minimalna usługi [zł]", value=25.0)

st.sidebar.divider()
st.sidebar.header("🔐 Admin")
pw = st.sidebar.text_input("Hasło", type="password")
if pw == HASLO_ADMINA:
    up = st.sidebar.file_uploader("Zaktualizuj cennik", type=['csv'])
    if up:
        with open(DEFAULT_FILE, "wb") as f: f.write(up.getbuffer())
        st.sidebar.success("Cennik zapisany!")

# --- 6. GŁÓWNY INTERFEJS ---
st.header("EuroRama Twój Dostawca Ram")

if not db:
    st.error("Wgraj plik cennik.csv w panelu bocznym.")
else:
    with st.container():
        row1_col1, row1_col2 = st.columns([2, 1])
        with row1_col1:
            codes = sorted(list(db.keys()))
            selected_code = st.selectbox("Wybierz kod listwy:", options=codes, index=0)
        with row1_col2:
            w_date = st.date_input("Data wyceny", datetime.now())

        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            input_w = st.number_input("Szerokość [cm]", min_value=1.0, value=50.0)
        with row2_col2:
            input_h = st.number_input("Wysokość [cm]", min_value=1.0, value=60.0)

        row3_col1, row3_col2 = st.columns(2)
        with row3_col1:
            m_l = st.number_input("Marża Listwa [%]", value=50)
        with row3_col2:
            m_r = st.number_input("Marża Rama [%]", value=35)

    with st.expander("📝 Dodatki i Uwagi"):
        st.write("Wybierz co doliczyć do ceny:")
        c1, c2, c3 = st.columns(3)
        check_szklo = c1.checkbox("Szkło")
        check_antyr = c2.checkbox("Antyreflex")
        check_tyl = c3.checkbox("Tył / HDF")
        
        extra_manual = st.number_input("Inny koszt dodatkowy [zł]", value=0.0)
        user_notes = st.text_area("Uwagi do zamówienia")

    col_btn1, col_btn2 = st.columns(2)
    
    if col_btn1.button("🚀 WYCEŃ", type="primary", use_container_width=True):
        item = db[selected_code]
        mb = ((2 * input_w) + (2 * input_h) + (8 * item['sz'])) / 100
        m2 = (input_w * input_h) / 10000
        
        # Obliczanie kosztu wybranych materiałów
        dodatki_netto = 0
        wybrane_tekst = []
        if check_szklo: 
            dodatki_netto += (m2 * cena_szklo)
            wybrane_tekst.append("Szkło")
        if check_antyr: 
            dodatki_netto += (m2 * cena_antyr)
            wybrane_tekst.append("Antyreflex")
        if check_tyl: 
            dodatki_netto += (m2 * cena_tyl)
            wybrane_tekst.append("Tył")
        
        # Koszty bazowe producenta + VAT
        c_prod_l = (mb * item['cl']) * VAT
        c_prod_r = (mb * item['cr']) * VAT
        
        # Kalkulacja dodatków z VAT i marżą (stosujemy marżę jak do listwy/ramy)
        f_dodatki_l = (dodatki_netto * VAT * (1 + m_l/100)) + extra_manual
        f_dodatki_r = (dodatki_netto * VAT * (1 + m_r/100)) + extra_manual
        
        final_l = max(round(c_prod_l * (1 + m_l/100) + f_dodatki_l, 2), cena_min)
        final_r = max(round(c_prod_r * (1 + m_r/100) + f_dodatki_r, 2), cena_min)
        
        st.session_state.calc_results = {
            'kod': selected_code.upper(), 's': input_w, 'w': input_h, 'mb': mb, 'm2': m2,
            'prod_l': round(c_prod_l, 2), 'prod_r': round(c_prod_r, 2),
            'f_l': final_l, 'f_r': final_r,
            'notes': user_notes, 'date': w_date,
            'dodatki_txt': ", ".join(wybrane_tekst) if wybrane_tekst else "Brak"
        }
        st.session_state.selected_option = None
        
        hist_entry = f"{datetime.now().strftime('%H:%M')} - {selected_code.upper()} ({input_w}x{input_h}) -> Rama: {final_r} zł"
        st.session_state.history.insert(0, hist_entry)
        st.session_state.history = st.session_state.history[:5]

    if col_btn2.button("🧹 NOWA WYCENA", use_container_width=True):
        reset_app()

# --- 7. WYNIKI ---
if st.session_state.calc_results:
    res = st.session_state.calc_results
    st.divider()
    st.markdown(f"📈 **Materiały:** {res['mb']:.2f} mb listwy | **Format:** {res['s']}x{res['w']} cm ({res['m2']:.4f} m²)")
    if res['dodatki_txt'] != "Brak":
        st.write(f"✅ **Dodatki:** {res['dodatki_txt']}")
    
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.markdown(f"""<div class='price-card'>
            <h3>📦 LISTWA + DODATKI</h3><h2 style='color:#0e63d1'>{res['f_l']} zł</h2>
            <p style='color:#888 !important; font-size:0.8em'>Producent listwy + VAT: {res['prod_l']} zł</p>
        </div>""", unsafe_allow_html=True)
        if st.button("Wybierz Opcję Listwa", use_container_width=True):
            st.session_state.selected_option = "Sama Listwa"
            st.session_state.active_price = res['f_l']

    with res_col2:
        st.markdown(f"""<div class='price-card'>
            <h3>🖼️ W RAMIE + DODATKI</h3><h2 style='color:#0e63d1'>{res['f_r']} zł</h2>
            <p style='color:#888 !important; font-size:0.8em'>Producent ramy + VAT: {res['prod_r']} zł</p>
        </div>""", unsafe_allow_html=True)
        if st.button("Wybierz Opcję Rama", use_container_width=True):
            st.session_state.selected_option = "Gotowa Rama"
            st.session_state.active_price = res['f_r']

    if st.session_state.selected_option:
        st.divider()
        sms_text = f"EuroRama: Wycena {res['date']}. {st.session_state.selected_option} {res['kod']}, {res['s']}x{res['w']}cm. Dodatki: {res['dodatki_txt']}. Cena: {st.session_state.active_price}zl. {res['notes']}"
        encoded_sms = urllib.parse.quote(sms_text)
        
        ex1, ex2 = st.columns(2)
        with ex1:
            pdf_data = {
                'data': res['date'], 'kod': res['kod'], 'format': f"{res['s']}x{res['w']}",
                'opcja': st.session_state.selected_option, 'cena': st.session_state.active_price, 
                'uwagi': res['notes'], 'dodatki_text': res['dodatki_txt']
            }
            try:
                p_bytes = create_pdf_bytes(pdf_data)
                st.download_button("📥 Pobierz PDF", data=p_bytes, file_name=f"wycena_{res['kod']}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e: st.error(f"Błąd PDF: {e}")
        with ex2:
            st.markdown(f'<a href="sms:?body={encoded_sms}" class="sms-btn">📱 Wyślij SMS</a>', unsafe_allow_html=True)

# --- 8. HISTORIA ---
if st.session_state.history:
    st.write("---")
    st.subheader("🕒 Ostatnie 5 wycen")
    for h in st.session_state.history:
        st.markdown(f"<div class='history-card'>{h}</div>", unsafe_allow_html=True)

st.markdown(f'<div class="footer"><p>📞 Zadzwoń: <b>15 876 30 16</b></p></div>', unsafe_allow_html=True)
