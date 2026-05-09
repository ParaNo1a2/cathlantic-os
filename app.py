import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.anthropic_handler import (
    expand_sectors, generate_job_titles, analyze_lead,
    generate_email_sequences, recommend_company_sizes, COMPANY_SIZE_OPTIONS,
)
from utils.apify_handler import run_leads_finder
from utils.web_scraper import fetch_homepage_text
from utils.instantly_handler import list_email_accounts, list_campaigns, create_campaign, upload_leads, launch_campaign

st.set_page_config(
    page_title="LCadreon — B2B Soğuk E-posta OS",
    page_icon="⚡",
    layout="wide"
)

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@500;600;700;800&display=swap');

/* ── Keyframes ─────────────────────────────────────────── */
@keyframes fadeSlideUp {
  from { opacity:0; transform:translateY(22px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes fadeSlideDown {
  from { opacity:0; transform:translateY(-22px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes fadeSlideRight {
  from { opacity:0; transform:translateX(-20px); }
  to   { opacity:1; transform:translateX(0); }
}
@keyframes fadeIn {
  from { opacity:0; } to { opacity:1; }
}
@keyframes glowPulse {
  0%,100% { text-shadow:0 0 8px rgba(255,23,68,.55); }
  50%     { text-shadow:0 0 28px rgba(255,23,68,1), 0 0 56px rgba(255,107,53,.4); }
}
@keyframes borderCycle {
  0%,100% { border-left-color:#FF1744; }
  50%     { border-left-color:#FF6B35; }
}
@keyframes countPop {
  0%  { transform:scale(.82); opacity:0; }
  65% { transform:scale(1.06); }
  100%{ transform:scale(1);   opacity:1; }
}
@keyframes scanline {
  0%   { transform:translateY(-100%); opacity:.06; }
  100% { transform:translateY(100vh); opacity:.06; }
}
@keyframes progressGlow {
  0%,100% { box-shadow:0 0 6px rgba(255,23,68,.5); }
  50%     { box-shadow:0 0 18px rgba(255,23,68,.9); }
}

/* ── Root ─────────────────────────────────────────────── */
:root {
  --bg:      #040205;
  --surface: #090408;
  --surf2:   #0F060E;
  --surf3:   #150A13;
  --border:  #1E0C17;
  --border2: #2E1221;
  --red:     #FF1744;
  --red2:    #FF6B35;
  --grad:    linear-gradient(135deg,#FF1744 0%,#FF6B35 100%);
  --glow:    0 0 28px rgba(255,23,68,.4);
  --glow2:   0 0 60px rgba(255,23,68,.12);
  --text:    #FFE8E8;
  --muted:   #6B3847;
  --muted2:  #4A2530;
  --radius:  3px;
}

/* ── Base ─────────────────────────────────────────────── */
html, body { background:var(--bg)!important; }

/* Subtle scanline overlay */
body::after {
  content:'';
  position:fixed; top:0; left:0; width:100%; height:40px;
  background:rgba(255,23,68,.04);
  animation:scanline 8s linear infinite;
  pointer-events:none; z-index:9999;
}

p, label {
  font-family:'Barlow',sans-serif!important;
  color:var(--text);
}
/* span ve div'de sadece renk — font-family HAYIR (expander icon bozuluyor) */
span, div {
  color:var(--text);
}
/* Streamlit metin container'larına Barlow aç */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] *,
[data-testid="stText"],
[data-testid="stCaptionContainer"],
.stAlert p,
.stSuccess p, .stInfo p, .stWarning p, .stError p,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"],
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-testid="stCheckbox"] span,
[data-testid="stCheckbox"] p,
[data-testid="stRadio"] span,
[data-testid="stRadio"] p,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stSelectbox"] label,
[data-testid="stToggle"] label,
[data-testid="stSlider"] label {
  font-family:'Barlow',sans-serif!important;
}
h1,h2,h3,h4 {
  font-family:'Bebas Neue',sans-serif!important;
  letter-spacing:.07em!important;
  font-weight:400!important;
  text-transform:uppercase!important;
  animation:fadeSlideRight .45s ease both;
}
h1 { font-size:2.5rem!important; }
h2 { font-size:1.85rem!important; }
h3 { font-size:1.3rem!important; }

/* ── Chrome cleanup ───────────────────────────────────── */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {
  display:none!important;
}

/* ── Layout ───────────────────────────────────────────── */
.main .block-container {
  padding:2rem 2.5rem 5rem!important;
  max-width:1180px!important;
}
section[data-testid="stSidebar"] { display:none!important; }

/* ── Divider ──────────────────────────────────────────── */
hr {
  border:none!important; height:1px!important;
  background:linear-gradient(90deg,transparent,var(--border2) 20%,var(--border2) 80%,transparent)!important;
  margin:2rem 0!important;
}

/* ── Primary button ───────────────────────────────────── */
button[data-testid="stBaseButton-primary"] {
  background:var(--grad)!important;
  color:#040205!important;
  border:none!important;
  font-family:'Bebas Neue',sans-serif!important;
  font-weight:400!important;
  letter-spacing:.13em!important;
  font-size:1rem!important;
  border-radius:var(--radius)!important;
  box-shadow:var(--glow)!important;
  transition:transform .15s, box-shadow .25s!important;
  position:relative!important;
  overflow:hidden!important;
}
button[data-testid="stBaseButton-primary"]:hover {
  transform:translateY(-2px)!important;
  box-shadow:0 0 44px rgba(255,23,68,.65), 0 6px 24px rgba(0,0,0,.5)!important;
}
button[data-testid="stBaseButton-primary"]:active {
  transform:translateY(0)!important;
}

/* ── Secondary button ─────────────────────────────────── */
button[data-testid="stBaseButton-secondary"] {
  background:transparent!important;
  border:1px solid var(--border2)!important;
  color:var(--muted)!important;
  border-radius:var(--radius)!important;
  font-family:'Barlow',sans-serif!important;
  font-weight:600!important;
  letter-spacing:.03em!important;
  transition:border-color .2s, color .2s, box-shadow .2s!important;
}
button[data-testid="stBaseButton-secondary"]:hover {
  border-color:var(--red)!important;
  color:var(--text)!important;
  box-shadow:0 0 14px rgba(255,23,68,.2)!important;
}

/* ── Inputs ───────────────────────────────────────────── */
input, textarea, [data-baseweb="select"] > div {
  background:var(--surface)!important;
  border:1px solid var(--border2)!important;
  border-radius:var(--radius)!important;
  color:var(--text)!important;
  font-family:'Barlow',sans-serif!important;
  transition:border-color .2s, box-shadow .2s!important;
}
input:focus, textarea:focus {
  border-color:var(--red)!important;
  box-shadow:0 0 0 2px rgba(255,23,68,.15), 0 0 20px rgba(255,23,68,.08)!important;
  outline:none!important;
}

/* ── Form container ───────────────────────────────────── */
[data-testid="stForm"] {
  background:var(--surface)!important;
  border:1px solid var(--border2)!important;
  border-left:3px solid var(--red)!important;
  border-radius:var(--radius)!important;
  padding:2rem!important;
  animation:borderCycle 4s ease-in-out infinite, fadeSlideUp .5s ease both;
  box-shadow:inset 0 0 60px rgba(255,23,68,.025)!important;
}

/* ── Tabs ─────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
  background:var(--surface)!important;
  border-radius:var(--radius)!important;
  padding:3px!important; gap:2px!important;
  border:1px solid var(--border2)!important;
}
[data-baseweb="tab"] {
  border-radius:2px!important;
  color:var(--muted)!important;
  font-family:'Barlow Condensed',sans-serif!important;
  font-weight:700!important;
  letter-spacing:.08em!important;
  text-transform:uppercase!important;
  font-size:.82rem!important;
  transition:color .2s!important;
}
[aria-selected="true"][data-baseweb="tab"] {
  background:var(--surf2)!important;
  color:var(--red)!important;
}
[data-baseweb="tab-highlight"] { display:none!important; }

/* ── Expander ─────────────────────────────────────────── */
[data-testid="stExpander"] {
  background:var(--surface)!important;
  border:1px solid var(--border2)!important;
  border-radius:var(--radius)!important;
  transition:border-color .25s, box-shadow .25s!important;
}
[data-testid="stExpander"]:hover {
  border-color:#3A1624!important;
  box-shadow:0 0 20px rgba(255,23,68,.06)!important;
}
/* Expander label metni — Barlow fontunu açıkça ver */
[data-testid="stExpander"] p,
[data-testid="stExpander"] .streamlit-expanderHeader p {
  font-family:'Barlow',sans-serif!important;
}
/* Expander toggle icon (ok) — font-family'yi browser default'a sıfırla */
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpander"] [class*="Arrow"],
[data-testid="stExpander"] [class*="arrow"],
[data-testid="stExpander"] [class*="Icon"],
[data-testid="stExpander"] [class*="icon"],
[data-testid="stExpander"] [class*="Toggle"],
[data-testid="stExpander"] [class*="toggle"],
[data-testid="stExpander"] svg {
  font-family:initial!important;
  color:var(--muted)!important;
}

/* ── Metrics ──────────────────────────────────────────── */
[data-testid="metric-container"] {
  background:var(--surface)!important;
  border:1px solid var(--border2)!important;
  border-top:2px solid var(--red)!important;
  border-radius:var(--radius)!important;
  padding:1.25rem 1.5rem!important;
  animation:fadeSlideUp .4s ease both, countPop .5s ease both;
  position:relative!important; overflow:hidden!important;
}
[data-testid="metric-container"]::before {
  content:'';
  position:absolute; top:0; left:0; right:0; height:50px;
  background:radial-gradient(ellipse at 50% -10%,rgba(255,23,68,.14),transparent 70%);
  pointer-events:none;
}
[data-testid="stMetricValue"] {
  font-family:'Bebas Neue',sans-serif!important;
  font-size:2.5rem!important;
  letter-spacing:.04em!important;
  color:var(--text)!important;
}

/* ── Alerts ───────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius:var(--radius)!important;
  border-left-width:3px!important;
  animation:fadeSlideRight .35s ease both!important;
}

/* ── DataFrame ────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border-radius:var(--radius)!important;
  overflow:hidden!important;
  border:1px solid var(--border2)!important;
  animation:fadeSlideUp .4s ease both;
}

/* ── Progress ─────────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
  background:var(--grad)!important;
  border-radius:0!important;
  animation:progressGlow 2s ease-in-out infinite;
}
[data-testid="stProgress"] > div {
  border-radius:0!important;
  background:var(--surf2)!important;
  height:4px!important;
}

/* ── Caption ──────────────────────────────────────────── */
[data-testid="stCaptionContainer"] {
  color:var(--muted)!important;
  font-size:.8rem!important;
}

/* ── Stepper ──────────────────────────────────────────── */
.lc-stepper {
  display:flex; align-items:center;
  margin:0 0 1.5rem; padding:14px 0;
  border-bottom:1px solid var(--border2);
  animation:fadeSlideDown .4s ease both;
}
.lc-step {
  display:flex; align-items:center; gap:7px;
  font-family:'Barlow Condensed',sans-serif;
  font-size:.76rem; font-weight:800;
  letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted2); padding:4px 0;
  transition:color .3s;
}
.lc-step.done { color:var(--muted2); }
.lc-step.done .lc-num { color:#7A2A38; }
.lc-step.active { color:var(--text); }
.lc-step.active .lc-num {
  color:var(--red);
  animation:glowPulse 2.5s ease-in-out infinite;
}
.lc-num {
  font-family:'Bebas Neue',sans-serif;
  font-size:1.05rem; min-width:16px;
}
.lc-line {
  flex:1; height:1px;
  background:var(--border2);
  min-width:12px; margin:0 6px;
}

/* ── Sector table cell overflow fix ──────────────────── */
[data-testid="stColumn"] p,
[data-testid="stColumn"] .stMarkdown {
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  min-width: 0 !important;
}

/* ── Landing card hover via :has() ───────────────────── */
[data-testid="stColumn"]:has(.lc-card) {
  transition:transform .3s;
}
[data-testid="stColumn"]:has(.lc-card):hover .lc-card {
  border-color:rgba(255,23,68,.5)!important;
  box-shadow:0 0 50px rgba(255,23,68,.14), inset 0 0 40px rgba(255,23,68,.04)!important;
  transform:translateY(-3px);
}
.lc-card {
  transition:border-color .3s, box-shadow .3s, transform .3s!important;
}
</style>
""", unsafe_allow_html=True)

# --- Session State ---
AUTOMATION_PRESETS = [
    "WhatsApp Chatbotu (müşteri destek, randevu, satış)",
    "Instagram DM Botu (takipçi dönüşümü, müşteri iletişimi)",
    "Web Sitesi Chatbotu (lead yakalama, destek)",
    "Satış Funnel Otomasyonu (lead'den müşteriye dönüşüm)",
    "CRM Entegrasyonu (HubSpot, Pipedrive, Salesforce)",
    "İçerik Üretim Otomasyonu (blog, sosyal medya, ürün açıklaması)",
    "Raporlama & Dashboard (Meta, Google, satış verileri)",
    "Randevu & Rezervasyon Sistemi",
    "Teklif & Onboarding Otomasyonu",
    "E-posta Kampanya Otomasyonu",
]

defaults = {
    "sectors_data": [],
    "selected_keywords": [],
    "selected_en_keywords": [],
    "selected_apollo_industries": [],
    "selected_sector_names": [],
    "job_titles_data": [],
    "selected_job_titles": [],
    "sector_input_value": "",
    "automation_input_value": "",
    "country_input_value": ["Turkey"],
    "company_sizes_value": ["11 - 50", "51 - 200"],
    "company_size_filter_enabled": True,
    "company_size_rec": {},
    # Şirket seçimi
    "active_company": "",
    "phlantic_apify_key": "",
    "phlantic_instantly_key": "",
    "sectors_approved": False,
    "step1_done": False,
    # Adım 2
    "leads_raw": [],
    "step2_done": False,
    # Adım 3
    "leads_analyzed": [],
    "step3_done": False,
    # Adım 4
    "leads_approved": [],
    "step4_ready": False,
    "email_sequences": {},
    "step4_done": False,
    # Adım 5
    "step5_done": False,
    "instantly_campaign_id": "",
    "instantly_upload_result": {},
    "campaign_launched": False,
    # API cache (her render'da tekrar çağrılmasın)
    "instantly_accounts_cache": None,
    "instantly_campaigns_cache": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================
# LOGIN GATE
# ============================================================
_APP_PASSWORD = st.secrets.get("APP_PASSWORD", "beyza1234")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height:15vh'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem;">
          <div style="font-family:'Bebas Neue',sans-serif;font-size:3.5rem;letter-spacing:.12em;
                      white-space:nowrap;
                      background:linear-gradient(135deg,#FF1744,#FF6B35);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      margin-bottom:4px;">CATHLANTIC</div>
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:.85rem;letter-spacing:.3em;
                      color:#7A3040;text-transform:uppercase;">OPERATING SYSTEM</div>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            pwd = st.text_input("Şifre", type="password", placeholder="••••••••••••", label_visibility="collapsed")
            submitted = st.form_submit_button("GİRİŞ", use_container_width=True, type="primary")
            if submitted:
                if pwd == _APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Hatalı şifre.")
    st.stop()

# ============================================================
# LANDING — ŞİRKET SEÇİMİ
# ============================================================
def _reset_campaign_state():
    preserve = {"active_company", "phlantic_apify_key", "phlantic_instantly_key"}
    for k in list(st.session_state.keys()):
        if k not in preserve:
            del st.session_state[k]

# --- Landing: iki sabit sekme ---
if not st.session_state.active_company:
    # Hero bölümü
    st.markdown("""
    <style>
    @keyframes heroTitle {
      0%   { opacity:0; transform:translateY(30px) skewX(-2deg); }
      100% { opacity:1; transform:translateY(0) skewX(0deg); }
    }
    @keyframes heroSub {
      0%   { opacity:0; letter-spacing:.4em; }
      100% { opacity:1; letter-spacing:.12em; }
    }
    @keyframes heroPill {
      0%   { opacity:0; transform:scaleX(.6); }
      100% { opacity:1; transform:scaleX(1); }
    }
    @keyframes cardEntrance {
      0%   { opacity:0; transform:translateY(32px); }
      100% { opacity:1; transform:translateY(0); }
    }
    </style>

    <div style='text-align:center;padding:5.5rem 0 3.5rem;position:relative'>
      <!-- pill -->
      <div style='display:inline-flex;align-items:center;gap:12px;margin-bottom:2rem;
                  animation:heroPill .6s cubic-bezier(.22,1,.36,1) both'>
        <div style='width:48px;height:1px;background:linear-gradient(90deg,transparent,#FF1744)'></div>
        <span style='font-family:"Barlow Condensed",sans-serif;font-size:.68rem;font-weight:800;
                     letter-spacing:.38em;text-transform:uppercase;color:#FF1744'>
          ⚡ GROWTH ENGINE
        </span>
        <div style='width:48px;height:1px;background:linear-gradient(90deg,#FF1744,transparent)'></div>
      </div>

      <!-- main title -->
      <div style='animation:heroTitle .7s .1s cubic-bezier(.22,1,.36,1) both'>
        <div style='font-family:"Bebas Neue",sans-serif;
                    font-size:clamp(4rem,10vw,7rem);
                    letter-spacing:.07em;color:#FFE8E8;
                    margin:0;line-height:.88;
                    text-shadow:0 0 80px rgba(255,23,68,.15)'>CATHLANTIC</div>
        <div style='font-family:"Bebas Neue",sans-serif;
                    font-size:clamp(1.6rem,4.5vw,3rem);
                    letter-spacing:.22em;
                    background:linear-gradient(135deg,#FF1744,#FF6B35);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    margin:.15rem 0 0;line-height:1.2'>OPERATING SYSTEM</div>
      </div>

      <!-- subtitle -->
      <p style='font-family:"Barlow Condensed",sans-serif;
                color:#4A2530;font-size:.78rem;font-weight:600;
                letter-spacing:.18em;text-transform:uppercase;
                margin:1.6rem 0 0;
                animation:heroSub .9s .3s ease both'>
        Apify &nbsp;·&nbsp; Anthropic &nbsp;·&nbsp; Instantly.ai
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Motion One — animated waveform (CDN via iframe)
    components.html("""
    <!DOCTYPE html><html>
    <head>
    <style>
      *{margin:0;padding:0;box-sizing:border-box}
      body{background:transparent;overflow:hidden}
      #wave{display:flex;gap:2px;height:44px;align-items:flex-end;
            justify-content:center;padding:0 12px;opacity:.85}
      .bar{flex:1;max-width:10px;min-width:2px;
           background:linear-gradient(180deg,#FF1744 0%,#FF6B35 100%);
           border-radius:1px 1px 0 0;opacity:0;transform-origin:bottom;
           transform:scaleY(0)}
    </style>
    </head>
    <body>
    <div id="wave"></div>
    <script src="https://cdn.jsdelivr.net/npm/motion@12/dist/motion.js"></script>
    <script>
      const wave = document.getElementById('wave');
      const N = 72;
      const hs = Array.from({length:N}, (_,i) => {
        const t = i/N, c = .5;
        const bell = Math.exp(-Math.pow((t-c)/.22,2));
        return 6 + bell * 34 + Math.random() * 8;
      });
      hs.forEach(h => {
        const b = document.createElement('div');
        b.className = 'bar'; b.style.height = h+'px'; wave.appendChild(b);
      });
      const {animate, stagger} = Motion;
      animate('.bar',
        {opacity:[0,.85], scaleY:[0,1]},
        {delay: stagger(.018,{from:'center'}),
         duration:.65, easing:[.22,1,.36,1]}
      );
    </script>
    </body></html>
    """, height=50)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    _, col_l, col_gap, col_r, _ = st.columns([1, 4, 0.4, 4, 1])

    with col_l:
        st.markdown("""
        <div class='lc-card' style='background:#090408;border:1px solid #2A0E1C;
                    border-top:3px solid #FF1744;border-radius:3px;padding:40px 30px;
                    text-align:center;position:relative;overflow:hidden;
                    animation:cardEntrance .7s .4s cubic-bezier(.22,1,.36,1) both'>
          <div style='position:absolute;top:0;left:0;right:0;height:1px;
                      background:linear-gradient(90deg,transparent,rgba(255,23,68,.5),transparent)'></div>
          <div style='position:absolute;top:0;right:0;width:80px;height:80px;
                      background:radial-gradient(circle at 100% 0,rgba(255,23,68,.12),transparent 70%)'></div>
          <div style='font-size:2.8rem;margin-bottom:1.3rem;
                      filter:drop-shadow(0 0 12px rgba(255,23,68,.4))'>🚀</div>
          <div style='font-family:"Bebas Neue",sans-serif;font-size:2.4rem;letter-spacing:.1em;
                      color:#FFE8E8;margin:0 0 .6rem'>LCADREON</div>
          <div style='width:40px;height:2px;background:linear-gradient(90deg,#FF1744,#FF6B35);
                      margin:0 auto .9rem'></div>
          <p style='font-family:"Barlow",sans-serif;color:#6B3847;font-size:.85rem;
                    margin:0;line-height:1.75;letter-spacing:.01em'>
            Ana şirket hesabı<br>
            Keyler &nbsp;<code style='background:#150810;padding:2px 7px;border-radius:2px;
                                color:#FF6B35;font-size:.78rem;border:1px solid #2A0E1C'>.env</code>&nbsp;'den okunur
          </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("LCADREON'A GİR →", key="btn_lcadreon", type="primary", use_container_width=True):
            st.session_state.active_company = "LCadreon"
            st.rerun()

    with col_r:
        st.markdown("""
        <div class='lc-card' style='background:#090408;border:1px solid #2A0E1C;
                    border-top:3px solid #FF6B35;border-radius:3px;padding:40px 30px;
                    text-align:center;position:relative;overflow:hidden;
                    animation:cardEntrance .7s .55s cubic-bezier(.22,1,.36,1) both'>
          <div style='position:absolute;top:0;left:0;right:0;height:1px;
                      background:linear-gradient(90deg,transparent,rgba(255,107,53,.5),transparent)'></div>
          <div style='position:absolute;top:0;right:0;width:80px;height:80px;
                      background:radial-gradient(circle at 100% 0,rgba(255,107,53,.1),transparent 70%)'></div>
          <div style='font-size:2.8rem;margin-bottom:1.3rem;
                      filter:drop-shadow(0 0 12px rgba(255,107,53,.35))'>🔷</div>
          <div style='font-family:"Bebas Neue",sans-serif;font-size:2.4rem;letter-spacing:.1em;
                      color:#FFE8E8;margin:0 0 .6rem'>PHLANTIC</div>
          <div style='width:40px;height:2px;background:linear-gradient(90deg,#FF6B35,#FF1744);
                      margin:0 auto .9rem'></div>
          <p style='font-family:"Barlow",sans-serif;color:#6B3847;font-size:.85rem;
                    margin:0;line-height:1.75;letter-spacing:.01em'>
            İkinci şirket hesabı<br>
            Apify &amp; Instantly keyleri girilir
          </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("PHLANTIC'E GİR →", key="btn_phlantic", use_container_width=True):
            st.session_state.active_company = "Phlantic"
            st.rerun()

    # Alt imza
    st.markdown("""
    <div style='text-align:center;margin-top:3rem;
                animation:fadeIn 1s .9s ease both;opacity:0;animation-fill-mode:both'>
      <span style='font-family:"Barlow Condensed",sans-serif;font-size:.7rem;font-weight:600;
                   letter-spacing:.2em;text-transform:uppercase;color:#2A0E1C'>
        v2.0 &nbsp;·&nbsp; Motion × UI/UX Pro Max
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# --- Phlantic key girişi ---
if st.session_state.active_company == "Phlantic" and (
    not st.session_state.phlantic_apify_key or not st.session_state.phlantic_instantly_key
):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<h1 style='text-align:center'>🔷 Phlantic</h1>"
        "<p style='text-align:center;color:gray'>Devam etmek için API keylerini gir</p>",
        unsafe_allow_html=True,
    )
    _, col_form, _ = st.columns([1, 3, 1])
    with col_form:
        with st.form("phlantic_keys_form", clear_on_submit=False):
            ph_apify     = st.text_input("Apify API Key", type="password", placeholder="apify_api_...")
            ph_instantly = st.text_input("Instantly API Key", type="password", placeholder="...")
            st.caption("Anthropic AI keyi LCadreon'a aittir, ayrıca girmen gerekmez.")
            col_back, col_save = st.columns(2)
            with col_back:
                back_clicked = st.form_submit_button("← Geri", use_container_width=True)
            with col_save:
                save_clicked = st.form_submit_button("Devam Et →", type="primary", use_container_width=True)
            if back_clicked:
                st.session_state.active_company = ""
                st.rerun()
            if save_clicked:
                if not ph_apify.strip() or not ph_instantly.strip():
                    st.error("Her iki keyi de gir.")
                else:
                    st.session_state.phlantic_apify_key     = ph_apify.strip()
                    st.session_state.phlantic_instantly_key = ph_instantly.strip()
                    st.rerun()
    st.stop()

# Aktif key'leri belirle
_apify_key     = st.session_state.phlantic_apify_key     if st.session_state.active_company == "Phlantic" else ""
_instantly_key = st.session_state.phlantic_instantly_key if st.session_state.active_company == "Phlantic" else ""

# --- Başlık ---
_is_lc    = st.session_state.active_company == "LCadreon"
_icon_lbl = "🚀 LCADREON" if _is_lc else "🔷 PHLANTIC"
_hdr_grad = "linear-gradient(135deg,#FF1744 0%,#FF6B35 100%)" if _is_lc else "linear-gradient(135deg,#FF6B35 0%,#FF1744 100%)"

col_hdr, col_switch = st.columns([8, 1])
with col_hdr:
    st.markdown(
        f"<h1 style='font-family:\"Bebas Neue\",sans-serif;font-size:2rem;letter-spacing:.06em;"
        f"background:{_hdr_grad};"
        f"-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0'>"
        f"{_icon_lbl} — B2B SOĞUK E-POSTA OS</h1>"
        f"<p style='color:#7A4A52;font-size:.8rem;margin:4px 0 0;letter-spacing:.08em'>Apify · Anthropic · Instantly.ai</p>",
        unsafe_allow_html=True,
    )
with col_switch:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("↩ Çıkış", help="Hesap seçim ekranına dön"):
        _reset_campaign_state()
        st.session_state.active_company = ""
        st.session_state.phlantic_apify_key = ""
        st.session_state.phlantic_instantly_key = ""
        st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# --- Step Progress ---
_s = st.session_state
def _step_class(n):
    if n == 5 and _s.step5_done: return "done"
    if n == 4 and (_s.step4_done or _s.step4_ready): return "done" if _s.step4_done else "active"
    if n == 3 and _s.step3_done: return "done"
    if n == 2 and _s.step2_done: return "done"
    if n == 1 and _s.step1_done: return "done"
    active_step = (5 if _s.step4_done else
                   4 if (_s.step4_ready or _s.step3_done) else
                   3 if _s.step2_done else
                   2 if _s.step1_done else 1)
    return "active" if n == active_step else ""

steps = [("1","Sektör"),("2","Lead"),("3","Analiz"),("4","Sekans"),("5","Gönder")]
stepper_html = "<div class='lc-stepper'>"
for i,(num,label) in enumerate(steps):
    cls = _step_class(int(num))
    stepper_html += f"<div class='lc-step {cls}'><span class='lc-num'>{num}</span>{label}</div>"
    if i < len(steps)-1:
        stepper_html += "<div class='lc-line'></div>"
stepper_html += "</div>"
st.markdown(stepper_html, unsafe_allow_html=True)
st.divider()

# ============================================================
# ADIM 1A: SEKTÖR GENİŞLETME
# ============================================================
st.header("Adım 1 — Sektör Genişletme, Keyword & Hedef Unvan Üretimi")
st.markdown(
    "Ana sektörünü gir. Yapay zeka niş sektörleri, Apify keywordlerini "
    "ve şirkette söz sahibi karar vericilerin unvanlarını otomatik üretecek."
)

with st.form("sector_form"):
    col_s, col_a = st.columns([1, 1])
    with col_s:
        sector_input = st.text_input(
            "Ana Sektör",
            placeholder="örn: E-ticaret, Sağlık, İnşaat, Emlak...",
            help="Hedef sektörü Türkçe veya İngilizce yazabilirsin."
        )
    with col_a:
        automation_presets_selected = st.multiselect(
            "Sunduğun Otomasyon(lar)",
            options=AUTOMATION_PRESETS,
            placeholder="Listeden seç (birden fazla olabilir)...",
            help="Hangi otomasyon/hizmeti satıyorsun?"
        )
    automation_custom = st.text_input(
        "Özel otomasyon / ek açıklama (isteğe bağlı)",
        placeholder="örn: Trendyol sipariş takip botu, AI destekli fiyat analizi...",
        help="Listede yoksa kendin yaz veya detay ekle."
    )
    submitted = st.form_submit_button("🔍 Sektörleri Genişlet", type="primary", use_container_width=True)

if submitted:
    if not sector_input.strip():
        st.error("Lütfen bir sektör gir.")
    elif not automation_presets_selected and not automation_custom.strip():
        st.error("Lütfen en az bir otomasyon/hizmet seç veya yaz.")
    else:
        automation_parts = list(automation_presets_selected)
        if automation_custom.strip():
            automation_parts.append(automation_custom.strip())
        automation_value = ", ".join(automation_parts)

        with st.spinner(f"**{sector_input}** + **{automation_value[:60]}** için niş sektörler üretiliyor..."):
            try:
                sectors = expand_sectors(sector_input.strip(), automation_value)
                st.session_state.sectors_data = sectors
                st.session_state.sector_input_value = sector_input.strip()
                st.session_state.automation_input_value = automation_value
                st.session_state.sectors_approved = False
                st.session_state.job_titles_data = []
                st.session_state.selected_job_titles = []
                st.session_state.selected_keywords = []
                st.session_state.step1_done = False
            except (ValueError, RuntimeError) as e:
                st.error(f"Hata: {e}")
                st.stop()

# ============================================================
# SEKTÖR TABLOSU & SEÇİM
# ============================================================
if st.session_state.sectors_data and not st.session_state.sectors_approved:
    st.subheader(f"Bulunan Alt/Yan Sektörler ({len(st.session_state.sectors_data)} adet)")
    st.markdown("Apify'a göndermek istediğin sektörleri seç, ardından **Onayla** butonuna bas.")

    selected_sectors = []
    # Başlık satırı
    h0, h1, h2, h3, h4, h5 = st.columns([0.5, 2, 2.5, 2, 2, 1.5])
    with h1: st.caption("**Sektör**")
    with h2: st.caption("**Neden hedef?**")
    with h3: st.caption("**Apollo Industries**")
    with h4: st.caption("**🇬🇧 Keywords (Apify)**")
    with h5: st.caption("**🇹🇷 TR (UI)**")
    st.divider()

    for i, item in enumerate(st.session_state.sectors_data):
        col_check, col_name, col_reason, col_ind, col_kw_en, col_kw_tr = st.columns([0.5, 2, 2.5, 2, 2, 1.5])
        with col_check:
            checked = st.checkbox("", key=f"sector_{i}", value=True)
        with col_name:
            st.markdown(f"**{item['sector_name']}**")
        with col_reason:
            st.caption(item["reason"])
        with col_ind:
            apollo_inds = item.get("apollo_industries", [])
            if apollo_inds:
                st.markdown(" · ".join([f"`{ind}`" for ind in apollo_inds]))
            else:
                st.caption("—")
        with col_kw_en:
            st.markdown(" · ".join([f"`{kw}`" for kw in item.get("keywords_en", [])]))
        with col_kw_tr:
            st.caption(" · ".join(item.get("keywords_tr", [])))
        if checked:
            selected_sectors.append(item)

    st.divider()
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        total_en  = sum(len(s.get("keywords_en", [])) for s in selected_sectors)
        total_ind = len({ind for s in selected_sectors for ind in s.get("apollo_industries", [])})
        st.info(
            f"**{len(selected_sectors)}** sektör seçildi · "
            f"🏷️ **{total_ind}** Apollo Industry · "
            f"🔑 **{total_en}** EN keyword · "
            f"Apify'a gidecek (TR keywordler hariç)"
        )
    with col_btn:
        if st.button("✅ Sektörleri Onayla →", type="primary", use_container_width=True):
            if not selected_sectors:
                st.warning("En az bir sektör seçmelisin.")
            else:
                all_keywords = []
                all_en_keywords = []
                all_names = []
                all_apollo_industries = []
                for s in selected_sectors:
                    all_keywords.extend(s.get("keywords_tr", []))
                    all_keywords.extend(s.get("keywords_en", []))
                    all_en_keywords.extend(s.get("keywords_en", []))  # sadece EN — Apify'a bunlar gider
                    all_names.append(s["sector_name"])
                    all_apollo_industries.extend(s.get("apollo_industries", []))
                st.session_state.selected_keywords = list(dict.fromkeys(all_keywords))
                st.session_state.selected_en_keywords = list(dict.fromkeys(all_en_keywords))
                st.session_state.selected_apollo_industries = list(dict.fromkeys(all_apollo_industries))
                st.session_state.selected_sector_names = all_names
                st.session_state.sectors_approved = True
                st.rerun()

# ============================================================
# ADIM 1B: JOB TITLE ÜRETİMİ (sektörler onaylandıktan sonra)
# ============================================================
if st.session_state.sectors_approved:

    # TR/EN ayrımı için sektör verilerinden çek
    all_kw_tr, all_kw_en = [], []
    for s in st.session_state.sectors_data:
        if s["sector_name"] in st.session_state.selected_sector_names:
            all_kw_tr.extend(s.get("keywords_tr", []))
            all_kw_en.extend(s.get("keywords_en", []))
    all_kw_tr = list(dict.fromkeys(all_kw_tr))
    all_kw_en = list(dict.fromkeys(all_kw_en))

    auto_label = st.session_state.automation_input_value
    auto_short = (auto_label[:55] + "...") if len(auto_label) > 58 else auto_label
    with st.expander(
        f"✅ Sektörler onaylandı — "
        f"🏷️ {len(st.session_state.selected_apollo_industries)} Apollo Industry · "
        f"🔑 {len(all_kw_en)} EN keyword · "
        f"{len(st.session_state.selected_sector_names)} sektör · 🤖 {auto_short}",
        expanded=False
    ):
        col_ind, col_en = st.columns(2)
        with col_ind:
            st.caption("🏷️ Apollo Industries (industry filtresi)")
            st.code("\n".join(st.session_state.selected_apollo_industries) or "(yok)", language=None)
        with col_en:
            st.caption("🔑 Keywords EN (industryKeywords filtresi)")
            st.code(", ".join(all_kw_en), language=None)

    st.divider()

    # Job title üretimini tetikle
    if not st.session_state.job_titles_data:
        with st.spinner("Karar verici ve satın alma yetkili unvanlar üretiliyor (Haiku)..."):
            try:
                titles = generate_job_titles(
                    st.session_state.sector_input_value,
                    st.session_state.selected_sector_names
                )
                st.session_state.job_titles_data = titles
            except (ValueError, RuntimeError) as e:
                st.error(f"Job title üretim hatası: {e}")
                st.stop()

    if st.session_state.job_titles_data:
        # Yetki seviyesine göre grupla
        levels = ["C-Level", "Director", "Manager", "Owner"]
        level_colors = {
            "C-Level": "🔴",
            "Director": "🟠",
            "Manager": "🟡",
            "Owner": "🟣",
        }

        st.subheader(f"Karar Verici Unvanlar ({len(st.session_state.job_titles_data)} adet)")
        st.markdown(
            "Sadece **satın alma yetkisi veya karar gücü** olan pozisyonlar listelendi. "
            "Apify'a göndermek istediklerini seç."
        )

        selected_titles = []

        for level in levels:
            level_items = [t for t in st.session_state.job_titles_data if t.get("authority_level") == level]
            if not level_items:
                continue

            st.markdown(f"#### {level_colors.get(level, '⚪')} {level}")

            for i, title in enumerate(level_items):
                col_check, col_tr, col_en, col_why = st.columns([0.5, 2, 2, 5])
                global_idx = st.session_state.job_titles_data.index(title)

                with col_check:
                    checked = st.checkbox("", key=f"title_{global_idx}", value=True)
                with col_tr:
                    st.markdown(f"**{title['tr']}**")
                with col_en:
                    st.caption(title["en"])
                with col_why:
                    st.caption(f"_{title.get('why', '')}_")

                if checked:
                    selected_titles.append(title)

        st.divider()
        col_info2, col_btn2 = st.columns([3, 1])
        with col_info2:
            st.info(
                f"**{len(selected_titles)}** unvan seçildi · "
                f"Apify'a **{len(selected_titles)}** EN unvan gönderilecek "
                f"(Türkçe unvanlar Apollo DB'de geçersiz, otomatik filtrelenir)"
            )
        with col_btn2:
            if st.button("✅ Onayla ve Adım 2'ye İlerle", type="primary", use_container_width=True):
                if not selected_titles:
                    st.warning("En az bir unvan seçmelisin.")
                else:
                    st.session_state.selected_job_titles = selected_titles
                    st.session_state.step1_done = True
                    st.rerun()

# ============================================================
# ADIM 1 TAMAMLANDI — ÖZET
# ============================================================
if st.session_state.step1_done:
    tr_titles = [t["tr"] for t in st.session_state.selected_job_titles]
    en_titles = [t["en"] for t in st.session_state.selected_job_titles]
    all_titles = tr_titles + en_titles

    st.success(
        f"**Adım 1 tamamlandı!** · "
        f"{len(st.session_state.selected_apollo_industries)} Apollo industry · "
        f"{len([k for k in st.session_state.selected_keywords if not any(c in k for c in 'ğüşıöçĞÜŞİÖÇ')])} EN keyword · "
        f"{len(en_titles)} EN unvan · Apify'a hazır."
    )

    col_kw, col_title = st.columns(2)
    with col_kw:
        with st.expander("📦 Apify'a Gidecek Parametreler"):
            apollo_inds = st.session_state.selected_apollo_industries
            en_kws = [k for k in st.session_state.selected_keywords if not any(
                c in k for c in "ğüşıöçĞÜŞİÖÇ"
            )]
            c1, c2 = st.columns(2)
            with c1:
                st.caption("🏷️ Apollo Industries")
                st.code("\n".join(apollo_inds) if apollo_inds else "(yok)", language=None)
            with c2:
                st.caption("🔑 Keywords EN")
                st.code("\n".join(en_kws), language=None)
    with col_title:
        with st.expander("👔 Onaylanan Unvanlar (TR + EN)"):
            c1, c2 = st.columns(2)
            with c1:
                st.caption("🇹🇷 Türkçe")
                st.code("\n".join(tr_titles), language=None)
            with c2:
                st.caption("🇬🇧 English")
                st.code("\n".join(en_titles), language=None)

    st.divider()

    # ============================================================
    # ADIM 2: APİFY VERI ÇEKME
    # ============================================================
    col_h2, col_back2 = st.columns([5, 1])
    col_h2.header("Adım 2 — Apify Lead Çekme")
    if col_back2.button("← Adım 1'e Dön", key="back_to_step1", use_container_width=True):
        st.session_state.step1_done = False
        for k in ["leads_raw", "step2_done", "leads_analyzed", "step3_done",
                  "leads_approved", "step4_ready", "step4_done", "email_sequences",
                  "step5_done", "instantly_campaign_id", "instantly_upload_result",
                  "campaign_launched"]:
            st.session_state[k] = defaults[k]
        st.rerun()

    tr_titles_all = [t["tr"] for t in st.session_state.selected_job_titles]
    en_titles_all = [t["en"] for t in st.session_state.selected_job_titles]
    all_job_titles = tr_titles_all + en_titles_all

    tab_basic, tab_size = st.tabs(["⚙️ Temel Parametreler", "🏢 Şirket Büyüklüğü"])

    with tab_basic:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            fetch_count = st.number_input(
                "Çekilecek max lead sayısı",
                min_value=100, max_value=30000, value=100, step=100,
                help="Scraper minimum 100, maksimum 30.000. Her ~1000 lead ≈ $1.5 maliyet."
            )
        with col_b:
            only_validated = st.toggle(
                "Sadece doğrulanmış email",
                value=True,
                help="Açık = yalnızca 'validated' emailler. Kapalı = tüm emailler dahil."
            )
        with col_c:
            run_label = st.text_input(
                "Run etiketi",
                value=f"{st.session_state.sector_input_value} — LCadreon",
                help="Apify dashboard'unda görünecek isim."
            )

        COUNTRY_OPTIONS = {
            "🇹🇷 Türkiye": "Turkey",
            "🇩🇪 Almanya": "Germany",
            "🇺🇸 Amerika": "United States",
            "🇬🇧 İngiltere": "United Kingdom",
            "🇳🇱 Hollanda": "Netherlands",
            "🇫🇷 Fransa": "France",
            "🇨🇭 İsviçre": "Switzerland",
            "🇦🇹 Avusturya": "Austria",
            "🇧🇪 Belçika": "Belgium",
            "🇦🇪 BAE": "United Arab Emirates",
            "🇸🇦 Suudi Arabistan": "Saudi Arabia",
            "🇦🇿 Azerbaycan": "Azerbaijan",
            "🇰🇿 Kazakistan": "Kazakhstan",
        }
        selected_country_labels = st.multiselect(
            "🌍 Hedef Ülke(ler)",
            options=list(COUNTRY_OPTIONS.keys()),
            default=["🇹🇷 Türkiye"],
            help="Apify bu ülkelerdeki profilleri tarar. Birden fazla seçebilirsin."
        )
        selected_countries = [COUNTRY_OPTIONS[lbl] for lbl in selected_country_labels] or ["Turkey"]
        st.session_state.country_input_value = selected_countries

        with st.expander("Apify'a gönderilecek parametreleri gör"):
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                st.caption("**Apollo Industries**")
                st.code("\n".join(st.session_state.selected_apollo_industries) or "(yok)", language=None)
            with pc2:
                st.caption("**Keywords EN**")
                en_kws_apify = [k for k in st.session_state.selected_keywords
                                if not any(c in k for c in "ğüşıöçĞÜŞİÖÇ")]
                st.code("\n".join(en_kws_apify), language=None)
            with pc3:
                st.caption("**Unvanlar EN**")
                st.code("\n".join(en_titles_all), language=None)
            st.caption(
                f"**companyCountry:** {', '.join(selected_country_labels)} · "
                "**Email:** " + ("Sadece Verified" if only_validated else "Email olanlar") +
                " · **Büyüklük filtresi:** " + (
                    " · ".join(st.session_state.company_sizes_value)
                    if st.session_state.company_size_filter_enabled
                    else "Kapalı (tüm büyüklükler)"
                )
            )

    with tab_size:
        size_filter_enabled = st.toggle(
            "Şirket büyüklüğü filtresi",
            value=st.session_state.company_size_filter_enabled,
            help="Kapalı = Apollo tüm büyüklükteki şirketleri tarar (önerilir, daha fazla lead). Açık = belirli aralıkları filtrele."
        )
        st.session_state.company_size_filter_enabled = size_filter_enabled

        if not size_filter_enabled:
            st.info(
                "**Filtre kapalı** — Apollo tüm büyüklükteki şirketleri tarar. "
                "Türkiye gibi küçük Apollo pazarlarında bu mod çok daha fazla lead getirir. "
                "Sadece büyük/kurumsal şirketleri hedefliyorsan filreyi aç."
            )
        else:
            st.markdown(
                "Yapay zeka, seçtiğin sektör ve otomasyona göre en uygun büyüklükleri önerir."
            )

            if not st.session_state.company_size_rec:
                with st.spinner("AI şirket büyüklüğü önerisi üretiyor..."):
                    rec = recommend_company_sizes(
                        sector=st.session_state.sector_input_value,
                        automation=st.session_state.automation_input_value,
                    )
                    st.session_state.company_size_rec = rec

            rec = st.session_state.company_size_rec
            recommended_values = rec.get("recommended", ["11 - 50", "51 - 200"])
            reasoning = rec.get("reasoning", {})

            st.markdown("#### AI Önerisi")
            size_val_to_label = {o["value"]: o["label"] for o in COMPANY_SIZE_OPTIONS}

            if reasoning:
                for val in recommended_values:
                    label = size_val_to_label.get(val, val)
                    reason = reasoning.get(val, "")
                    st.success(f"**{label}** — {reason}")
            else:
                rec_labels = [size_val_to_label.get(v, v) for v in recommended_values]
                st.info("Önerilen: " + " · ".join(rec_labels))

            st.markdown("#### Seçimini Yap")
            st.caption("AI önerileri işaretli gelir, istediğini ekleyip çıkarabilirsin.")

            selected_sizes = []
            cols_size = st.columns(2)
            for i, opt in enumerate(COMPANY_SIZE_OPTIONS):
                col = cols_size[i % 2]
                is_recommended = opt["value"] in recommended_values
                tag = " ✨ AI önerisi" if is_recommended else ""
                checked = col.checkbox(
                    f"{opt['label']}{tag}",
                    value=is_recommended,
                    key=f"size_{opt['value']}",
                )
                if checked:
                    selected_sizes.append(opt["value"])

            if not selected_sizes:
                st.warning("En az bir büyüklük seçmelisin — AI önerisi otomatik uygulanacak.")
                selected_sizes = recommended_values

            st.session_state.company_sizes_value = selected_sizes
            st.info(
                f"**{len(selected_sizes)}** büyüklük seçildi: "
                + " · ".join(size_val_to_label.get(v, v) for v in selected_sizes)
            )

    if not st.session_state.step2_done:
        if st.button("🚀 Apify'ı Çalıştır ve Lead Çek", type="primary", use_container_width=True):
            with st.spinner("Apify çalışıyor... Lead'ler çekiliyor (bu 1-5 dakika sürebilir)..."):
                try:
                    leads, meta = run_leads_finder(
                        keywords=st.session_state.selected_en_keywords,
                        job_titles=all_job_titles,
                        fetch_count=int(fetch_count),
                        only_validated_emails=only_validated,
                        run_label=run_label,
                        countries=st.session_state.country_input_value,
                        company_sizes=(
                            st.session_state.company_sizes_value
                            if st.session_state.company_size_filter_enabled
                            else []
                        ),
                        api_key=_apify_key,
                    )
                    if meta.get("truncated"):
                        st.warning(
                            f"⚠️ Scraper limiti: {meta['keywords_sent']} keyword ve "
                            f"{meta['titles_sent']} unvan gönderildi (fazlası otomatik kesildi)."
                        )
                    if not leads:
                        raw = meta.get("raw_items", "?")
                        valid = meta.get("valid_leads", 0)
                        st.error(
                            f"Apify 0 kullanılabilir lead döndürdü. "
                            f"Apollo'dan **{raw}** ham kayıt geldi, geçerlilik filtresinden **{valid}** geçti."
                        )
                        with st.expander("🔍 Debug — Apify'a gönderilen parametreler"):
                            import json as _json
                            st.code(_json.dumps(meta.get("actor_input", {}), indent=2, ensure_ascii=False), language="json")
                        if meta.get("rejected_sample"):
                            with st.expander("🔬 Debug — Reddedilen kaydın field'ları (email/isim nerede?)"):
                                st.code(_json.dumps(meta.get("rejected_sample", {}), indent=2, ensure_ascii=False), language="json")
                        if raw == 0:
                            st.warning(
                                "Apollo hiç kayıt döndürmedi. Olası sebepler:\n"
                                "- Filtrelerin kombinasyonu çok kısıtlayıcı (büyüklük, keyword, email doğrulama)\n"
                                "- **Şirket büyüklüğü filtresini kapat** veya farklı aralık seç\n"
                                "- 'Sadece doğrulanmış email' kapatıp tekrar dene (Türkiye'de verified email sayısı az)"
                            )
                        else:
                            st.warning(
                                f"Apollo {raw} kayıt döndürdü ama geçerlilik filtresinden geçemedi. "
                                "Email veya isim alanı eksik olabilir."
                            )
                    else:
                        st.session_state.leads_raw = leads
                        st.session_state.step2_done = True
                        st.rerun()
                except (ValueError, RuntimeError) as e:
                    st.error(f"Apify Hatası: {e}")

    if st.session_state.step2_done and st.session_state.leads_raw:
        leads = st.session_state.leads_raw
        col_s2ok, col_s2reset = st.columns([5, 1])
        col_s2ok.success(f"**{len(leads)}** lead başarıyla çekildi!")
        if col_s2reset.button("🔄 Tekrar Çalıştır", help="Parametreleri değiştirip yeniden lead çek", use_container_width=True):
            for k in ["step2_done", "leads_raw", "step3_done", "leads_analyzed",
                      "step4_ready", "step4_done", "email_sequences", "step5_done",
                      "leads_approved", "instantly_campaign_id", "instantly_upload_result",
                      "campaign_launched", "instantly_accounts_cache", "instantly_campaigns_cache"]:
                st.session_state[k] = defaults[k]
            st.rerun()

        df = pd.DataFrame(leads)
        df.index = df.index + 1

        # Kolonları Türkçeleştir
        col_map = {
            "first_name": "Ad",
            "last_name": "Soyad",
            "email": "Email",
            "company_name": "Şirket",
            "company_website": "Website",
            "job_title": "Unvan",
            "location": "Konum",
        }
        df = df.rename(columns=col_map)

        st.dataframe(df, use_container_width=True, height=420)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ CSV olarak indir",
            data=csv,
            file_name=f"leads_{st.session_state.sector_input_value}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.divider()

        # ============================================================
        # ADIM 3: WEB ANALİZİ, FİLTRELEME VE CİNSİYET TESPİTİ
        # ============================================================
        col_h3, col_back3 = st.columns([5, 1])
        col_h3.header("Adım 3 — Web Analizi, Filtreleme & Cinsiyet Tespiti")
        if col_back3.button("← Adım 2'ye Dön", key="back_to_step2", use_container_width=True):
            for k in ["step2_done", "leads_raw", "leads_analyzed", "step3_done",
                      "leads_approved", "step4_ready", "step4_done", "email_sequences",
                      "step5_done", "instantly_campaign_id", "instantly_upload_result",
                      "campaign_launched"]:
                st.session_state[k] = defaults[k]
            st.rerun()
        st.markdown(
            "Her lead'in web sitesi otomatik okunur ve Haiku ile analiz edilir. "
            "**Alakası Yok** olanlar elenir, **Belki** olanları sen onaylarsın."
        )

        if not st.session_state.step3_done:
            if st.button("🔍 Analizi Başlat", type="primary", use_container_width=True):
                leads_to_analyze = st.session_state.leads_raw
                total = len(leads_to_analyze)
                analyzed = []

                progress_bar = st.progress(0, text="Hazırlanıyor...")
                status_box = st.empty()

                def process_lead(idx_lead):
                    idx, lead = idx_lead
                    site_text = fetch_homepage_text(lead.get("company_website", ""))
                    result = analyze_lead(
                        first_name=lead.get("first_name", ""),
                        website_text=site_text,
                        target_sector=st.session_state.sector_input_value,
                        automation=st.session_state.automation_input_value,
                    )
                    return {**lead, **result}

                with ThreadPoolExecutor(max_workers=6) as executor:
                    futures = {
                        executor.submit(process_lead, (i, lead)): i
                        for i, lead in enumerate(leads_to_analyze)
                    }
                    done_count = 0
                    for future in as_completed(futures):
                        result = future.result()
                        analyzed.append(result)
                        done_count += 1
                        pct = done_count / total
                        relevance = result.get("relevance", "?")
                        name = f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
                        progress_bar.progress(pct, text=f"({done_count}/{total}) {name} → {relevance}")
                        status_box.caption(f"Son: **{name}** — {result.get('reason', '')}")

                progress_bar.progress(1.0, text="Analiz tamamlandı!")
                status_box.empty()
                st.session_state.leads_analyzed = analyzed
                st.session_state.step3_done = True
                st.rerun()

        if st.session_state.step3_done and st.session_state.leads_analyzed:
            analyzed = st.session_state.leads_analyzed

            direct = [l for l in analyzed if l.get("relevance") == "Doğrudan İlişkili"]
            maybe  = [l for l in analyzed if l.get("relevance") == "Belki"]
            irrelevant = [l for l in analyzed if l.get("relevance") == "Alakası Yok"]

            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])
            c1.metric("✅ Doğrudan İlişkili", len(direct))
            c2.metric("🟡 Belki", len(maybe))
            c3.metric("❌ Alakası Yok (elindi)", len(irrelevant))
            if c4.button("🔄 Yeniden Analiz Et", use_container_width=True,
                         help="Lead listesi değişti veya analizi tekrar çalıştırmak istiyorsun"):
                for k in ["step3_done", "leads_analyzed", "step4_ready", "step4_done",
                          "email_sequences", "step5_done", "leads_approved",
                          "instantly_campaign_id", "instantly_upload_result",
                          "campaign_launched", "instantly_accounts_cache", "instantly_campaigns_cache"]:
                    st.session_state[k] = defaults[k]
                st.rerun()

            # --- Doğrudan İlişkili ---
            if direct:
                st.subheader("✅ Doğrudan İlişkili")
                df_direct = pd.DataFrame([{
                    "Ad": f"{l['first_name']} {l['last_name']}".strip(),
                    "Unvan": l.get("job_title", ""),
                    "Hitap": l.get("unvan", ""),
                    "Email": l.get("email", ""),
                    "Şirket": l.get("company_name", ""),
                    "Website": l.get("company_website", ""),
                    "Neden": l.get("reason", ""),
                } for l in direct])
                df_direct.index = df_direct.index + 1
                st.dataframe(df_direct, use_container_width=True)

            # --- Belki (Manuel İnceleme) ---
            if maybe:
                st.subheader("🟡 Belki — Manuel İnceleme")
                st.caption("Dahil etmek istediklerini seç:")
                selected_maybe = []
                for i, lead in enumerate(maybe):
                    col_chk, col_info = st.columns([0.5, 9.5])
                    with col_chk:
                        include = st.checkbox("", key=f"maybe_{i}", value=False)
                    with col_info:
                        name = f"{lead['first_name']} {lead['last_name']}".strip()
                        st.markdown(
                            f"**{name}** · {lead.get('job_title','')} @ "
                            f"[{lead.get('company_name','')}]({lead.get('company_website','#')}) "
                            f"· _{lead.get('reason','')}_"
                        )
                    if include:
                        selected_maybe.append(lead)
            else:
                selected_maybe = []

            st.divider()

            final_leads = direct + selected_maybe
            col_info3, col_btn3 = st.columns([3, 1])
            with col_info3:
                st.success(
                    f"**{len(final_leads)}** lead onaylandı "
                    f"({len(direct)} doğrudan + {len(selected_maybe)} belki seçildi)"
                )
            with col_btn3:
                if st.button("✅ Onayla ve Adım 4'e İlerle", type="primary", use_container_width=True):
                    if not final_leads:
                        st.warning("En az bir lead onaylanmalı.")
                    else:
                        st.session_state.leads_approved = final_leads
                        st.session_state.step4_ready = True
                        st.rerun()

            if st.session_state.get("step4_ready"):
                st.divider()

                # ============================================================
                # ADIM 4: SEKTÖR BAZLI E-POSTA SEKANS YAZIMI
                # ============================================================
                col_h4, col_back4 = st.columns([5, 1])
                col_h4.header("Adım 4 — E-posta Sekansı Yazımı")
                if col_back4.button("← Adım 3'e Dön", key="back_to_step3", use_container_width=True):
                    for k in ["step4_ready", "step4_done", "email_sequences", "step5_done",
                              "leads_approved", "instantly_campaign_id", "instantly_upload_result",
                              "campaign_launched"]:
                        st.session_state[k] = defaults[k]
                    st.rerun()
                st.markdown(
                    f"**{st.session_state.sector_input_value}** sektörüne özel, "
                    "yüksek dönüşümlü soğuk e-posta sekansları üretiliyor. "
                    "Sonuçları düzenleyebilirsin."
                )

                if not st.session_state.email_sequences:
                    with st.spinner("Sonnet ile e-posta sekansları yazılıyor..."):
                        try:
                            seqs = generate_email_sequences(
                                target_sector=st.session_state.sector_input_value,
                                sub_sectors=st.session_state.selected_sector_names,
                                automation=st.session_state.automation_input_value,
                            )
                            st.session_state.email_sequences = seqs
                            st.rerun()
                        except (ValueError, RuntimeError) as e:
                            st.error(f"E-posta üretim hatası: {e}")

                if st.session_state.email_sequences:
                    seqs = st.session_state.email_sequences

                    EMAIL_LABELS = {
                        "email_1_a": ("🔴 İlk Mail — A (Acı Noktası)", "pain"),
                        "email_1_b": ("🟡 İlk Mail — B (Sosyal Kanıt)", "proof"),
                        "email_1_c": ("🟣 İlk Mail — C (Merak)", "curiosity"),
                        "followup_1": ("📩 Follow-up 1 — 2. Gün", "followup"),
                        "followup_2": ("📩 Follow-up 2 — 4. Gün", "followup"),
                        "followup_3": ("💥 Follow-up 3 — Break-up (8. Gün)", "breakup"),
                    }

                    edited_seqs = {}

                    # İlk mail A/B/C — tab olarak göster
                    st.subheader("✉️ İlk Mail — 3 A/B/C Varyantı")
                    tab_a, tab_b, tab_c = st.tabs([
                        "🔴 A — Acı Noktası", "🟡 B — Sosyal Kanıt", "🟣 C — Merak"
                    ])

                    for tab, key in zip([tab_a, tab_b, tab_c], ["email_1_a", "email_1_b", "email_1_c"]):
                        with tab:
                            seq = seqs.get(key, {})
                            edited_subject = st.text_input(
                                "Konu Satırı",
                                value=seq.get("subject", ""),
                                key=f"subj_{key}"
                            )
                            edited_body = st.text_area(
                                "Mail İçeriği",
                                value=seq.get("body", ""),
                                height=200,
                                key=f"body_{key}"
                            )
                            word_count = len(edited_body.split())
                            color = "green" if word_count <= 80 else "orange" if word_count <= 100 else "red"
                            st.caption(f":{color}[{word_count} kelime]")
                            edited_seqs[key] = {"subject": edited_subject, "body": edited_body}

                    st.divider()

                    # Follow-up'lar
                    st.subheader("📬 Follow-up Sekansı")
                    fu_cols = {
                        "followup_1": ("📩 Follow-up 1 · 2. Gün", 150),
                        "followup_2": ("📩 Follow-up 2 · 4. Gün", 150),
                        "followup_3": ("💥 Break-up · 8. Gün", 160),
                    }

                    for key, (label, height) in fu_cols.items():
                        with st.expander(label, expanded=True):
                            seq = seqs.get(key, {})
                            edited_subject = st.text_input(
                                "Konu", value=seq.get("subject", ""), key=f"subj_{key}"
                            )
                            edited_body = st.text_area(
                                "İçerik", value=seq.get("body", ""), height=height, key=f"body_{key}"
                            )
                            word_count = len(edited_body.split())
                            color = "green" if word_count <= 50 else "orange" if word_count <= 70 else "red"
                            st.caption(f":{color}[{word_count} kelime]")
                            edited_seqs[key] = {"subject": edited_subject, "body": edited_body}

                    st.divider()
                    col_seq_info, col_seq_btn = st.columns([3, 1])
                    with col_seq_info:
                        st.info(
                            f"**{len(st.session_state.leads_approved)}** onaylı lead · "
                            "Instantly.ai'a aktarılmaya hazır"
                        )
                    with col_seq_btn:
                        if st.button("✅ Sekansları Onayla → Adım 5", type="primary", use_container_width=True):
                            st.session_state.email_sequences = edited_seqs
                            st.session_state.step4_done = True
                            st.rerun()

                if st.session_state.step4_done:
                    st.success("Adım 4 tamamlandı! Sekanslar onaylandı.")
                    st.divider()

                    # ============================================================
                    # ADIM 5: INSTANTLY.AI AKTARIM
                    # ============================================================
                    col_h5, col_back5 = st.columns([5, 1])
                    col_h5.header("Adım 5 — Instantly.ai'a Aktar")
                    if col_back5.button("← Adım 4'e Dön", key="back_to_step4", use_container_width=True):
                        for k in ["step4_done", "step5_done", "instantly_campaign_id",
                                  "instantly_upload_result", "campaign_launched",
                                  "instantly_accounts_cache", "instantly_campaigns_cache"]:
                            st.session_state[k] = defaults[k]
                        st.rerun()
                    st.markdown(
                        f"**{len(st.session_state.leads_approved)}** onaylı lead ve oluşturulan sekanslar "
                        "Instantly.ai'a aktarılacak. Yeni kampanya oluşturabilir veya mevcut birine ekleyebilirsin."
                    )

                    campaign_mode = st.radio(
                        "Kampanya seçeneği",
                        ["🆕 Yeni kampanya oluştur", "📋 Mevcut kampanyaya ekle"],
                        horizontal=True,
                        key="campaign_mode_radio",
                    )

                    campaign_id_to_use = ""

                    if campaign_mode == "🆕 Yeni kampanya oluştur":
                        col5a, col5b = st.columns(2)
                        with col5a:
                            camp_name = st.text_input(
                                "Kampanya adı",
                                value=f"{st.session_state.sector_input_value} — {st.session_state.active_company}",
                                key="instantly_camp_name",
                            )
                            TIMEZONE_OPTIONS = {
                                "🇹🇷 Türkiye (UTC+3)":     "Europe/Istanbul",
                                "🇩🇪 Almanya (UTC+1/2)":   "Europe/Berlin",
                                "🇬🇧 İngiltere (UTC+0/1)": "Europe/London",
                                "🇫🇷 Fransa (UTC+1/2)":    "Europe/Paris",
                                "🇦🇪 BAE (UTC+4)":         "Asia/Dubai",
                                "🇦🇿 Azerbaycan (UTC+4)":  "Asia/Baku",
                                "🇰🇿 Kazakistan (UTC+5)":  "Asia/Almaty",
                                "🇺🇸 New York (UTC-5/4)":  "America/New_York",
                                "🇺🇸 Los Angeles (UTC-8)": "America/Los_Angeles",
                            }
                            selected_tz_label = st.selectbox(
                                "Kampanya timezone",
                                options=list(TIMEZONE_OPTIONS.keys()),
                                index=0,
                                key="instantly_timezone",
                            )
                            selected_timezone = TIMEZONE_OPTIONS[selected_tz_label]
                        with col5b:
                            if st.session_state.instantly_accounts_cache is None:
                                with st.spinner("Sending hesapları yükleniyor..."):
                                    try:
                                        st.session_state.instantly_accounts_cache = list_email_accounts(api_key=_instantly_key)
                                    except Exception as e:
                                        st.session_state.instantly_accounts_cache = []
                                        st.warning(f"Hesaplar yüklenemedi: {e}")
                            accounts = st.session_state.instantly_accounts_cache

                            if accounts:
                                account_options = {a["email"]: a["id"] for a in accounts}
                                selected_emails = st.multiselect(
                                    "Sending email hesapları",
                                    options=list(account_options.keys()),
                                    default=list(account_options.keys())[:1],
                                    key="instantly_accounts",
                                    help="E-posta hesaplarını seç. Birden fazla seçebilirsin.",
                                )
                                selected_account_ids = [account_options[e] for e in selected_emails]
                                daily_limit = len(selected_account_ids) * 30
                                st.info(
                                    f"**{len(selected_account_ids)} hesap × 30 = {daily_limit} mail/gün** "
                                    f"(her hesap için 30 limit)"
                                )
                            else:
                                st.error("Instantly'de aktif sending hesabı bulunamadı. Dashboard'dan ekle.")
                                selected_account_ids = []
                                daily_limit = 30

                        if not st.session_state.step5_done:
                            st.divider()
                            if st.button(
                                "🚀 Instantly'e Aktar — Kampanya Oluştur & Lead Yükle",
                                type="primary",
                                use_container_width=True,
                                key="instantly_launch_btn",
                            ):
                                if not camp_name.strip():
                                    st.error("Kampanya adı boş olamaz.")
                                elif not selected_account_ids:
                                    st.error("En az bir sending hesabı seçmelisin.")
                                else:
                                    with st.spinner("Kampanya oluşturuluyor..."):
                                        try:
                                            new_id = create_campaign(
                                                name=camp_name.strip(),
                                                email_accounts=selected_account_ids,
                                                sequences=st.session_state.email_sequences,
                                                daily_limit=daily_limit,
                                                timezone=selected_timezone,
                                                api_key=_instantly_key,
                                            )
                                            st.session_state.instantly_campaign_id = new_id
                                        except Exception as e:
                                            st.error(f"Kampanya oluşturma hatası: {e}")
                                            st.stop()

                                    with st.spinner(f"Lead'ler yükleniyor ({len(st.session_state.leads_approved)} adet)..."):
                                        try:
                                            result = upload_leads(
                                                campaign_id=st.session_state.instantly_campaign_id,
                                                leads=st.session_state.leads_approved,
                                                api_key=_instantly_key,
                                            )
                                            st.session_state.instantly_upload_result = result
                                            st.session_state.step5_done = True
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Lead yükleme hatası: {e}")

                    else:
                        if st.session_state.instantly_campaigns_cache is None:
                            with st.spinner("Mevcut kampanyalar yükleniyor..."):
                                try:
                                    st.session_state.instantly_campaigns_cache = list_campaigns(api_key=_instantly_key)
                                except Exception as e:
                                    st.session_state.instantly_campaigns_cache = []
                                    st.warning(f"Kampanyalar yüklenemedi: {e}")
                        campaigns = st.session_state.instantly_campaigns_cache

                        if campaigns:
                            camp_options = {f"{c['name']} ({c['status']})": c["id"] for c in campaigns}
                            selected_camp_label = st.selectbox(
                                "Kampanya seç",
                                options=list(camp_options.keys()),
                                key="instantly_existing_camp",
                            )
                            campaign_id_to_use = camp_options.get(selected_camp_label, "")
                        else:
                            st.error("Instantly'de kampanya bulunamadı.")

                        if not st.session_state.step5_done:
                            st.divider()
                            if st.button(
                                "📤 Lead'leri Mevcut Kampanyaya Yükle",
                                type="primary",
                                use_container_width=True,
                                key="instantly_existing_btn",
                            ):
                                if not campaign_id_to_use:
                                    st.error("Bir kampanya seçmelisin.")
                                else:
                                    with st.spinner(f"Lead'ler yükleniyor ({len(st.session_state.leads_approved)} adet)..."):
                                        try:
                                            result = upload_leads(
                                                campaign_id=campaign_id_to_use,
                                                leads=st.session_state.leads_approved,
                                                api_key=_instantly_key,
                                            )
                                            st.session_state.instantly_campaign_id = campaign_id_to_use
                                            st.session_state.instantly_upload_result = result
                                            st.session_state.step5_done = True
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Lead yükleme hatası: {e}")

                    if st.session_state.step5_done:
                        result = st.session_state.instantly_upload_result
                        uploaded = result.get("uploaded", 0)
                        failed = result.get("failed", 0)

                        st.balloons()
                        st.success(
                            f"**Instantly.ai aktarımı tamamlandı!** · "
                            f"✅ {uploaded} lead yüklendi · "
                            f"{'⚠️ ' + str(failed) + ' duplicate/hata' if failed else '0 hata'}"
                        )

                        camp_id = st.session_state.instantly_campaign_id
                        col_final_a, col_final_b, col_final_c = st.columns(3)
                        col_final_a.metric("Lead Yüklendi", uploaded)
                        col_final_b.metric("Duplicate / Hata", failed)
                        col_final_c.metric("Kampanya ID", camp_id[:8] + "..." if len(camp_id) > 8 else camp_id)

                        st.markdown(f"**Kampanya ID:** `{camp_id}`")

                        st.divider()

                        # ── Kampanya başlatma butonu ──
                        if not st.session_state.campaign_launched:
                            st.markdown("""
                            <div style='background:#090408;border:1px solid #2A0E1C;border-left:3px solid #FF1744;
                                        border-radius:3px;padding:1.25rem 1.5rem;margin-bottom:1rem'>
                              <div style='font-family:"Bebas Neue",sans-serif;font-size:1.2rem;
                                          letter-spacing:.08em;color:#FFE8E8;margin-bottom:.4rem'>
                                🚀 KAMPANYA HAZIR — BAŞLATMAK İSTİYOR MUSUN?
                              </div>
                              <p style='font-family:"Barlow",sans-serif;color:#6B3847;font-size:.85rem;margin:0'>
                                Kampanya şu an <strong style="color:#FF6B35">draft</strong> modunda.
                                Aşağıdaki butona basarsan Instantly'de aktif hale gelir ve mailler gönderilmeye başlar.
                              </p>
                            </div>
                            """, unsafe_allow_html=True)
                            col_launch, col_skip = st.columns([3, 1])
                            with col_launch:
                                if st.button(
                                    "🚀 EVET, KAMPANYAYI BAŞLAT",
                                    type="primary",
                                    use_container_width=True,
                                    key="btn_launch_campaign",
                                ):
                                    with st.spinner("Kampanya başlatılıyor..."):
                                        try:
                                            launch_campaign(camp_id, api_key=_instantly_key)
                                            st.session_state.campaign_launched = True
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Başlatma hatası: {e}")
                            with col_skip:
                                if st.button("Sonra Başlat", use_container_width=True, key="btn_skip_launch"):
                                    st.session_state.campaign_launched = True
                                    st.rerun()
                        else:
                            st.success("✅ Kampanya aktif! Instantly dashboard'undan takip edebilirsin.")

                        st.divider()
                        if st.button("🔄 Yeni Kampanya Başlat (Sıfırla)", key="reset_btn"):
                            for k in list(st.session_state.keys()):
                                del st.session_state[k]
                            st.rerun()
