
import streamlit as st
import sqlite3
import pandas as pd
import os
import json
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime
from uuid import uuid4

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Addis Auto Sales",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB = "addis_auto.db"
IMG_DIR = "car_photos"
VIDEO_DIR = "car_videos"
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

ADMIN_HASH = hashlib.sha256("admin123".encode()).hexdigest()

DEALER_ADDRESS = "904 N La Brea Ave, Inglewood, CA"
DEALER_PHONE = "4246720018"
GOOGLE_MAPS_URL = "https://www.google.com/maps/search/?api=1&query=904%20N%20La%20Brea%20Ave%20Inglewood%20CA"

# =====================================================
# GMAIL EMAIL SETTINGS
# =====================================================
GMAIL_ADDRESS = "autosalesaddis@gmail.com"
GMAIL_APP_PASSWORD = "dskwwqmhvvscpcjr"
ADMIN_EMAIL = "autosalesaddis@gmail.com"

# =====================================================
# DATABASE
# =====================================================
def get_conn():
    return sqlite3.connect(DB)

def query_db(query, params=(), commit=False):
    conn = get_conn()
    if commit:
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return None
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def add_missing_column(table, column, col_type):
    conn = get_conn()
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
    conn.close()

def log_activity(person, action, details=""):
    query_db("""
    INSERT INTO activity_logs
    (salesperson, action, details, created_at)
    VALUES (?,?,?,?)
    """, (person, action, details, str(datetime.now())), commit=True)

def create_notification(title, message):
    query_db("""
    INSERT INTO notifications
    (title, message, created_at, seen)
    VALUES (?,?,?,?)
    """, (title, message, str(datetime.now()), "No"), commit=True)

def notify_admin(event_type, customer_name="", phone="", vehicle="", details=""):
    title = f"ADMIN ALERT: {event_type}"
    message_parts = []
    if customer_name:
        message_parts.append(f"Customer: {customer_name}")
    if phone:
        message_parts.append(f"Phone: {phone}")
    if vehicle:
        message_parts.append(f"Vehicle: {vehicle}")
    if details:
        message_parts.append(f"Details: {details}")

    message = " | ".join(message_parts) if message_parts else event_type
    create_notification(title, message)
    send_sms_placeholder(DEALER_PHONE, f"{title} - {message}")

def send_sms_placeholder(phone, message):
    # Real SMS requires Twilio. This logs the message so you can wire Twilio later.
    query_db("""
    INSERT INTO sms_logs
    (phone, message, status, created_at)
    VALUES (?,?,?,?)
    """, (phone, message, "Logged - Twilio not connected", str(datetime.now())), commit=True)

def send_email(to_email, subject, body):
    if not to_email:
        return

    try:
        msg = EmailMessage()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        create_notification("Email Error", str(e))

# =====================================================
# TABLES
# =====================================================
query_db("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT,
    model TEXT,
    year INTEGER,
    price REAL,
    mileage INTEGER,
    transmission TEXT,
    fuel TEXT,
    body_style TEXT,
    featured TEXT,
    status TEXT,
    image_paths TEXT,
    created_at TEXT
)
""", commit=True)

for col, typ in [
    ("video_paths", "TEXT"),
    ("title_status", "TEXT"),
    ("accident_history", "TEXT"),
    ("owner_history", "TEXT"),
    ("service_history", "TEXT"),
    ("vin", "TEXT"),
    ("exterior_color", "TEXT"),
    ("interior_color", "TEXT"),
    ("description", "TEXT"),
    ("views", "INTEGER DEFAULT 0")
]:
    add_missing_column("inventory", col, typ)

query_db("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    budget TEXT,
    vehicle_type TEXT,
    financing TEXT,
    trade_in TEXT,
    notes TEXT,
    created_at TEXT
)
""", commit=True)

for col, typ in [
    ("status", "TEXT DEFAULT 'New Lead'"),
    ("assigned_to", "TEXT")
]:
    add_missing_column("leads", col, typ)

query_db("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    date TEXT,
    time TEXT,
    reason TEXT,
    created_at TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS finance_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    vehicle TEXT,
    price TEXT,
    monthly_income TEXT,
    employment TEXT,
    credit_range TEXT,
    down_payment TEXT,
    loan_term TEXT,
    appointment_date TEXT,
    appointment_time TEXT,
    notes TEXT,
    created_at TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS buyer_questionnaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    reason_today TEXT,
    desired_year TEXT,
    desired_make TEXT,
    desired_model TEXT,
    vehicle_type TEXT,
    budget TEXT,
    payment_preference TEXT,
    timeline TEXT,
    notes TEXT,
    created_at TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS salespeople (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    role TEXT,
    status TEXT,
    created_at TEXT
)
""", commit=True)

for col, typ in [
    ("photo_path", "TEXT"),
    ("specialties", "TEXT"),
    ("username", "TEXT"),
    ("password", "TEXT")
]:
    add_missing_column("salespeople", col, typ)

query_db("""
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salesperson TEXT,
    action TEXT,
    details TEXT,
    created_at TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS trade_ins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    vehicle_year TEXT,
    vehicle_make TEXT,
    vehicle_model TEXT,
    mileage INTEGER,
    condition TEXT,
    payoff TEXT,
    estimated_value TEXT,
    notes TEXT,
    created_at TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    rating INTEGER,
    review TEXT,
    created_at TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    message TEXT,
    created_at TEXT,
    seen TEXT
)
""", commit=True)

query_db("""
CREATE TABLE IF NOT EXISTS sms_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT,
    message TEXT,
    status TEXT,
    created_at TEXT
)
""", commit=True)

# =====================================================
# SESSION STATE
# =====================================================
defaults = {
    "selected_vehicle": None,
    "selected_vehicle_id": None,
    "force_page": None,
    "confirmation_data": None,
    "auth": False,
    "favorites": [],
    "compare": [],
    "theme": "Red Neon",
    "selected_salesperson": "Admin",
    "user_role": None,
    "logged_in_username": None,
    "loading_seen": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =====================================================
# HELPERS
# =====================================================
def save_uploaded_files(files, folder):
    paths = []
    for file in files or []:
        safe_name = file.name.replace(" ", "_")
        filename = f"{int(datetime.now().timestamp())}_{uuid4().hex[:8]}_{safe_name}"
        path = os.path.join(folder, filename)
        with open(path, "wb") as f:
            f.write(file.getbuffer())
        paths.append(path)
    return paths

def monthly_payment(price, down, apr, years, tax_rate=9.5, fees=595):
    total_price = price + (price * tax_rate / 100) + fees
    loan = max(total_price - down, 0)
    months = years * 12
    monthly_rate = apr / 100 / 12
    if months <= 0:
        return 0
    if monthly_rate == 0:
        return loan / months
    return loan * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)

def car_summary(car):
    clean_badge = []
    if str(car.get("title_status", "")).lower() == "clean":
        clean_badge.append("clean title")
    if str(car.get("accident_history", "")).lower() in ["none", "no accidents"]:
        clean_badge.append("no accident history")
    if str(car.get("owner_history", "")).strip():
        clean_badge.append(str(car.get("owner_history")))
    trust = ", ".join(clean_badge) if clean_badge else "details available from dealer"
    return (
        f"{int(car['year'])} {car['make']} {car['model']} with {int(car['mileage']):,} miles. "
        f"It has {car['transmission']} transmission, {car['fuel']} fuel type, and {car['body_style']} body style. "
        f"Listed at ${float(car['price']):,.0f}. Trust notes: {trust}."
    )

def show_premium_banner(title, subtitle, image_url):
    st.markdown(f"""
    <div class="glass premium-banner" style="
        text-align:center;
        padding:44px 25px;
        background:
        linear-gradient(135deg, rgba(255,0,0,.22), rgba(0,0,0,.92)),
        url('{image_url}');
        background-size:cover;
        background-position:center;
        border:1px solid rgba(255,255,255,.10);
    ">
        <h2 style="
            font-size:2.35rem;
            font-weight:900;
            margin-bottom:10px;
            color:white;
            text-shadow:0 0 18px rgba(255,0,0,.55);
        ">{title}</h2>
        <p style="
            color:#e6e6e6;
            font-size:1.05rem;
            max-width:820px;
            margin:auto;
            line-height:1.6;
        ">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# =====================================================
