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

# STYLIZACJA GRAFITOWA (DARK MODE - OCHRONA WZROKU)
st.markdown("""
    <style>
    .stApp {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        font-weight: bold;
        background-color: #0e63d1;
        color: white;
        border: None;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #121212;
        text-align: center;
        padding: 10px;
        border-top: 2px solid #0e63d1;
        z-index: 100;
        color: #ffffff;
    }
    .price-card {
        border: 1px solid #444;
        padding: 20px;
        border-radius: 15px;
        background-color: #2d2d2d;
        color: #ffffff;
        margin-bottom: 10px;
    }
    h1, h2, h3, p, label, .stMarkdown, span {
        color: #ffffff !important;
    }
    .stExpander {
        background-color: #2d2d2d !important;
        border: 1px solid #444 !important;
    }
    </style>
    """, unsafe_allow_html=True)

if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=220)

# --- 3. PANEL ADMINISTRACYJNY ---
st.sidebar.header("🔐 Admin")
pass_input = st.sidebar.text_input("Hasło", type="password")
if pass_input == HASLO_ADMINA:
    up_file = st.sidebar.file_uploader("Wgraj cennik CSV", type=['csv'])
    if up_file:
        with open(DEFAULT_FILE, "wb") as f:
            f.write(up_file.getbuffer())
        st.sidebar.success("Zaktualizowano!")

# --- 4. FUNKCJE ---
def load_db():
    if not os.path.exists(DEFAULT_FILE): return None
    try:
        # Próba wczytania z pominięciem błędnych linii i wykrywaniem separatora
        df = pd.read_csv(DEFAULT_FILE, header=None, sep=None, engine='python', encoding='cp1250', on_bad_lines='skip')
        data = {}
        for _, row in df.iterrows():
            try:
                # SPRZĄTANIE KODU
                k = str(row[0]).strip().lower()
                if k == "" or "profil" in k or "kolumna" in k: continue
                if k.endswith('.0'): k = k[:-2]
                
                # BEZPIECZNA KONWERSJA CEN (To naprawia Twój błąd ze zdjęcia)
                c_l_raw = str(row[2]).replace(',', '.').strip()
                c_r_raw = str(row[3]).replace(',', '.').strip()
                sz_raw = str(row[4]).replace(',', '.').strip()
                
                data[k] = {
                    "cl": float(c_l_raw), 
                    "cr": float(c_r_raw), 
                    "sz": float(sz_raw)
                }
            except (ValueError, TypeError, IndexError):
                continue # Jeśli to nagłówek lub błąd, po prostu przejdź do następnego wiersza
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
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"DO ZAPLATY: {data['cena']} PLN", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", '', 10)
    pdf.multi_cell(0, 10, f"Uwagi: {data['uwagi']}")
    return pdf.output()

db = load_db()

# --- 5. INTERFEJS ---
st.header("Eurorama Twój Dostawca Ram")

col_a, col_b = st.columns([2, 1])
with col_a:
    user_input = st.text_input("Podaj kod i wymiary (np. 34 50 60)", key="input_text")
with col_b:
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
do_calc = b_col1.button("🚀 WYCEŃ")
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

                st.markdown(f"**Materiał:** {mb:.2f} mb | **Powierzchnia:** {m2:.4f} m²")
                
                res_l, res_r = st.columns(2)
                with res_l:
                    st.markdown(f"<div class='price-card'><h3>📦 LISTWA</h3><h2 style='color:#0e63d1 !important'>{f_l} zł</h2><p>Hurt + VAT: {c_p_l:.2f} zł</p></div>", unsafe_allow_html=True)
                    if st.button("Wybierz Opcję Listwa"):
                        st.text_area("Tekst SMS:", value=f"Eurorama: Wycena {wycena_data}. Listwa {kod.upper()}, {szer}x{wys}cm. Cena: {f_l}zl. {uwagi}")
                        pdf_b = generate_pdf({'data': wycena_data, 'kod': kod.upper(), 'format': f"{szer}x{wys}", 'cena': f_l, 'uwagi': uwagi})
                        st.download_button("📥 PDF (Listwa)", data=pdf_b, file_name=f"wycena_l_{kod}.pdf")

                with res_r:
                    st.markdown(f"<div class='price-card'><h3>🖼️ W RAMIE</h3><h2 style='color:#0e63d1 !important'>{f_r} zł</h2><p>Hurt + VAT: {c_p_r:.2f} zł</p></div>", unsafe_allow_html=True)
                    if st.button("Wybierz Opcję Rama"):
                        st.text_area("Tekst SMS:", value=f"Eurorama: Wycena {wycena_data}. Rama {kod.upper()}, {szer}x{wys}cm. Cena: {f_r}zl. {uwagi}")
                        pdf_b = generate_pdf({'data': wycena_data, 'kod': kod.upper(), 'format': f"{szer}x{wys}", 'cena': f_r, 'uwagi': uwagi})
                        st.download_button("📥 PDF (Rama)", data=pdf_b, file_name=f"wycena_r_{kod}.pdf")
            else: st.error(f"Nie znaleziono kodu {kod}")
        else: st.warning("Wpisz kod i wymiary")
    else: st.error("Baza danych jest pusta lub niezaładowana.")

st.markdown(f"""<div class="footer"><p>📞 Zadzwoń: <b>15 876 30 16</b></p></div>""", unsafe_allow_html=True)
