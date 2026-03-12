import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import date
import urllib.parse

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Eurorama v8.7", page_icon="🖼️", layout="wide")

# Parametry
VAT = 1.23
DEFAULT_FILE = "cennik.csv"
LOGO_FILE = "logo.png"
HASLO_ADMINA = "Admin123" # Twoje hasło

# --- 2. INICJALIZACJA PAMIĘCI (SESSION STATE) ---
if 'calc_results' not in st.session_state:
    st.session_state.calc_results = None
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None
if 'user_notes' not in st.session_state:
    st.session_state.user_notes = ""

def reset_app():
    st.session_state.calc_results = None
    st.session_state.selected_option = None
    st.session_state.user_notes = ""
    st.rerun()

# --- 3. STYLIZACJA DARK MODE ---
st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e; color: #ffffff; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #2d2d2d !important; color: #ffffff !important; border: 1px solid #444 !important;
    }
    .price-card {
        border: 2px solid #0e63d1; padding: 20px; border-radius: 15px; background-color: #2d2d2d;
        color: #ffffff; text-align: center; margin-bottom: 15px;
    }
    .sms-btn {
        display: inline-block; padding: 12px 24px; background-color: #25d366; color: white !important;
        text-decoration: none; border-radius: 10px; font-weight: bold; width: 100%; text-align: center;
        margin-top: 10px; border: none;
    }
    h1, h2, h3, p, label, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# Wyświetlanie Logo
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=220)

# --- 4. FUNKCJE POMOCNICZE ---
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
                data[k] = {
                    "cl": float(str(row[2]).replace(',','.')), 
                    "cr": float(str(row[3]).replace(',','.')), 
                    "sz": float(str(row[4]).replace(',','.'))
                }
            except: continue
        return data
    except: return None

def create_pdf_bytes(d):
    # Generowanie PDF jako bajty (naprawia błąd Streamlit)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "WYCENA OPRAWY - EURORAMA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Data: {d['data']}", ln=True)
    pdf.cell(0, 10, f"Kod listwy: {d['kod']}", ln=True)
    pdf.cell(0, 10, f"Format: {d['format']} cm", ln=True)
    pdf.cell(0, 10, f"Opcja: {d['opcja']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"DO ZAPLATY: {d['cena']} PLN", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", '', 10)
    # Usuwamy polskie znaki dla pewności, że PDF się nie wywali w chmurze bez czcionek
    uwagi_safe = d['uwagi'].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, f"Uwagi: {uwagi_safe}")
    return bytes(pdf.output())

db = load_db()

# --- 5. PANEL ADMINA ---
st.sidebar.header("🔐 Panel Admina")
pass_in = st.sidebar.text_input("Hasło", type="password")
if pass_in == HASLO_ADMINA:
    f_up = st.sidebar.file_uploader("Wgraj cennik", type=['csv'])
    if f_up:
        with open(DEFAULT_FILE, "wb") as f: f.write(f_up.getbuffer())
        st.sidebar.success("Zaktualizowano!")

# --- 6. INTERFEJS GŁÓWNY ---
st.header("Eurorama Twój Dostawca Ram")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Kod i wymiary (np. 34 50 60)", key="main_input")
with col2:
    wycena_date = st.date_input("Data wyceny", date.today())

m_col1, m_col2 = st.columns(2)
mar_l = m_col1.number_input("Marża Listwa [%]", value=60)
mar_r = m_col2.number_input("Marża Rama [%]", value=45)

with st.expander("💰 Dodatki i Uwagi"):
    e1, e2 = st.columns(2)
    extra_l = e1.number_input("Dodatek Listwa [zł]", value=0.0)
    extra_r = e2.number_input("Dodatek Rama [zł]", value=0.0)
    st.session_state.user_notes = st.text_area("Uwagi do zamówienia", value=st.session_state.user_notes)

# Przyciski główne
b1, b2 = st.columns(2)
if b1.button("🚀 WYCEŃ", type="primary"):
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
                
                # Zapisujemy wyniki do sesji
                st.session_state.calc_results = {
                    'kod': k.upper(), 's': s, 'w': w, 'mb': mb,
                    'prod_l': round(c_p_l, 2), 'prod_r': round(c_p_r, 2),
                    'f_l': round((c_p_l * (1 + mar_l/100)) + extra_l, 2),
                    'f_r': round((c_p_r * (1 + mar_r/100)) + extra_r, 2)
                }
                st.session_state.selected_option = None # Reset wyboru przy nowej wycenie
            else: st.error("Brak kodu!")
        else: st.warning("Podaj wymiary!")

if b2.button("🧹 NOWA WYCENA"):
    reset_app()

# --- 7. WYŚWIETLANIE WYNIKÓW ---
if st.session_state.calc_results:
    res = st.session_state.calc_results
    st.divider()
    st.markdown(f"📊 **Materiał:** {res['mb']:.2f} mb | Profil: {res['kod']} | Format: {res['s']}x{res['w']} cm")
    
    r_col1, r_col2 = st.columns(2)
    
    with r_col1:
        st.markdown(f"""<div class='price-card'>
            <h3>📦 LISTWA</h3><h2 style='color:#0e63d1'>{res['f_l']} zł</h2>
            <p style='color:#aaa !important; font-size:0.8em'>Hurt + VAT: {res['prod_l']} zł</p>
        </div>""", unsafe_allow_html=True)
        if st.button("Wybierz Opcję Listwa"):
            st.session_state.selected_option = "Listwa"
            st.session_state.active_price = res['f_l']

    with r_col2:
        st.markdown(f"""<div class='price-card'>
            <h3>🖼️ W RAMIE</h3><h2 style='color:#0e63d1'>{res['f_r']} zł</h2>
            <p style='color:#aaa !important; font-size:0.8em'>Hurt + VAT: {res['prod_r']} zł</p>
        </div>""", unsafe_allow_html=True)
        if st.button("Wybierz Opcję Rama"):
            st.session_state.selected_option = "Rama"
            st.session_state.active_price = res['f_r']

    # --- 8. PANEL EKSPORTU (TYLKO PO WYBORZE) ---
    if st.session_state.selected_option:
        st.divider()
        st.subheader(f"✅ Wybrano: {st.session_state.selected_option}")
        
        opt = st.session_state.selected_option
        prc = st.session_state.active_price
        notes = st.session_state.user_notes
        
        # Przygotowanie SMS
        sms_body = f"Eurorama: Wycena {wycena_date}. {opt} {res['kod']}, {res['s']}x{res['w']}cm. Cena: {prc}zl. {notes}"
        encoded_sms = urllib.parse.quote(sms_body)
        
        ex1, ex2 = st.columns(2)
        
        with ex1:
            # Naprawiony przycisk PDF
            pdf_data = {
                'data': wycena_date, 'kod': res['kod'], 'format': f"{res['s']}x{res['w']}",
                'opcja': opt, 'cena': prc, 'uwagi': notes
            }
            try:
                p_bytes = create_pdf_bytes(pdf_data)
                st.download_button(
                    label="📥 Pobierz PDF",
                    data=p_bytes,
                    file_name=f"wycena_{res['kod']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Błąd PDF: {e}")

        with ex2:
            # Przycisk SMS
            st.markdown(f'<a href="sms:?body={encoded_sms}" class="sms-btn">📱 Wyślij SMS</a>', unsafe_allow_html=True)

st.markdown(f'<div class="footer"><p>📞 Zadzwoń: <b>15 876 30 16</b></p></div>', unsafe_allow_html=True)