# CSS
# =====================================================
theme_class = "theme-light" if st.session_state["theme"] == "White Luxury" else "theme-black" if st.session_state["theme"] == "Black Luxury" else "theme-red"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.stApp {{
    background:
        radial-gradient(circle at 15% 20%, rgba(255,0,0,.35), transparent 28%),
        radial-gradient(circle at 80% 15%, rgba(255,255,255,.13), transparent 25%),
        radial-gradient(circle at 70% 80%, rgba(255,0,0,.18), transparent 35%),
        linear-gradient(135deg, #020202, #0a0000 45%, #111 100%);
    background-size: 160% 160%;
    animation: animatedBackground 12s ease-in-out infinite;
    color: white;
    overflow-x: hidden;
}}

@keyframes animatedBackground {{
    0%, 100% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
}}

.stApp::before {{
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
        linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,.65), transparent);
    z-index: 0;
}}

.block-container {{
    padding-top: 1rem;
    padding-left: 3rem;
    padding-right: 3rem;
    animation: pageFade .8s ease;
    position: relative;
    z-index: 1;
}}

@keyframes pageFade {{
    from {{ opacity: 0; transform: translateY(22px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

[data-testid="stSidebar"] {{
    display: none;
}}

.top-nav {{
    position: sticky;
    top: 0;
    z-index: 999;
    margin-bottom: 20px;
    background: rgba(5,5,5,.78);
    backdrop-filter: blur(22px);
    border: 1px solid rgba(255,255,255,.11);
    border-radius: 26px;
    padding: 16px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    animation: navDrop .75s ease;
    box-shadow: 0 22px 70px rgba(0,0,0,.55), 0 0 35px rgba(255,0,0,.12);
}}

@keyframes navDrop {{
    from {{ opacity: 0; transform: translateY(-26px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.logo {{
    font-size: 1.7rem;
    font-weight: 900;
    letter-spacing: 2px;
    white-space: nowrap;
}}

.logo span {{
    color: #ff2424;
    text-shadow: 0 0 20px rgba(255,0,0,.85);
}}

.nav-radio {{
    flex: 1;
    display: flex;
    justify-content: flex-end;
}}

div[role="radiogroup"] {{
    display: flex !important;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
}}

div[role="radiogroup"] label {{
    background: rgba(255,255,255,.07) !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 999px !important;
    padding: 10px 17px !important;
    transition: all .25s ease !important;
    color: white !important;
    font-weight: 800 !important;
    margin: 0 !important;
}}

div[role="radiogroup"] label:hover {{
    transform: translateY(-3px);
    border-color: rgba(255,0,0,.70) !important;
    box-shadow: 0 0 24px rgba(255,0,0,.28);
    background: rgba(255,0,0,.16) !important;
}}

div[role="radiogroup"] label:has(input:checked) {{
    background: linear-gradient(90deg, #ff2020, #8d0000) !important;
    border-color: rgba(255,0,0,.85) !important;
    box-shadow: 0 0 26px rgba(255,0,0,.45);
}}

.quick-contact, .floating-actions {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 12px 0 25px;
}}

.quick-contact a, .floating-actions a {{
    text-decoration: none;
    color: white;
    background: rgba(255,255,255,.08);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 999px;
    padding: 10px 16px;
    font-weight: 900;
    transition: .25s ease;
}}

.quick-contact a:hover, .floating-actions a:hover {{
    background: rgba(255,0,0,.22);
    border-color: rgba(255,0,0,.65);
    transform: translateY(-3px);
}}

.floating-actions {{
    position: fixed;
    right: 18px;
    bottom: 18px;
    z-index: 9999;
    flex-direction: column;
}}

.hero {{
    position: relative;
    overflow: hidden;
    min-height: 510px;
    border-radius: 40px;
    padding: 82px 58px;
    background:
        linear-gradient(90deg, rgba(0,0,0,.92), rgba(0,0,0,.28)),
        url("https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1800");
    background-size: cover;
    background-position: center;
    border: 1px solid rgba(255,255,255,.14);
    box-shadow: 0 38px 120px rgba(0,0,0,.70);
    margin-bottom: 36px;
    animation: heroZoom .85s ease;
}}

.hero::before {{
    content: "";
    position: absolute;
    width: 470px;
    height: 470px;
    right: -130px;
    top: -140px;
    background: rgba(255,0,0,.34);
    filter: blur(95px);
    border-radius: 50%;
    animation: glowFloat 6s ease-in-out infinite;
}}

@keyframes heroZoom {{
    from {{ opacity: 0; transform: scale(.97); }}
    to {{ opacity: 1; transform: scale(1); }}
}}

@keyframes glowFloat {{
    0%, 100% {{ transform: translate(0,0) scale(1); }}
    50% {{ transform: translate(-35px,40px) scale(1.16); }}
}}

.hero-content {{
    position: relative;
    z-index: 3;
    max-width: 860px;
}}

.hero h1 {{
    font-size: 5.2rem;
    line-height: .94;
    font-weight: 900;
    margin-bottom: 18px;
}}

.hero p {{
    color: #e7e7e7;
    font-size: 1.2rem;
    max-width: 690px;
}}

.section-title {{
    font-size: 2.15rem;
    font-weight: 900;
    margin: 36px 0 20px;
    text-shadow: 0 0 18px rgba(255,0,0,.28);
}}

.glass, .grid-card, .car-card {{
    background: rgba(14,14,14,.88);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 30px;
    backdrop-filter: blur(20px);
    box-shadow: 0 22px 65px rgba(0,0,0,.40);
    transition: all .30s ease;
    animation: cardAppear .75s ease;
}}

@keyframes cardAppear {{
    from {{ opacity: 0; transform: translateY(28px) scale(.98); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}

.glass {{
    padding: 28px;
    margin-bottom: 28px;
}}

.grid-card {{
    padding: 26px;
    margin-bottom: 24px;
}}

.grid-card:hover, .glass:hover, .car-card:hover {{
    transform: translateY(-8px);
    border-color: rgba(255,0,0,.62);
    box-shadow: 0 26px 80px rgba(255,0,0,.18), 0 0 30px rgba(255,0,0,.13);
}}

.icon-big {{
    font-size: 2.45rem;
    margin-bottom: 10px;
}}

.card-title {{
    font-size: 1.24rem;
    font-weight: 900;
    margin-bottom: 8px;
}}

.card-text {{
    color: #c9c9c9;
    font-size: .95rem;
}}

.trust-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 30px;
}}

.trust-box {{
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.11);
    border-radius: 24px;
    padding: 22px;
    text-align: center;
}}

.trust-number {{
    font-size: 2rem;
    font-weight: 900;
    color: #ff2b2b;
}}

.car-card {{
    padding: 0;
    overflow: hidden;
    margin-bottom: 32px;
}}

.car-card img {{
    transition: transform .45s ease, filter .45s ease;
}}

.car-card:hover img {{
    transform: scale(1.06);
    filter: brightness(1.08) contrast(1.05);
}}

.car-body {{
    padding: 23px;
}}

.car-title {{
    font-size: 1.4rem;
    font-weight: 900;
}}

.price {{
    color: #ff2b2b;
    font-size: 2.05rem;
    font-weight: 900;
    margin: 8px 0 12px;
    text-shadow: 0 0 18px rgba(255,0,0,.45);
}}

.badge {{
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(25,25,25,.95);
    border: 1px solid #303030;
    margin: 4px 3px;
    font-size: .86rem;
}}

.badge-red {{
    background: #ff2020;
    color: black;
    font-weight: 900;
}}

.badge-green {{
    background: #00ff88;
    color: black;
    font-weight: 900;
}}

.badge-gold {{
    background: linear-gradient(90deg, #ffd700, #ff9f00);
    color: black;
    font-weight: 900;
}}

.confirm-check {{
    font-size: 5rem;
    color: #00ff88;
    text-shadow: 0 0 35px rgba(0,255,136,.7);
    text-align: center;
    margin-bottom: 10px;
}}

.confirm-title {{
    font-size: 2.8rem;
    font-weight: 900;
    text-align: center;
    color: #00ff88;
}}

.confirm-subtitle {{
    text-align: center;
    color: #ddd;
    font-size: 1.15rem;
    margin-bottom: 25px;
}}

.stButton > button {{
    width: 100%;
    height: 3.2rem;
    border-radius: 16px;
    border: none;
    background: linear-gradient(90deg, #ff2020, #920000);
    color: white;
    font-weight: 900;
    box-shadow: 0 12px 32px rgba(255,0,0,.24);
    transition: all .25s ease;
}}

.stButton > button:hover {{
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 0 30px rgba(255,0,0,.65);
}}

input, textarea {{
    border-radius: 14px !important;
}}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {{
    background: rgba(17,17,17,.98) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,.12) !important;
}}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background: rgba(255,255,255,.96) !important;
    color: #111111 !important;
    border: 1px solid rgba(255,255,255,.25) !important;
    border-radius: 14px !important;
}

.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
.stDateInput input:focus {
    background: #ffffff !important;
    color: #000000 !important;
    border: 2px solid #ff2020 !important;
    box-shadow: 0 0 18px rgba(255,32,32,.45) !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #666666 !important;
    opacity: 1 !important;
}

/* Selectbox text visibility */
.stSelectbox div[data-baseweb="select"] span,
.stSelectbox div[data-baseweb="select"] input {
    color: #111111 !important;
}

/* Dropdown menu readability */
div[data-baseweb="popover"] {
    color: #111111 !important;
}

div[data-baseweb="popover"] * {
    color: #111111 !important;
}

/* Date picker readability */
div[data-baseweb="calendar"] * {
    color: #111111 !important;
}

[data-testid="metric-container"] {{
    background: rgba(16,16,16,.92);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 24px;
    padding: 22px;
}}

.loading-screen {{
    position: fixed;
    inset: 0;
    background: #050505;
    z-index: 100000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: hideLoader 2s forwards;
}}

.loader-logo {{
    font-size: 2rem;
    font-weight: 900;
    color: white;
    text-shadow: 0 0 28px red;
    animation: pulse 1s infinite;
}}

@keyframes pulse {{
    0%, 100% {{ transform: scale(1); opacity: .75; }}
    50% {{ transform: scale(1.08); opacity: 1; }}
}}

@keyframes hideLoader {{
    0%, 80% {{ opacity: 1; visibility: visible; }}
    100% {{ opacity: 0; visibility: hidden; }}
}}

@media(max-width: 1000px) {{
    .top-nav {{
        display: block;
        text-align: center;
    }}

    .nav-radio {{
        justify-content: center;
        margin-top: 14px;
    }}

    div[role="radiogroup"] {{
        justify-content: center;
    }}

    .hero h1 {{
        font-size: 4rem;
    }}

    .trust-row {{
        grid-template-columns: repeat(2, 1fr);
    }}
}}


@media(max-width: 768px) {{
    .block-container {{
        padding-left: 1rem;
        padding-right: 1rem;
    }}

    .top-nav {{
        border-radius: 20px;
        padding: 14px;
    }}

    .logo {{
        font-size: 1.25rem;
    }}

    div[role="radiogroup"] label {{
        padding: 8px 12px !important;
        font-size: .80rem !important;
    }}

    .hero {{
        padding: 46px 24px;
        min-height: 400px;
        border-radius: 28px;
    }}

    .hero h1 {{
        font-size: 2.75rem;
    }}

    .hero p {{
        font-size: 1rem;
    }}

    .section-title {{
        font-size: 1.65rem;
    }}

    .trust-row {{
        grid-template-columns: 1fr;
    }}

    .glass {{
        padding: 20px;
        border-radius: 23px;
    }}

    .floating-actions {{
        right: 8px;
        bottom: 8px;
    }}
}}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
.premium-banner {
    min-height: 150px;
    animation: bannerFloat .9s ease;
}

@keyframes bannerFloat {
    from {
        opacity: 0;
        transform: translateY(25px) scale(.98);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

.premium-banner h2 {
    animation: bannerText .9s ease;
}

.premium-banner p {
    animation: bannerText 1.1s ease;
}

@keyframes bannerText {
    from {
        opacity: 0;
        transform: translateY(18px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media(max-width: 768px) {
    .premium-banner {
        padding: 30px 18px !important;
        border-radius: 22px !important;
    }

    .premium-banner h2 {
        font-size: 1.65rem !important;
    }

    .premium-banner p {
        font-size: .95rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

if not st.session_state["loading_seen"]:
    st.markdown('<div class="loading-screen"><div class="loader-logo">ADDIS AUTO SALES</div></div>', unsafe_allow_html=True)
    st.session_state["loading_seen"] = True

# =====================================================
# TOP NAV
# =====================================================
st.markdown(
    '<div class="top-nav"><div class="logo">ADDIS <span>AUTO SALES</span></div><div class="nav-radio">',
    unsafe_allow_html=True
)

page_label = st.radio(
    "Navigation",
    ["🏠 Home", "🚘 Showroom", "💳 Finance", "📅 Appointment", "🔐 Dealer Portal"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown('</div></div>', unsafe_allow_html=True)

page = (
    page_label
    .replace("🏠 ", "")
    .replace("🚘 ", "")
    .replace("💳 ", "")
    .replace("📅 ", "")
    .replace("🔐 ", "")
)

if st.session_state.get("force_page"):
    page = st.session_state["force_page"]
    st.session_state["force_page"] = None

# Quick contact + floating actions
st.markdown(f"""
<div class="quick-contact">
    <a href="{GOOGLE_MAPS_URL}" target="_blank">📍 Location</a>
    <a href="tel:{DEALER_PHONE}">📞 Call Addis Auto Sales</a>
</div>
<div class="floating-actions">
    <a href="tel:{DEALER_PHONE}">📞 Call</a>
    <a href="{GOOGLE_MAPS_URL}" target="_blank">📍 Location</a>
</div>
""", unsafe_allow_html=True)

# =====================================================
# HOME
# =====================================================
if page == "Home":

    st.markdown("""
    <div class="hero">
        <div class="hero-content">
            <h1>Find Your Next Car Without The Stress.</h1>
            <p>
            Premium vehicles, fast financing help, trade-in support,
            appointment booking, and a modern buying experience built for Addis Auto Sales.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    if c1.button("🚘 Browse Inventory"):
        st.session_state["force_page"] = "Showroom"
        st.rerun()
    if c2.button("💳 Get Pre-Approved"):
        st.session_state["force_page"] = "Finance"
        st.rerun()
    if c3.button("📅 Book Appointment"):
        st.session_state["force_page"] = "Appointment"
        st.rerun()

    st.markdown("""
    <div class="trust-row">
        <div class="trust-box"><div class="trust-number">100%</div><div>Clean Buying Experience</div></div>
        <div class="trust-box"><div class="trust-number">24hr</div><div>Fast Lead Response</div></div>
        <div class="trust-box"><div class="trust-number">0</div><div>Pressure Sales</div></div>
        <div class="trust-box"><div class="trust-number">CA</div><div>Inglewood Based</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Buyer Questionnaire</div>', unsafe_allow_html=True)

    show_premium_banner(
        "Find Your Perfect Vehicle",
        "Tell Addis Auto Sales what kind of vehicle you want, your budget, and what brings you in today. Our team will use this to help match you with the right car.",
        "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?q=80&w=1800"
    )

    with st.form("buyer_questionnaire"):
        c1, c2, c3 = st.columns(3)
        q_name = c1.text_input("Full Name", placeholder="Enter your full name")
        q_phone = c2.text_input("Phone Number", placeholder="(555) 123-4567")
        q_email = c3.text_input("Email", placeholder="example@email.com")
        reason_today = c1.selectbox("What brings you in today?", ["Just Looking", "Need a car soon", "Ready to buy today", "Want financing", "Trade-in question", "Test drive"])
        desired_year = c2.selectbox("Preferred Year", ["Any", "2010+", "2015+", "2020+", "2022+", "2024+"])
        vehicle_type = c3.selectbox("Vehicle Type", ["Any", "Sedan", "SUV", "Truck", "Luxury", "Sports Car", "Hybrid", "Electric", "Family Car"])
        desired_make = c1.text_input("Preferred Make", placeholder="Toyota, Mercedes, Honda...")
        desired_model = c2.text_input("Preferred Model", placeholder="Camry, E350, Accord...")
        budget = c3.selectbox("Budget", ["Under $10K", "$10K - $20K", "$20K - $35K", "$35K - $50K", "$50K+"])
        payment_preference = c1.selectbox("Payment Preference", ["Not Sure", "Finance", "One-Time Payment"])
        timeline = c2.selectbox("Buying Timeline", ["Today", "This Week", "This Month", "Just Looking"])
        q_notes = st.text_area("Anything else we should know?")

        submit_questionnaire = st.form_submit_button("Submit Questionnaire")

        if submit_questionnaire:
            if not q_name or not q_phone:
                st.error("Please enter your name and phone number.")
            else:
                query_db("""
                INSERT INTO buyer_questionnaires
                (name, phone, email, reason_today, desired_year, desired_make, desired_model, vehicle_type, budget, payment_preference, timeline, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (q_name, q_phone, q_email, reason_today, desired_year, desired_make, desired_model, vehicle_type, budget, payment_preference, timeline, q_notes, str(datetime.now())), commit=True)

                query_db("""
                INSERT INTO leads
                (name, phone, email, budget, vehicle_type, financing, trade_in, notes, created_at, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (q_name, q_phone, q_email, budget, vehicle_type, payment_preference, "Not Provided", f"Questionnaire: {reason_today}. Year: {desired_year}. Make: {desired_make}. Model: {desired_model}. Timeline: {timeline}. Notes: {q_notes}", str(datetime.now()), "New Lead"), commit=True)

                send_sms_placeholder(q_phone, "Thank you for contacting Addis Auto Sales. We received your request.")
                create_notification("New Questionnaire", f"{q_name} submitted a buyer questionnaire.")

                send_email(
                    q_email,
                    "Addis Auto Sales Inquiry Received",
                    f"""
Hi {q_name},

We received your vehicle inquiry questionnaire.

Vehicle Interest:
{desired_year} {desired_make} {desired_model}

Budget:
{budget}

Payment Preference:
{payment_preference}

A member of Addis Auto Sales will contact you soon.

904 N La Brea Ave, Inglewood, CA
424-672-0018
"""
                )

                send_email(
                    ADMIN_EMAIL,
                    "New Buyer Questionnaire",
                    f"""
New customer inquiry submitted.

Customer: {q_name}
Phone: {q_phone}
Email: {q_email}

Vehicle Interest:
{desired_year} {desired_make} {desired_model}

Budget:
{budget}

Payment Preference:
{payment_preference}
"""
                )

                notify_admin(
                    "New Buyer Questionnaire",
                    q_name,
                    q_phone,
                    f"{desired_year} {desired_make} {desired_model}",
                    f"Budget: {budget} | Preference: {payment_preference} | Timeline: {timeline}"
                )

                st.session_state["confirmation_data"] = {
                    "title": "Questionnaire Submitted",
                    "subtitle": "We received your vehicle preferences.",
                    "message": "Would you like to schedule an appointment next?",
                    "name": q_name,
                    "vehicle": f"{desired_year} {desired_make} {desired_model} / {vehicle_type}",
                    "date": str(datetime.now().date()),
                    "time": str(datetime.now().strftime("%I:%M %p")),
                    "ask_appointment": True
                }
                st.session_state["force_page"] = "Confirmation"
                st.rerun()


# =====================================================
# SHOWROOM
# =====================================================
elif page == "Showroom":

    st.markdown('<div class="section-title">Showroom Inventory</div>', unsafe_allow_html=True)

    cars = query_db("SELECT * FROM inventory ORDER BY featured DESC, id DESC")

    with st.expander("Advanced Filters", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        search = f1.text_input("Search make or model")
        max_price = f2.slider("Max Price", 1000, 200000, 100000)
        max_mileage = f3.slider("Max Mileage", 0, 300000, 300000)
        year_min = f4.slider("Minimum Year", 1990, 2035, 2000)
        body_filter = f1.selectbox("Body Style", ["All", "Sedan", "SUV", "Truck", "Coupe", "Luxury", "Van", "Sports Car"])
        fuel_filter = f2.selectbox("Fuel", ["All", "Gasoline", "Hybrid", "Electric", "Diesel"])
        status_filter = f3.selectbox("Status", ["All", "Available", "Sold"])
        sort_by = f4.selectbox("Sort By", ["Newest", "Price Low To High", "Price High To Low", "Mileage Low To High"])

    if not cars.empty:
        if search:
            cars = cars[cars["make"].str.contains(search, case=False, na=False) | cars["model"].str.contains(search, case=False, na=False)]
        cars = cars[(cars["price"] <= max_price) & (cars["mileage"] <= max_mileage) & (cars["year"] >= year_min)]
        if body_filter != "All":
            cars = cars[cars["body_style"] == body_filter]
        if fuel_filter != "All":
            cars = cars[cars["fuel"] == fuel_filter]
        if status_filter != "All":
            cars = cars[cars["status"] == status_filter]
        if sort_by == "Price Low To High":
            cars = cars.sort_values("price")
        elif sort_by == "Price High To Low":
            cars = cars.sort_values("price", ascending=False)
        elif sort_by == "Mileage Low To High":
            cars = cars.sort_values("mileage")

    if cars.empty:
        st.info("No vehicles match your search.")
    else:
        cols = st.columns(3)

        for i, (_, car) in enumerate(cars.iterrows()):
            with cols[i % 3]:
                st.markdown('<div class="car-card">', unsafe_allow_html=True)

                image_list = []
                if car["image_paths"]:
                    try:
                        image_list = [img for img in json.loads(car["image_paths"]) if os.path.exists(img)]
                        if image_list:
                            st.image(image_list[0], use_container_width=True)
                            with st.expander("View Gallery"):
                                for img in image_list:
                                    st.image(img, use_container_width=True)
                    except Exception:
                        pass

                st.markdown('<div class="car-body">', unsafe_allow_html=True)

                if car["featured"] == "Yes":
                    st.markdown('<span class="badge badge-gold">FEATURED</span>', unsafe_allow_html=True)
                if car["status"] == "Sold":
                    st.markdown('<span class="badge badge-red">SOLD</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge badge-green">AVAILABLE</span>', unsafe_allow_html=True)

                selected_vehicle_name = f"{int(car['year'])} {car['make']} {car['model']}"
                st.markdown(f'<div class="car-title">{selected_vehicle_name}</div><div class="price">${float(car["price"]):,.0f}</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <span class="badge">🚗 {int(car['mileage']):,} mi</span>
                <span class="badge">⚙️ {car['transmission']}</span>
                <span class="badge">⛽ {car['fuel']}</span>
                <span class="badge">🏁 {car['body_style']}</span>
                """, unsafe_allow_html=True)

                with st.expander("Sales Summary"):
                    st.write(car_summary(car))
                    st.markdown(f"""
                    <span class="badge">🛡️ Title: {car.get('title_status') or 'Ask Dealer'}</span>
                    <span class="badge">📋 Accidents: {car.get('accident_history') or 'Ask Dealer'}</span>
                    <span class="badge">👤 Owners: {car.get('owner_history') or 'Ask Dealer'}</span>
                    """, unsafe_allow_html=True)

                with st.expander("Premium Payment Calculator"):
                    d1, d2 = st.columns(2)
                    down = d1.number_input("Down Payment", 0, int(car["price"]), 3000, key=f"down_{car['id']}")
                    years = d2.slider("Loan Years", 1, 8, 5, key=f"years_{car['id']}")
                    apr = d1.slider("APR %", 1.0, 25.0, 7.5, key=f"apr_{car['id']}")
                    tax = d2.slider("Tax %", 0.0, 12.0, 9.5, key=f"tax_{car['id']}")
                    fees = d1.number_input("Dealer/DMV Fees", 0, 5000, 595, key=f"fees_{car['id']}")
                    st.metric("Estimated Monthly", f"${monthly_payment(float(car['price']), down, apr, years, tax, fees):,.2f}")

                with st.expander("Videos"):
                    try:
                        videos = [v for v in json.loads(car.get("video_paths") or "[]") if os.path.exists(v)]
                        if videos:
                            for vid in videos:
                                st.video(vid)
                        else:
                            st.info("No videos uploaded.")
                    except Exception:
                        st.info("No videos uploaded.")

                fav_col, comp_col = st.columns(2)
                if fav_col.button("❤️ Save", key=f"fav_{car['id']}"):
                    if int(car["id"]) not in st.session_state["favorites"]:
                        st.session_state["favorites"].append(int(car["id"]))
                    st.success("Saved.")
                if comp_col.button("⇄ Compare", key=f"compare_{car['id']}"):
                    if int(car["id"]) not in st.session_state["compare"] and len(st.session_state["compare"]) < 3:
                        st.session_state["compare"].append(int(car["id"]))
                    st.success("Added to compare.")

                if car["status"] == "Available":
                    selected_vehicle = {"id": int(car["id"]), "name": selected_vehicle_name, "price": float(car["price"])}
                    c1, c2 = st.columns(2)
                    if c1.button("Apply For Financing", key=f"go_finance_{car['id']}"):
                        st.session_state["selected_vehicle"] = selected_vehicle
                        query_db("UPDATE inventory SET views = COALESCE(views,0)+1 WHERE id=?", (int(car["id"]),), commit=True)
                        st.session_state["force_page"] = "Finance"
                        st.rerun()
                    if c2.button("One-Time Payment", key=f"go_one_time_{car['id']}"):
                        st.session_state["selected_vehicle"] = selected_vehicle
                        query_db("UPDATE inventory SET views = COALESCE(views,0)+1 WHERE id=?", (int(car["id"]),), commit=True)
                        st.session_state["force_page"] = "Appointment"
                        st.rerun()
                else:
                    st.markdown('<div class="badge badge-red" style="width:100%;text-align:center;margin-top:12px;">SOLD</div>', unsafe_allow_html=True)

                st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Saved Favorites</div>', unsafe_allow_html=True)
    if st.session_state["favorites"]:
        favs = query_db(f"SELECT year, make, model, price FROM inventory WHERE id IN ({','.join(['?']*len(st.session_state['favorites']))})", tuple(st.session_state["favorites"]))
        st.dataframe(favs, use_container_width=True)
    else:
        st.info("No saved cars yet.")

    st.markdown('<div class="section-title">Compare Vehicles</div>', unsafe_allow_html=True)
    if st.session_state["compare"]:
        comp = query_db(f"SELECT year, make, model, price, mileage, transmission, fuel, body_style, title_status, accident_history FROM inventory WHERE id IN ({','.join(['?']*len(st.session_state['compare']))})", tuple(st.session_state["compare"]))
        st.dataframe(comp, use_container_width=True)
        if st.button("Clear Compare"):
            st.session_state["compare"] = []
            st.rerun()
    else:
        st.info("Add up to 3 cars to compare.")

# =====================================================
# FINANCE
# =====================================================
elif page == "Finance":
    st.markdown('<div class="section-title">Finance Application</div>', unsafe_allow_html=True)
    selected = st.session_state.get("selected_vehicle")

    if selected:
        st.markdown(f'<div class="glass"><h2>Selected Vehicle</h2><h3>{selected["name"]}</h3><h3 style="color:#ff2b2b;">${selected["price"]:,.0f}</h3></div>', unsafe_allow_html=True)
    else:
        st.info("No vehicle selected. You can still submit a general finance application.")

    c_back = st.columns(1)[0]
    if c_back.button("← Back To Showroom"):
        st.session_state["force_page"] = "Showroom"
        st.rerun()

    with st.form("finance_page_form"):
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full Name", placeholder="Enter your full name")
        phone = c2.text_input("Phone Number", placeholder="(555) 123-4567")
        email = c1.text_input("Email", placeholder="example@email.com")
        monthly_income = c2.number_input("Monthly Income", min_value=0)
        employment_status = c1.selectbox("Employment Status", ["Full-Time", "Part-Time", "Self-Employed", "Student", "Unemployed", "Other"])
        credit_range = c2.selectbox("Credit Score Range", ["Excellent 720+", "Good 680-719", "Fair 620-679", "Poor Under 620", "Not Sure"])
        down_payment = c1.number_input("Down Payment", min_value=0, value=3000)
        loan_term = c2.selectbox("Preferred Loan Term", ["36 Months", "48 Months", "60 Months", "72 Months", "84 Months"])
        appointment_date = c1.date_input("Preferred Appointment Date")
        appointment_time = c2.selectbox("Preferred Appointment Time", ["9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"])
        finance_notes = st.text_area("Additional Notes", placeholder="Example: I want payments under $500/month.")
        submit_finance = st.form_submit_button("Submit Finance Application")

        if submit_finance:
            if not full_name or not phone:
                st.error("Please enter your name and phone number.")
            else:
                vehicle_name = selected["name"] if selected else "General Finance Application"
                vehicle_price = f"${selected['price']:,.0f}" if selected else "Not Selected"

                query_db("""
                INSERT INTO finance_applications
                (name, phone, email, vehicle, price, monthly_income, employment, credit_range, down_payment, loan_term, appointment_date, appointment_time, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (full_name, phone, email, vehicle_name, vehicle_price, f"${monthly_income:,.0f}", employment_status, credit_range, f"${down_payment:,.0f}", loan_term, str(appointment_date), appointment_time, finance_notes, str(datetime.now())), commit=True)

                query_db("""
                INSERT INTO leads
                (name, phone, email, budget, vehicle_type, financing, trade_in, notes, created_at, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (full_name, phone, email, vehicle_price, vehicle_name, "Finance", "Not Provided", f"Finance application submitted. Credit: {credit_range}. Down: ${down_payment:,.0f}. Term: {loan_term}.", str(datetime.now()), "Financing"), commit=True)

                send_sms_placeholder(phone, f"Addis Auto Sales received your finance application for {vehicle_name}.")
                create_notification("New Finance Application", f"{full_name} applied for {vehicle_name}.")

                send_email(
                    email,
                    "Addis Auto Sales Finance Application Received",
                    f"""
Hi {full_name},

Your finance application was received successfully.

Vehicle:
{vehicle_name}

Preferred Appointment:
{appointment_date} at {appointment_time}

Addis Auto Sales will contact you shortly.

904 N La Brea Ave, Inglewood, CA
424-672-0018
"""
                )

                send_email(
                    ADMIN_EMAIL,
                    "New Finance Application Alert",
                    f"""
New finance application submitted.

Customer: {full_name}
Phone: {phone}
Email: {email}
Vehicle: {vehicle_name}
Income: ${monthly_income:,.0f}
Credit: {credit_range}
Down Payment: ${down_payment:,.0f}
Loan Term: {loan_term}
"""
                )

                notify_admin(
                    "New Finance Application",
                    full_name,
                    phone,
                    vehicle_name,
                    f"Income: ${monthly_income:,.0f} | Credit: {credit_range} | Down: ${down_payment:,.0f} | Term: {loan_term}"
                )

                st.session_state["confirmation_data"] = {
                    "title": "Finance Application Submitted",
                    "subtitle": "Your application was received successfully.",
                    "message": "Addis Auto Sales will review your finance application and contact you soon.",
                    "name": full_name,
                    "vehicle": vehicle_name,
                    "date": str(appointment_date),
                    "time": appointment_time,
                    "ask_appointment": False
                }
                st.session_state["force_page"] = "Confirmation"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# APPOINTMENT / ONE-TIME PAYMENT
# =====================================================
elif page == "Appointment":
    st.markdown('<div class="section-title">Schedule Appointment</div>', unsafe_allow_html=True)
    selected = st.session_state.get("selected_vehicle")

    if selected:
        st.markdown(f'<div class="glass"><h2>Selected Vehicle</h2><h3>{selected["name"]}</h3><h3 style="color:#ff2b2b;">${selected["price"]:,.0f}</h3></div>', unsafe_allow_html=True)

    show_premium_banner(
        "Schedule Your Visit",
        "Choose a time that works for you. Addis Auto Sales will prepare the vehicle and confirm your appointment before you arrive.",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1800"
    )

    with st.form("appointment_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full Name", placeholder="Enter your full name")
        phone = c2.text_input("Phone Number", placeholder="(555) 123-4567")
        email = c1.text_input("Email", placeholder="example@email.com")
        date = c2.date_input("Appointment Date")
        appointment_submitted_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        time = "Submitted in real time"
        appointment_end_time = appointment_submitted_at

        st.info(f"Appointment request time will be recorded automatically: {appointment_submitted_at}")
        reason = st.text_area("Reason for visit", value="Vehicle Appointment")
        submit = st.form_submit_button("Book Appointment")

        if submit:
            vehicle_name = selected["name"] if selected else "General Appointment"
            vehicle_price = f"${selected['price']:,.0f}" if selected else "Not Selected"
            if not name or not phone:
                st.error("Please enter your name and phone number.")
            else:
                query_db("INSERT INTO appointments (name, phone, email, date, time, reason, created_at) VALUES (?,?,?,?,?,?,?)", (name, phone, email, str(date), time, f"{reason} | Vehicle: {vehicle_name}", str(datetime.now())), commit=True)
                query_db("""
                INSERT INTO leads
                (name, phone, email, budget, vehicle_type, financing, trade_in, notes, created_at, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (name, phone, email, vehicle_price, vehicle_name, "One-Time Payment", "Not Provided", f"Appointment booked. Reason: {reason}", str(datetime.now()), "Appointment Set"), commit=True)

                send_sms_placeholder(phone, f"Addis Auto Sales received your appointment request for {vehicle_name}.")
                create_notification("New Appointment", f"{name} booked appointment for {vehicle_name}.")

                send_email(
                    email,
                    "Your Addis Auto Sales Appointment Confirmation",
                    f"""
Dear {name},

Welcome to Addis Auto Sales — we truly appreciate the opportunity to assist you.

Thank you for scheduling your appointment with our dealership. Your request has been successfully received, and our team is already preparing for your visit to make your experience smooth, professional, and personalized.

{name}, we understand that purchasing a vehicle is an important decision, and our goal is to help you feel comfortable, informed, and confident throughout the process. Whether you are visiting for a test drive, financing assistance, trade-in support, or to finalize your purchase, we are excited to help you find the right vehicle that fits your needs and budget.

Appointment Details
-------------------
Vehicle: {vehicle_name}
Date: {date}
Submitted: {appointment_end_time}
Reason for Visit: {reason}

Dealership Location
-------------------
Addis Auto Sales
904 N La Brea Ave
Inglewood, CA

Phone: 424-672-0018

About Addis Auto Sales
----------------------
Addis Auto Sales is a local Inglewood dealership focused on helping customers find quality vehicles with a simple, respectful, and professional buying experience. Whether you are visiting for a test drive, financing questions, trade-in support, or to complete your purchase, our team is here to help guide you through the process.

Before You Arrive
-----------------
Please bring a valid driver's license.
If you are interested in financing, please bring proof of income and any documents that may help with your application.
If you are trading in a vehicle, please bring the title or payoff information if available.

A member of our team may contact you before your appointment to confirm availability and answer any questions you may have.

If you need to reschedule your appointment or speak with our staff before arriving, please contact us anytime at 424-672-0018.

Thank you again, {name}, for choosing Addis Auto Sales.

We look forward to welcoming you to our dealership and helping you drive away in a vehicle you’ll love.

Warm regards,

The Addis Auto Sales Team

Addis Auto Sales
904 N La Brea Ave, Inglewood, CA
424-672-0018
"""
                )

                send_email(
                    ADMIN_EMAIL,
                    "New Customer Appointment - Addis Auto Sales",
                    f"""
A new customer appointment has been submitted through the Addis Auto Sales website.

Customer Information
--------------------
Name: {name}
Phone: {phone}
Email: {email}

Appointment Details
-------------------
Vehicle: {vehicle_name}
Date: {date}
Submitted: {appointment_end_time}
Reason: {reason}

Recommended Follow-Up
---------------------
Please contact the customer to confirm availability, prepare the vehicle, and answer any questions before arrival.

Dealership:
Addis Auto Sales
904 N La Brea Ave, Inglewood, CA
424-672-0018
"""
                )

                notify_admin(
                    "New Appointment Inquiry",
                    name,
                    phone,
                    vehicle_name,
                    f"Date: {date} | Submitted: {appointment_end_time} | Reason: {reason}"
                )

                st.session_state["confirmation_data"] = {
                    "title": "Appointment Request Received",
                    "subtitle": "Thank you for choosing Addis Auto Sales.",
                    "message": "Your appointment request has been received. Our team will prepare your vehicle information and may contact you to confirm your visit. Your appointment request was recorded in real time, and our team will contact you to confirm the best available appointment slot. Location: 904 N La Brea Ave, Inglewood, CA. Phone: 424-672-0018.",
                    "name": name,
                    "vehicle": vehicle_name,
                    "date": str(date),
                    "time": appointment_end_time,
                    "ask_appointment": False
                }
                st.session_state["force_page"] = "Confirmation"
                st.rerun()


    st.markdown("""
    <div style="
        margin:60px 0 30px 0;
        border-top:1px solid rgba(255,255,255,.12);
        padding-top:35px;
    ">
        <h2 style="
            color:white;
            font-size:2rem;
            font-weight:900;
            text-align:center;
        ">
            Vehicle Trade-In Center
        </h2>

        <p style="
            text-align:center;
            color:#e5e5e5;
            max-width:820px;
            margin:auto;
            margin-top:14px;
            line-height:1.9;
        ">
            Thinking about trading in your current vehicle? Addis Auto Sales makes the process simple, transparent, and professional. 
            Submit your vehicle details to receive an estimated trade-in value, and our team will carefully review your information to help you maximize your offer. 
            Whether you are upgrading, downsizing, or preparing for your next purchase, we are here to help make your transition smooth and stress-free.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Trade-In Estimator</div>', unsafe_allow_html=True)
    with st.form("trade_in_form"):
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        t1, t2, t3 = st.columns(3)
        tn = t1.text_input("Your Name", key="trade_name")
        tp = t2.text_input("Phone", key="trade_phone")
        te = t3.text_input("Email", key="trade_email")
        vy = t1.text_input("Vehicle Year")
        vmk = t2.text_input("Vehicle Make")
        vmd = t3.text_input("Vehicle Model")
        mi = t1.number_input("Mileage", min_value=0)
        condition = t2.selectbox("Condition", ["Excellent", "Good", "Fair", "Needs Work"])
        payoff = t3.selectbox("Still Owe Money?", ["No", "Yes"])
        notes = st.text_area("Trade-In Notes")
        trade_submit = st.form_submit_button("Estimate Trade-In")
        if trade_submit:
            base = max(2500, 22000 - (mi * 0.06))
            multipliers = {"Excellent": 1.15, "Good": 1.0, "Fair": .78, "Needs Work": .55}
            estimate = base * multipliers[condition]
            query_db("""
            INSERT INTO trade_ins
            (name, phone, email, vehicle_year, vehicle_make, vehicle_model, mileage, condition, payoff, estimated_value, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (tn, tp, te, vy, vmk, vmd, mi, condition, payoff, f"${estimate:,.0f}", notes, str(datetime.now())), commit=True)
            notify_admin(
                "New Trade-In Request",
                tn,
                tp,
                f"{vy} {vmk} {vmd}",
                f"Mileage: {mi:,} | Condition: {condition} | Estimate: ${estimate:,.0f}"
            )
            
            send_email(
                te,
                "Addis Auto Sales Trade-In Request Received",
                f"""
Hi {tn},

We received your trade-in request.

Vehicle:
{vy} {vmk} {vmd}

Estimated Value:
Around ${estimate:,.0f}

Addis Auto Sales will verify the vehicle in person.

904 N La Brea Ave, Inglewood, CA
424-672-0018
"""
            )

            send_email(
                ADMIN_EMAIL,
                "New Trade-In Request",
                f"""
New trade-in request submitted.

Customer: {tn}
Phone: {tp}
Email: {te}
Vehicle: {vy} {vmk} {vmd}
Mileage: {mi:,}
Condition: {condition}
Estimated Value: ${estimate:,.0f}
"""
            )

            st.success(f"Estimated trade-in range: around ${estimate:,.0f}. Dealer will verify in person.")
        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# CONFIRMATION — hidden from menu
# =====================================================
elif page == "Confirmation":
    data = st.session_state.get("confirmation_data")
    st.markdown('<div class="section-title">Confirmation</div>', unsafe_allow_html=True)

    if not data:
        st.info("No recent confirmation found.")
        if st.button("Go To Home"):
            st.session_state["force_page"] = "Home"
            st.rerun()
    else:
        st.markdown(f"""
        <div class="glass">
            <div class="confirm-check">✓</div>
            <div class="confirm-title">{data.get("title")}</div>
            <div class="confirm-subtitle">{data.get("subtitle")}</div>
            <p style="text-align:center;">{data.get("message")}</p>
            <hr>
            <p><b>Name:</b> {data.get("name")}</p>
            <p><b>Vehicle / Request:</b> {data.get("vehicle")}</p>
            <p><b>Date:</b> {data.get("date")}</p>
            <p><b>Time:</b> {data.get("time")}</p>
        </div>
        """, unsafe_allow_html=True)

        if data.get("ask_appointment"):
            st.markdown("### Would you like to schedule an appointment now?")
            c1, c2 = st.columns(2)
            if c1.button("Yes, Schedule Appointment"):
                st.session_state["force_page"] = "Appointment"
                st.rerun()
            if c2.button("No, Go Home"):
                st.session_state["force_page"] = "Home"
                st.rerun()
        else:
            c1, c2 = st.columns(2)
            if c1.button("Go Back Home"):
                st.session_state["force_page"] = "Home"
                st.rerun()
            if c2.button("Back To Showroom"):
                st.session_state["force_page"] = "Showroom"
                st.rerun()

# =====================================================
# DEALER PORTAL
# =====================================================
elif page == "Dealer Portal":
    if not st.session_state.get("auth", False):
        st.markdown('<div class="section-title">Dealer / Salesperson Login</div>', unsafe_allow_html=True)

        with st.form("dealer_sales_login"):
            username = st.text_input("Username", placeholder="admin or salesperson username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            login_submit = st.form_submit_button("Login")

            if login_submit:
                # Admin login
                if username.strip().lower() == "admin" and hashlib.sha256(password.encode()).hexdigest() == ADMIN_HASH:
                    st.session_state["auth"] = True
                    st.session_state["user_role"] = "Admin"
                    st.session_state["logged_in_username"] = "admin"
                    st.session_state["selected_salesperson"] = "Admin"
                    st.rerun()

                else:
                    users = query_db("""
                    SELECT *
                    FROM salespeople
                    WHERE username = ? AND password = ? AND status = 'Active'
                    """, (username.strip(), password.strip()))

                    if not users.empty:
                        user = users.iloc[0]
                        st.session_state["auth"] = True
                        st.session_state["user_role"] = "Salesperson"
                        st.session_state["logged_in_username"] = username.strip()
                        st.session_state["selected_salesperson"] = user["name"]
                        log_activity(user["name"], "Logged In", "Salesperson logged into dealer portal")
                        notify_admin(
                            "Salesperson Login",
                            user["name"],
                            "",
                            "",
                            "Salesperson logged into dealer portal"
                        )
                        st.rerun()
                    else:
                        st.error("Wrong username or password.")

    else:
        st.success(f"Dealer Portal Active — Logged in as {st.session_state.get('selected_salesperson', 'Admin')}")

        if st.button("Logout"):
            log_activity(st.session_state.get("selected_salesperson", "Unknown"), "Logged Out", "User logged out")
            st.session_state["auth"] = False
            st.session_state["user_role"] = None
            st.session_state["logged_in_username"] = None
            st.session_state["selected_salesperson"] = "Admin"
            st.rerun()

        if st.session_state.get("user_role") == "Admin":
            salespeople = query_db("SELECT * FROM salespeople WHERE status='Active' ORDER BY name ASC")
            if not salespeople.empty:
                selected_salesperson = st.selectbox("Current Salesperson / Admin User", ["Admin"] + salespeople["name"].tolist())
                st.session_state["selected_salesperson"] = selected_salesperson
            else:
                st.session_state["selected_salesperson"] = "Admin"

        if st.session_state.get("user_role") == "Salesperson":
            tabs = st.tabs([
                "Dashboard",
                "Add Vehicle",
                "Inventory",
                "Leads CRM",
                "Appointments"
            ])
        else:
            tabs = st.tabs([
                "Dashboard", "Add Vehicle", "Inventory", "Leads CRM", "Appointments",
                "Finance Apps", "Questionnaires", "Trade-Ins", "Reviews",
                "Salespeople", "Activity Log", "Notifications"
            ])

        with tabs[0]:
            total_cars = len(query_db("SELECT * FROM inventory"))
            available_cars = len(query_db("SELECT * FROM inventory WHERE status='Available'"))
            sold_cars = len(query_db("SELECT * FROM inventory WHERE status='Sold'"))
            total_leads = len(query_db("SELECT * FROM leads"))
            total_appts = len(query_db("SELECT * FROM appointments"))
            total_finance = len(query_db("SELECT * FROM finance_applications"))
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Total Cars", total_cars)
            c2.metric("Available", available_cars)
            c3.metric("Sold", sold_cars)
            c4.metric("Leads", total_leads)
            c5.metric("Appointments", total_appts)
            c6.metric("Finance Apps", total_finance)

            st.markdown("### Most Viewed Vehicles")
            viewed = query_db("SELECT year, make, model, views FROM inventory ORDER BY COALESCE(views,0) DESC LIMIT 10")
            st.dataframe(viewed, use_container_width=True)

        with tabs[1]:
            st.markdown("### Add New Vehicle")
            with st.form("add_vehicle_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                make = c1.text_input("Make")
                model = c2.text_input("Model")
                year = c1.number_input("Year", 1990, 2035, 2024)
                price = c2.number_input("Price", min_value=0)
                mileage = c1.number_input("Mileage", min_value=0)
                vin = c2.text_input("VIN")
                transmission = c1.selectbox("Transmission", ["Automatic", "Manual"])
                fuel = c2.selectbox("Fuel Type", ["Gasoline", "Hybrid", "Electric", "Diesel"])
                body_style = c1.selectbox("Body Style", ["Sedan", "SUV", "Truck", "Coupe", "Luxury", "Van", "Sports Car"])
                featured = c2.selectbox("Featured Vehicle?", ["No", "Yes"])
                status = c1.selectbox("Vehicle Status", ["Available", "Sold"])
                title_status = c2.selectbox("Title Status", ["Clean", "Salvage", "Rebuilt", "Ask Dealer"])
                accident_history = c1.selectbox("Accident History", ["No Accidents", "Minor Accident", "Accident Reported", "Ask Dealer"])
                owner_history = c2.selectbox("Owner History", ["One Owner", "Two Owners", "Multiple Owners", "Ask Dealer"])
                service_history = c1.text_input("Service History", placeholder="Regular service, dealer maintained...")
                exterior_color = c2.text_input("Exterior Color")
                interior_color = c1.text_input("Interior Color")
                description = st.text_area("Vehicle Description")
                photos = st.file_uploader("Upload Multiple Vehicle Photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
                videos = st.file_uploader("Upload Vehicle Videos", type=["mp4", "mov", "m4v"], accept_multiple_files=True)
                submit = st.form_submit_button("Publish Vehicle")

                if submit:
                    if not make or not model:
                        st.error("Please enter the vehicle make and model.")
                    elif not photos:
                        st.error("Please upload at least one vehicle photo.")
                    else:
                        saved_paths = save_uploaded_files(photos, IMG_DIR)
                        video_paths = save_uploaded_files(videos, VIDEO_DIR)
                        query_db("""
                        INSERT INTO inventory
                        (make, model, year, price, mileage, transmission, fuel, body_style, featured, status,
                         image_paths, created_at, video_paths, title_status, accident_history, owner_history,
                         service_history, vin, exterior_color, interior_color, description, views)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (make, model, year, price, mileage, transmission, fuel, body_style, featured, status,
                              json.dumps(saved_paths), str(datetime.now()), json.dumps(video_paths), title_status,
                              accident_history, owner_history, service_history, vin, exterior_color, interior_color,
                              description, 0), commit=True)

                        vehicle_label = f"{year} {make} {model}"
                        log_activity(st.session_state["selected_salesperson"], "Added Vehicle", f"{vehicle_label} | Status: {status} | Price: ${price:,.0f}")
                        create_notification("New Vehicle Added", vehicle_label)

                        send_email(
                            ADMIN_EMAIL,
                            "Vehicle Posted Successfully",
                            f"""
A vehicle was posted successfully.

Posted By: {st.session_state["selected_salesperson"]}
Vehicle: {vehicle_label}
Status: {status}
Price: ${price:,.0f}
"""
                        )

                        notify_admin(
                            "Vehicle Posted",
                            st.session_state["selected_salesperson"],
                            "",
                            vehicle_label,
                            f"Status: {status} | Price: ${price:,.0f}"
                        )

                        st.session_state["confirmation_data"] = {
                            "title": "Vehicle Published Successfully",
                            "subtitle": "The vehicle is now LIVE in the showroom.",
                            "message": f"{st.session_state['selected_salesperson']} successfully posted a new available vehicle.",
                            "name": st.session_state["selected_salesperson"],
                            "vehicle": vehicle_label,
                            "date": str(datetime.now().date()),
                            "time": str(datetime.now().strftime("%I:%M %p")),
                            "ask_appointment": False
                        }

                        # Redirect admin / salesperson to confirmation page
                        st.session_state["force_page"] = "Confirmation"
                        st.rerun()

        with tabs[2]:
            st.markdown("### Inventory Manager")
            inv = query_db("SELECT * FROM inventory ORDER BY id DESC")
            if inv.empty:
                st.info("No vehicles uploaded yet.")
            else:
                for _, row in inv.iterrows():
                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        c1.write(f"**{row['year']} {row['make']} {row['model']}**")
                        c2.write(f"${row['price']:,.0f}")
                        c3.write(f"Status: **{row['status']}**")
                        button_label = "Mark Sold" if row["status"] == "Available" else "Mark Available"
                        if c4.button(button_label, key=f"status_toggle_{row['id']}"):
                            new_status = "Sold" if row["status"] == "Available" else "Available"
                            query_db("UPDATE inventory SET status=? WHERE id=?", (new_status, row["id"]), commit=True)
                            log_activity(st.session_state["selected_salesperson"], "Changed Vehicle Status", f"{row['year']} {row['make']} {row['model']} changed to {new_status}")
                            notify_admin(
                                "Vehicle Status Changed",
                                st.session_state["selected_salesperson"],
                                "",
                                f"{row['year']} {row['make']} {row['model']}",
                                f"New status: {new_status}"
                            )
                            st.rerun()
                    st.divider()

        with tabs[3]:
            st.markdown("### Lead Pipeline CRM")
            leads = query_db("SELECT * FROM leads ORDER BY id DESC")
            if leads.empty:
                st.info("No leads yet.")
            else:
                status_options = ["New Lead", "Contacted", "Appointment Set", "Financing", "Sold", "Closed"]
                for _, lead in leads.iterrows():
                    with st.expander(f"{lead['name']} - {lead['vehicle_type']} - {lead.get('status') or 'New Lead'}"):
                        st.write(lead.to_dict())
                        new_status = st.selectbox("Update Status", status_options, index=status_options.index(lead.get("status") if lead.get("status") in status_options else "New Lead"), key=f"lead_status_{lead['id']}")
                        assigned = st.text_input("Assigned To", value=lead.get("assigned_to") or "", key=f"assigned_{lead['id']}")
                        if st.button("Save Lead Update", key=f"save_lead_{lead['id']}"):
                            query_db("UPDATE leads SET status=?, assigned_to=? WHERE id=?", (new_status, assigned, int(lead["id"])), commit=True)
                            log_activity(st.session_state["selected_salesperson"], "Updated Lead", f"Lead {lead['name']} set to {new_status}")
                            notify_admin(
                                "Lead Updated",
                                st.session_state["selected_salesperson"],
                                "",
                                str(lead.get("vehicle_type", "")),
                                f"Lead: {lead['name']} | Status: {new_status} | Assigned: {assigned}"
                            )
                            st.rerun()

        with tabs[4]:
            st.markdown("### Appointments")
            st.dataframe(query_db("SELECT * FROM appointments ORDER BY id DESC"), use_container_width=True)

        if st.session_state.get("user_role") == "Admin":
            with tabs[5]:
                st.markdown("### Finance Applications")
                st.dataframe(query_db("SELECT * FROM finance_applications ORDER BY id DESC"), use_container_width=True)

            with tabs[6]:
                st.markdown("### Buyer Questionnaires")
                st.dataframe(query_db("SELECT * FROM buyer_questionnaires ORDER BY id DESC"), use_container_width=True)

            with tabs[7]:
                st.markdown("### Trade-Ins")
                st.dataframe(query_db("SELECT * FROM trade_ins ORDER BY id DESC"), use_container_width=True)

            with tabs[8]:
                st.markdown("### Reviews")
                with st.form("review_form"):
                    rn = st.text_input("Customer Name")
                    rating = st.slider("Rating", 1, 5, 5)
                    review = st.text_area("Review")
                    if st.form_submit_button("Add Review"):
                        query_db("INSERT INTO reviews (name, rating, review, created_at) VALUES (?,?,?,?)", (rn, rating, review, str(datetime.now())), commit=True)
                        notify_admin(
                            "New Review Added",
                            rn,
                            "",
                            "",
                            f"Rating: {rating} stars"
                        )
                        st.success("Review added.")
                st.dataframe(query_db("SELECT * FROM reviews ORDER BY id DESC"), use_container_width=True)

        with tabs[9]:
            st.markdown("### Add Salesperson")
            with st.form("add_salesperson_form"):
                c1, c2 = st.columns(2)
                sp_name = c1.text_input("Salesperson Name")
                sp_phone = c2.text_input("Phone")
                sp_email = c1.text_input("Email", placeholder="example@email.com")
                sp_role = c2.selectbox("Role", ["Sales Consultant", "Manager", "Finance Specialist", "Admin"])
                sp_specialties = st.text_input("Specialties", placeholder="Luxury, Finance, Trucks...")
                sp_status = st.selectbox("Status", ["Active", "Inactive"])
                sp_photo = st.file_uploader("Salesperson Photo", type=["jpg", "jpeg", "png"])
                add_sp = st.form_submit_button("Add Salesperson")
                if add_sp:
                    if not sp_name:
                        st.error("Please enter salesperson name.")
                    else:
                        photo_path = ""
                        if sp_photo:
                            photo_path = save_uploaded_files([sp_photo], IMG_DIR)[0]
                        query_db("INSERT INTO salespeople (name, phone, email, role, status, created_at, photo_path, specialties) VALUES (?,?,?,?,?,?,?,?)", (sp_name, sp_phone, sp_email, sp_role, sp_status, str(datetime.now()), photo_path, sp_specialties), commit=True)
                        log_activity(st.session_state["selected_salesperson"], "Added Salesperson", f"{sp_name} | Role: {sp_role} | Status: {sp_status}")
                        st.success("Salesperson added.")
                        st.rerun()

            team = query_db("SELECT * FROM salespeople ORDER BY id DESC")
            st.dataframe(team, use_container_width=True)

            with tabs[10]:
                st.markdown("### Salesperson Activity Log")
                st.dataframe(query_db("SELECT * FROM activity_logs ORDER BY id DESC"), use_container_width=True)

            with tabs[11]:
                st.markdown("### Notifications")
                st.dataframe(query_db("SELECT * FROM notifications ORDER BY id DESC"), use_container_width=True)
                st.markdown("### SMS Logs")
                st.dataframe(query_db("SELECT * FROM sms_logs ORDER BY id DESC"), use_container_width=True)

