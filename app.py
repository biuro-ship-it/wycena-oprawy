import streamlit as st
import pandas as pd
import re
import os
import urllib.parse
from fpdf import FPDF
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# --- 1. KONFIGURACJA I SEKRETY ---
st.set_page_config(page_title="EuroRama Ekspert v10.0", page_icon="🖼️", layout="wide")

# Stałe
VAT: float = 1.23
DEFAULT_FILE: str = "cennik.csv"
LOGO_FILE: str = "logo.png"

# Bezpieczne hasło z Streamlit Secrets lub fallback dla testów
HASLO_ADMINA: str = st.secrets.get("ADMIN_PASSWORD", "Admin123")

# --- 2. LOGIKA OBLICZEŃ (Separation of Concerns) ---
def calculate_prices(
    item: Dict[str, float], 
    width: float, 
    height: float, 
    margin_l: float, 
    margin_r: float,
    extra_l: float,
    extra_r: float,
    materials_netto: float,
    min_price: float
) -> Tuple[float, float, float, float, float]:
    """
    Czysta funkcja do obliczeń cenowych. 
    Zwraca: (mb_listwy, m2_obrazu, cena_prod_l, cena_prod_r, cena_final_l, cena_final_r)
    """
    mb = ((2 * width) + (2 * height) + (8 * item['sz'])) / 100
    m2 = (width * height) / 10000
    
    # Koszty producenta brutto
    prod_l = mb * item['cl'] * VAT
    prod_r = mb * item['cr'] * VAT
    
    # Dodatki z marżą
    dodatki_l = (materials_netto * VAT * (1 + margin_l / 100)) + extra_l
    dodatki_r = (materials_netto * VAT * (1 + margin_r / 100)) + extra_r
    
    # Finalne ceny
    final_l = max(round(prod_l * (1 + margin_l / 100) + dodatki_l, 2), min_price)
    final_r = max(round(prod_r * (1 + margin_r / 100) + dodatki_r, 2), min_price)
    
    return mb, m2, round(prod_l, 2), round(prod_r, 2), final_l, final_r

# --- 3. OBSŁUGA DANYCH (Caching & Error Handling) ---
@st.cache_data(show_spinner="Wczytywanie bazy danych...")
def load_db(file_path: str) -> Optional[Dict[str, Dict[str, float]]]:
    if not os.path.exists(file_path):
        return None
    try:
        # Szybsze parsowanie z określonym separatorem
        df = pd.read_csv(
            file_path, 
            header=None, 
            encoding='cp1250', 
            sep=None, 
            engine='python', 
            on_bad_lines='skip'
        )
        data = {}
        for _, row in df.iterrows():
            try:
                k = str(row[0]).strip().lower()
                if k == "" or any(word in k for word in ["profil", "kolumna", "netto"]):
                    continue
                if k.endswith('.0'): k = k[:-2]
                
                data[k] = {
                    "cl": float(str(row[2]).replace(',', '.')), 
                    "cr": float(str(row[3]).replace(',', '.')), 
                    "sz": float(str(row[4]).replace(',', '.'))
                }
            except (ValueError, IndexError):
                continue
        return data
    except Exception as e:
        st.error(f"Błąd bazy danych: {e}")
        return None

# --- 4. EKSPORT (PDF & SMS) ---
def create_pdf_bytes(d: Dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=10, y=8, w=40)
    
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(0, 15, "POTWIERDZENIE WYCENY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 10, f"Data: {d['data']}", ln=True, align='R')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Szczegoly:", ln=True)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Listwa: {d['kod']}", ln=True)
    pdf.cell(0, 10, f"Format: {d['format']} cm", ln=True)
    pdf.cell(0, 10, f"Opcja: {d['opcja']}", ln=True)
    if d['dodatki']: pdf.cell(0, 10, f"Dodatki: {d['dodatki']}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.set_text_color(14, 99, 209)
    pdf.cell(0, 15, f"KWOTA: {d['cena']} PLN", ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", 'I', 10)
    uwagi = str(d['uwagi']).encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, f"Uwagi: {uwagi}")
    
    # Poprawiony eksport bytes dla fpdf2
    return pdf.output()

# --- 5. INTERFEJS I SESJA ---
def get_url_param(key: str, default: float) -> float:
    p = st.query_params.get(key)
    try:
        return float(p) if p else default
    except:
        return default

if 'history' not in st.session_state: st.session_state.history = []
if 'calc_results' not in st.session_state: st.session_state.calc_results = None
if 'selected_option' not in st.session_state: st.session_state.selected_option = None

# --- UI START ---
if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, use_container_width=True)

st.sidebar.header("⚙️ Profil Cenowy")
c_szklo = st.sidebar.number_input("Szkło [zł/m2]", value=get_url_param('gs', 43.0))
c_antyr = st.sidebar.number_input("Antyreflex [zł/m2]", value=get_url_param('as', 85.0))
c_tyl = st.sidebar.number_input("Tył / HDF [zł/m2]", value=get_url_param('bs', 30.0))
c_min = st.sidebar.number_input("Cena min. [zł]", value=get_url_param('mi', 25.0))
def_m_l = st.sidebar.number_input("Marża Listwa [%]", value=int(get_url_param('ml', 50)))
def_m_r = st.sidebar.number_input("Marża Rama [%]", value=int(get_url_param('mr', 35)))

if st.sidebar.button("💾 Zapisz ustawienia"):
    st.query_params.from_dict({'gs':c_szklo, 'as':c_antyr, 'bs':c_tyl, 'mi':c_min, 'ml':def_m_l, 'mr':def_m_r})
    st.sidebar.success("Zapisano!")

st.sidebar.divider()
st.sidebar.header("🔐 Admin")
if st.sidebar.text_input("Hasło", type="password") == HASLO_ADMINA:
    up = st.sidebar.file_uploader("Cennik CSV", type=['csv'])
    if up:
        with open(DEFAULT_FILE, "wb") as f: f.write(up.getbuffer())
        st.cache_data.clear() # Czyścimy cache po wgraniu nowej bazy
        st.sidebar.success("Baza odświeżona!")

st.header("EuroRama Twój Dostawca Ram")
db = load_db(DEFAULT_FILE)

if not db:
    st.info("Oczekiwanie na bazę danych (cennik.csv)...")
else:
    # Układ główny
    with st.container():
        c1, c2 = st.columns([2, 1])
        codes = sorted(db)
        sel_code = c1.selectbox("Wybierz profil:", options=codes)
        w_date = c2.date_input("Data", datetime.now())

        c3, c4 = st.columns(2)
        in_w = c3.number_input("Szerokość [cm]", min_value=1.0, value=50.0)
        in_h = c4.number_input("Wysokość [cm]", min_value=1.0, value=60.0)

    with st.expander("📝 Dodatki"):
        cx1, cx2, cx3 = st.columns(3)
        ch_sz = cx1.checkbox("Szkło")
        ch_an = cx2.checkbox("Antyreflex")
        ch_ty = cx3.checkbox("Tył")
        ex_man = st.number_input("Inny koszt [zł]", value=0.0)
        u_notes = st.text_area("Uwagi")

    # Akcja wyceny
    if st.button("🚀 WYCEŃ", type="primary", use_container_width=True):
        m2_pow = (in_w * in_h) / 10000
        mat_netto = (c_szklo if ch_sz else 0) + (c_antyr if ch_an else 0) + (c_tyl if ch_ty else 0)
        mat_total = mat_netto * m2_pow
        
        # Wywołanie funkcji obliczeniowej
        mb, m2, p_l, p_r, f_l, f_r = calculate_prices(
            db[sel_code], in_w, in_h, def_m_l, def_m_r, ex_man, ex_man, mat_total, c_min
        )
        
        st.session_state.calc_results = {
            'kod': sel_code.upper(), 's': in_w, 'w': in_h, 'mb': mb, 'm2': m2,
            'prod_l': p_l, 'prod_r': p_r, 'f_l': f_l, 'f_r': f_r,
            'notes': u_notes, 'date': w_date,
            'addons': ", ".join([t for t, c in zip(["Szkło", "Antyr.", "Tył"], [ch_sz, ch_an, ch_ty]) if c])
        }
        
        # Historia z limitem 20 wpisów
        st.session_state.history.insert(0, f"{datetime.now().strftime('%H:%M')} - {sel_code.upper()} ({in_w}x{in_h}) -> {f_r} zł")
        st.session_state.history = st.session_state.history[:20]

    # Prezentacja wyników
    if st.session_state.calc_results:
        res = st.session_state.calc_results
        st.divider()
        st.markdown(f"📈 {res['mb']:.2f} mb | {res['s']}x{res['w']} cm | Dodatki: {res['addons'] or 'Brak'}")
        
        r1, r2 = st.columns(2)
        with r1:
            st.markdown(f"<div class='price-card'><h3>📦 LISTWA</h3><h2 style='color:#0e63d1'>{res['f_l']} zł</h2><p style='color:#888'>Producent: {res['prod_l']} zł</p></div>", unsafe_allow_html=True)
            if st.button("Wybierz Listwę", use_container_width=True): st.session_state.selected_option = ("Sama Listwa", res['f_l'])
        with r2:
            st.markdown(f"<div class='price-card'><h3>🖼️ W RAMIE</h3><h2 style='color:#0e63d1'>{res['f_r']} zł</h2><p style='color:#888'>Producent: {res['prod_r']} zł</p></div>", unsafe_allow_html=True)
            if st.button("Wybierz Ramę", use_container_width=True): st.session_state.selected_option = ("Gotowa Rama", res['f_r'])

        if st.session_state.selected_option:
            opt_name, opt_price = st.session_state.selected_option
            sms = f"EuroRama: Wycena {res['date']}. {opt_name} {res['kod']}, {res['s']}x{res['w']}cm. Cena: {opt_price}zl."
            
            ex1, ex2 = st.columns(2)
            with ex1:
                p_bytes = create_pdf_bytes({'data':res['date'], 'kod':res['kod'], 'format':f"{res['s']}x{res['w']}", 'opcja':opt_name, 'cena':opt_price, 'uwagi':res['notes'], 'dodatki':res['addons']})
                st.download_button("📥 PDF", data=p_bytes, file_name=f"wycena_{res['kod']}.pdf", mime="application/pdf", use_container_width=True)
            with ex2:
                st.markdown(f'<a href="sms:?body={urllib.parse.quote(sms)}" class="sms-btn">📱 SMS</a>', unsafe_allow_html=True)

# Historia w UI
if st.session_state.history:
    st.write("---")
    st.subheader("🕒 Historia")
    for h in st.session_state.history:
        st.markdown(f"<div class='history-card'>{h}</div>", unsafe_allow_html=True)

st.markdown('<div class="footer"><p>📞 Zadzwoń: <b>15 876 30 16</b></p></div>', unsafe_allow_html=True)
