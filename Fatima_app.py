import streamlit as st
import sqlite3
import hashlib
import secrets
import string
from pathlib import Path
from datetime import datetime, timedelta

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "parcel_locker.db"

st.set_page_config(
    page_title="Parcel Privé | Private Parcel Delivery",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Theme ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --navy:#102A43; --teal:#0D9488; --mint:#E6FFFA; --ink:#243B53; --muted:#627D98; --line:#E5EDF3; }
html, body, [class*="css"] { font-family:'DM Sans', sans-serif; }
.stApp { background:#F7FAFC; color:var(--ink); }
.block-container { max-width:1240px; padding-top:1.25rem; padding-bottom:3rem; }
header[data-testid="stHeader"] { background:rgba(247,250,252,.92); }
#MainMenu, footer { visibility:hidden; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line)!important; border-radius:18px!important; }
.hero {
  background:linear-gradient(115deg, rgba(9,35,54,.96), rgba(13,148,136,.86)),
  radial-gradient(circle at 90% 10%, #61D5C8, transparent 30%);
  border-radius:26px; padding:3.2rem 3rem; color:white; min-height:330px;
  box-shadow:0 18px 45px rgba(16,42,67,.12);
}
.hero h1 { color:white; font-family:Manrope,sans-serif; font-size:clamp(2.2rem,4vw,3.6rem); line-height:1.08; letter-spacing:-1.5px; margin:.6rem 0 1rem; }
.hero p { color:#E6FFFA; font-size:1.05rem; max-width:650px; line-height:1.7; }
.eyebrow { color:#99F6E4; text-transform:uppercase; letter-spacing:2px; font-size:.78rem; font-weight:800; }
.brand {font-family:Manrope,sans-serif;font-weight:800;font-size:1.22rem;color:#102A43;letter-spacing:-.5px;}
.brand span {color:#0D9488;}
.topnav {display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.4rem 0 1.2rem;border-bottom:1px solid #E5EDF3;margin-bottom:1.6rem;}
.navnote {font-size:.88rem;color:#627D98;}
.feature {background:white;border:1px solid #E5EDF3;border-radius:18px;padding:1.2rem;height:100%;}
.feature .emoji {font-size:1.5rem;margin-bottom:.7rem;}
.feature h3 {font-size:1.02rem;color:#102A43;margin:.2rem 0 .5rem;}
.feature p {font-size:.9rem;line-height:1.55;color:#627D98;margin:0;}
.section-title {font-family:Manrope,sans-serif;font-size:1.8rem;font-weight:800;letter-spacing:-.6px;color:#102A43;}
.subtle {color:#627D98;}
.metric {background:white;border:1px solid #E5EDF3;border-radius:16px;padding:1rem 1.15rem;}
.metric .label {font-size:.8rem;color:#627D98;}
.metric .value {font-size:1.65rem;font-weight:800;color:#102A43;}
.status {display:inline-block;background:#E6FFFA;color:#0F766E;padding:.25rem .65rem;border-radius:999px;font-size:.78rem;font-weight:700;}
div.stButton > button {border-radius:11px;border:1px solid #D6E3EA;font-weight:700;min-height:2.7rem;}
div.stButton > button[kind="primary"] {background:#0D9488;border-color:#0D9488;color:white;}
div.stButton > button[kind="primary"]:hover {background:#0F766E;border-color:#0F766E;}
[data-testid="stSidebar"] {background:#102A43;}
[data-testid="stSidebar"] * {color:white!important;}
hr {border-color:#E5EDF3;}
.small-muted {font-size:.82rem;color:#627D98;}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          full_name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL,
          phone TEXT DEFAULT '',
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          delivery_id TEXT UNIQUE NOT NULL,
          customer_id INTEGER NOT NULL,
          customer_name TEXT NOT NULL,
          customer_email TEXT NOT NULL,
          customer_phone TEXT NOT NULL,
          customer_address TEXT NOT NULL,
          product_name TEXT NOT NULL,
          product_category TEXT NOT NULL,
          quantity INTEGER NOT NULL DEFAULT 1,
          amount REAL NOT NULL,
          preferred_hub TEXT NOT NULL,
          backup_hub TEXT NOT NULL,
          assigned_hub TEXT DEFAULT '',
          locker_no TEXT DEFAULT '',
          status TEXT NOT NULL,
          seller_note TEXT DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          delivery_id TEXT NOT NULL,
          status TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """)
        # Safe demo accounts, inserted only if absent. Passwords are shown in README.
        demos = [
          ("Demo Customer","customer@parcelprive.demo","03001234567","Customer123!","Customer"),
          ("Demo Seller","seller@parcelprive.demo","","Seller123!","Seller"),
          ("Demo Rider","rider@parcelprive.demo","","Rider123!","Rider"),
          ("Demo Admin","admin@parcelprive.demo","","Admin123!","Admin"),
        ]
        for name,email,phone,password,role in demos:
            if not con.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():
                con.execute("INSERT INTO users(full_name,email,phone,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                            (name,email,phone,hash_password(password),role,now()))
        con.commit()

def now():
    return datetime.now().isoformat(timespec="seconds")

def hash_password(password):
    # PBKDF2-based password hashing for this educational prototype.
    salt = "parcel-prive-demo-salt"
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()

def make_delivery_id():
    alphabet = string.ascii_uppercase + string.digits
    return "PP-" + "".join(secrets.choice(alphabet) for _ in range(8))

def add_event(delivery_id, status, note):
    with connect() as con:
        con.execute("INSERT INTO events(delivery_id,status,note,created_at) VALUES(?,?,?,?)",
                    (delivery_id,status,note,now()))
        con.commit()

def all_orders():
    with connect() as con:
        return con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()

def get_order(delivery_id):
    with connect() as con:
        return con.execute("SELECT * FROM orders WHERE delivery_id=?",(delivery_id,)).fetchone()

def order_events(delivery_id):
    with connect() as con:
        return con.execute("SELECT * FROM events WHERE delivery_id=? ORDER BY id",(delivery_id,)).fetchall()

def money(v):
    return f"Rs. {float(v):,.0f}"

init_db()

HUBS = ["DHA Hub", "Clifton Hub", "Gulshan Hub", "North Nazimabad Hub"]
PRODUCTS = [
    {"name":"Everyday Sneakers","category":"Shoes","price":5499,"emoji":"👟","desc":"Lightweight comfort for everyday journeys."},
    {"name":"Classic White Trainers","category":"Shoes","price":6299,"emoji":"👟","desc":"A clean, versatile everyday style."},
    {"name":"Minimal Backpack","category":"Accessories","price":3499,"emoji":"🎒","desc":"Smart storage for work and campus."},
    {"name":"Everyday Hoodie","category":"Clothing","price":4299,"emoji":"🧥","desc":"A relaxed fit with a soft feel."},
    {"name":"Classic Watch","category":"Accessories","price":7999,"emoji":"⌚","desc":"A timeless finish for any outfit."},
    {"name":"Cotton T-shirt","category":"Clothing","price":1899,"emoji":"👕","desc":"Soft cotton and an easy fit."},
]
STATUS_STEPS = ["Order Placed","Sent to Seller","Collected by Rider","At Locker Hub","Ready for Pickup","Collected"]

# ---------- Session ----------
for key, value in {"page":"Home","user":None,"cart":{},"login_role":"Customer"}.items():
    if key not in st.session_state:
        st.session_state[key] = value

def set_page(page):
    st.session_state.page = page

def current_user():
    return st.session_state.user

def login_user(email,password,role):
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE lower(email)=lower(?) AND role=?",(email.strip(),role)).fetchone()
    if row and row["password_hash"] == hash_password(password):
        st.session_state.user = dict(row)
        st.session_state.page = "Dashboard"
        st.session_state.cart = {}
        return True
    return False

def create_user(name,email,phone,password,role):
    try:
        with connect() as con:
            con.execute("INSERT INTO users(full_name,email,phone,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                        (name.strip(),email.strip().lower(),phone.strip(),hash_password(password),role,now()))
            con.commit()
        return True, ""
    except sqlite3.IntegrityError:
        return False, "This email already has an account. Please log in."

# ---------- Shared header ----------
def header():
    left, right = st.columns([2.2, 4.8])
    with left:
        st.markdown('<div class="brand">📦 Parcel <span>Privé</span></div><div class="small-muted">Your parcel. Your privacy.</div>', unsafe_allow_html=True)
    with right:
        cols = st.columns([1,1.3,1.3,1,1.25])
        labels = [("Home","Home"),("How it works","How It Works"),("Privacy policy","Privacy Policy"),("Login","Login"),("Create account","Create Account")]
        for col,(label,page) in zip(cols,labels):
            with col:
                if st.button(label, key="nav_"+page, use_container_width=True):
                    set_page(page)
                    st.rerun()
    st.markdown("<hr>", unsafe_allow_html=True)

def footer():
    st.markdown("<hr>", unsafe_allow_html=True)
    a,b,c = st.columns([2,3,2])
    with a: st.markdown('<div class="brand">📦 Parcel <span>Privé</span></div>',unsafe_allow_html=True)
    with b: st.markdown('<div class="small-muted">Privacy-first parcel delivery through secure automated locker hubs.</div>',unsafe_allow_html=True)
    with c: st.markdown('<div class="small-muted">Academic prototype · Karachi, Pakistan</div>',unsafe_allow_html=True)

def feature_card(emoji,title,desc):
    st.markdown(f'<div class="feature"><div class="emoji">{emoji}</div><h3>{title}</h3><p>{desc}</p></div>',unsafe_allow_html=True)

# ---------- Pages ----------
def home_page():
    header()
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">A smarter way to receive parcels</div>
      <h1>Your parcel.<br> Your privacy.</h1>
      <p>Shop with confidence. Your parcel travels to a secure locker hub—not to a shared list of personal details. Track every step, then collect when it suits you.</p>
    </div>
    """,unsafe_allow_html=True)
    st.write("")
    c1,c2,c3 = st.columns([1,1,1])
    with c1:
        if st.button("Explore the shop  →", type="primary", use_container_width=True):
            st.session_state.page = "Login"
            st.rerun()
    with c2:
        if st.button("How it works", use_container_width=True):
            set_page("How It Works"); st.rerun()
    with c3:
        if st.button("Create your account", use_container_width=True):
            set_page("Create Account"); st.rerun()
    st.write("")
    st.markdown('<div class="section-title">Delivery designed around you</div><p class="subtle">Simple to use. Thoughtful about your privacy.</p>',unsafe_allow_html=True)
    cols = st.columns(4)
    cards = [
        ("🔐","Privacy first","Your home address and personal phone number are not shown to sellers and riders by default."),
        ("📍","Choose your hub","Select your preferred hub and approve a backup hub at checkout."),
        ("📦","Track every step","Follow your order from checkout to seller, rider, locker and pickup."),
        ("📲","Secure pickup","Pickup instructions are issued after the parcel deposit is confirmed."),
    ]
    for col,card in zip(cols,cards):
        with col: feature_card(*card)
    st.write("")
    st.markdown('<div class="section-title">How delivery works</div>',unsafe_allow_html=True)
    steps = st.columns(4)
    for col,(n,title,desc) in zip(steps,[
        ("01","Shop","Choose your items and check out."),
        ("02","Seller prepares","Seller sees only the information needed to fulfil the order."),
        ("03","Rider delivers","Rider takes the parcel to the assigned secure hub."),
        ("04","You collect","Use your pickup instructions when your parcel is ready."),
    ]):
        with col:
            st.markdown(f'<div class="feature"><div class="eyebrow" style="color:#0D9488">{n}</div><h3>{title}</h3><p>{desc}</p></div>',unsafe_allow_html=True)
    st.write("")
    footer()

def how_page():
    header()
    st.markdown('<div class="section-title">How it works</div><p class="subtle">One order, clear handoffs, and privacy-conscious delivery.</p>',unsafe_allow_html=True)
    steps = [
      ("1. Create an account","Register as a customer, seller, rider or administrator. Each role gets its own workspace."),
      ("2. Shop and check out","The customer selects products, confirms contact details, and chooses a preferred hub plus an approved backup."),
      ("3. Seller prepares the parcel","The seller receives the delivery ID, item details and only the fulfilment information they need. Home address and personal phone are restricted."),
      ("4. Rider collects the parcel","The rider sees assigned jobs, seller collection information and the destination hub—not the customer's home address."),
      ("5. Locker deposit is confirmed","The hub and locker are assigned only when availability is checked. The pickup window begins after a confirmed deposit."),
      ("6. Customer collects","The customer follows pickup instructions. In this prototype, QR tokens are simulated and do not operate physical hardware."),
    ]
    for i in range(0,len(steps),2):
        cols = st.columns(2)
        for col,(title,desc) in zip(cols,steps[i:i+2]):
            with col:
                st.markdown(f'<div class="feature"><h3>{title}</h3><p>{desc}</p></div>',unsafe_allow_html=True)
        st.write("")
    if st.button("Create an account",type="primary"):
        set_page("Create Account"); st.rerun()
    footer()

def privacy_page():
    header()
    st.markdown('<div class="section-title">Privacy policy</div><p class="subtle">Plain-language overview of how this academic prototype handles information.</p>',unsafe_allow_html=True)
    sections = [
      ("Information collected","Account name, email, optional phone number, order items, delivery preferences, order status and the details needed to fulfil a delivery."),
      ("What sellers can see","Delivery ID, ordered products, quantity, order notes and the fulfilment information needed to prepare the parcel. Customer home address and personal phone are not displayed in the seller dashboard."),
      ("What riders can see","Assigned delivery ID, seller collection information, destination hub, locker assignment and operational status. Customer home address and personal phone are not displayed."),
      ("Storage and security","The starter app stores data in a local SQLite database file. Streamlit cloud storage can be ephemeral; a production deployment should use hosted PostgreSQL, secure secrets, stronger account controls and audit logging."),
      ("QR and locker hardware","This version simulates pickup instructions. It does not validate real hardware unlocks or payment transactions. A production version must use expiring, one-time server-validated tokens and a verified hardware interface."),
      ("Your choices","Use demo data only. Do not enter real customer personal information into this academic prototype."),
    ]
    for title,desc in sections:
        with st.expander(title,expanded=False):
            st.write(desc)
    footer()

def auth_page(create=False):
    header()
    left,right = st.columns([1.05,1.4],gap="large")
    with left:
        st.markdown('<div class="section-title">'+("Create your account" if create else "Welcome back")+'</div>',unsafe_allow_html=True)
        st.markdown('<p class="subtle">'+("Join Parcel Privé for a more private delivery experience." if create else "Choose your role and sign in to your workspace.")+'</p>',unsafe_allow_html=True)
        st.markdown('<div class="feature"><h3>🔐 Privacy-first by design</h3><p>Separate workspaces help each role see only the information needed for their task.</p><br><h3>📦 One connected journey</h3><p>Orders move through a shared order workflow from customer to seller to rider and locker hub.</p></div>',unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            if create:
                st.subheader("Create account")
                role = st.selectbox("I want to register as",["Customer","Seller","Rider","Admin"],key="signup_role")
                st.caption("For a real deployment, public Admin registration must be disabled and admin accounts provisioned securely.")
                name = st.text_input("Full name",key="signup_name",placeholder="Enter your full name")
                email = st.text_input("Email address",key="signup_email",placeholder="you@example.com")
                phone = st.text_input("Phone number (optional)",key="signup_phone",placeholder="03xx xxxxxxx")
                password = st.text_input("Password",type="password",key="signup_password")
                confirm = st.text_input("Confirm password",type="password",key="signup_confirm")
                if st.button("Create account",type="primary",use_container_width=True):
                    if not name.strip() or not email.strip() or not password:
                        st.error("Please fill in your name, email and password.")
                    elif "@" not in email or "." not in email.split("@")[-1]:
                        st.error("Please enter a valid email address.")
                    elif len(password)<8:
                        st.error("Use a password with at least 8 characters.")
                    elif password != confirm:
                        st.error("Passwords do not match.")
                    elif role=="Admin":
                        st.error("Admin registration is disabled. Use the demo admin account for this prototype.")
                    else:
                        ok,msg = create_user(name,email,phone,password,role)
                        if ok:
                            st.success("Account created. You can now log in.")
                            st.session_state.login_role=role
                            st.session_state.page="Login"
                            st.rerun()
                        else: st.error(msg)
                if st.button("Already have an account? Log in",use_container_width=True):
                    set_page("Login"); st.rerun()
            else:
                st.subheader("Log in")
                role = st.selectbox("Login as",["Customer","Seller","Rider","Admin"],index=["Customer","Seller","Rider","Admin"].index(st.session_state.login_role),key="login_role_select")
                email = st.text_input("Email address",key="login_email",placeholder="you@example.com")
                password = st.text_input("Password",type="password",key="login_password")
                if st.button("Log in securely",type="primary",use_container_width=True):
                    if login_user(email,password,role):
                        st.success("Logged in.")
                        st.rerun()
                    else:
                        st.error("Email, password or selected role is incorrect.")
                if st.button("Create a new account",use_container_width=True):
                    set_page("Create Account"); st.rerun()
                with st.expander("Demo accounts"):
                    st.write("Customer: `customer@parcelprive.demo` / `Customer123!`")
                    st.write("Seller: `seller@parcelprive.demo` / `Seller123!`")
                    st.write("Rider: `rider@parcelprive.demo` / `Rider123!`")
                    st.write("Admin: `admin@parcelprive.demo` / `Admin123!`")
    footer()

def logout():
    st.session_state.user = None
    st.session_state.page = "Home"
    st.session_state.cart = {}
    st.rerun()

def dashboard_shell():
    user = current_user()
    role = user["role"]
    with st.sidebar:
        st.markdown('<div class="brand" style="color:white">📦 Parcel <span>Privé</span></div>',unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**{user['full_name']}**")
        st.caption(role+" workspace")
        st.markdown("---")
        if role=="Customer":
            pages = ["Overview","Shop","My Orders","Checkout","Track a Parcel","My Profile"]
        elif role=="Seller":
            pages = ["Overview","Incoming Orders","Dispatch History","My Profile"]
        elif role=="Rider":
            pages = ["Overview","Assigned Deliveries","Delivery History","My Profile"]
        else:
            pages = ["Overview","All Orders","Users","Hub & Locker Status","System Notes"]
        selected = st.radio("NAVIGATION",pages,label_visibility="collapsed",key=f"nav_{role}")
        st.markdown("---")
        if st.button("View public website",use_container_width=True):
            set_page("Home"); st.rerun()
        if st.button("Log out",use_container_width=True):
            logout()
    return selected

def create_order(customer, product, qty, preferred, backup):
    delivery_id = make_delivery_id()
    with connect() as con:
        con.execute("""INSERT INTO orders(delivery_id,customer_id,customer_name,customer_email,customer_phone,customer_address,
        product_name,product_category,quantity,amount,preferred_hub,backup_hub,status,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (delivery_id,customer["id"],customer["full_name"],customer["email"],customer.get("phone",""),"Address entered at checkout",
         product["name"],product["category"],qty,product["price"]*qty,preferred,backup,"Order Placed",now(),now()))
        con.commit()
    add_event(delivery_id,"Order Placed","Order created by customer.")
    add_event(delivery_id,"Sent to Seller","Order is now visible in the seller workspace.")
    with connect() as con:
        con.execute("UPDATE orders SET status='Sent to Seller',updated_at=? WHERE delivery_id=?",(now(),delivery_id))
        con.commit()
    return delivery_id

def status_update(order, status, note):
    with connect() as con:
        con.execute("UPDATE orders SET status=?,updated_at=? WHERE delivery_id=?",(status,now(),order["delivery_id"]))
        con.commit()
    add_event(order["delivery_id"],status,note)

def customer_dashboard(page):
    user=current_user()
    if page=="Overview":
        st.markdown(f'<div class="section-title">Good to see you, {user["full_name"].split()[0]}.</div><p class="subtle">Your deliveries, all in one private place.</p>',unsafe_allow_html=True)
        orders=[o for o in all_orders() if o["customer_id"]==user["id"]]
        a,b,c=st.columns(3)
        for col,label,value in [(a,"Total orders",len(orders)),(b,"In progress",sum(o["status"] not in ["Collected","Returned"] for o in orders)),(c,"Ready for pickup",sum(o["status"]=="Ready for Pickup" for o in orders))]:
            with col: st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div></div>',unsafe_allow_html=True)
        st.write("")
        st.subheader("Recent orders")
        if not orders: st.info("You have no orders yet. Open Shop to browse the demo catalogue.")
        else:
            for o in orders[:5]:
                with st.container(border=True):
                    x,y,z=st.columns([2.3,2,1])
                    x.markdown(f"**{o['product_name']}**  \n`{o['delivery_id']}`")
                    y.markdown(f"{money(o['amount'])}  \n<span class='status'>{o['status']}</span>",unsafe_allow_html=True)
                    with z:
                        if st.button("Track",key="track_"+o["delivery_id"]):
                            st.session_state.track_id=o["delivery_id"]; st.session_state[f"nav_Customer"]="Track a Parcel"; st.rerun()
        st.write("")
        if st.button("Browse products",type="primary"):
            st.session_state["nav_Customer"]="Shop"; st.rerun()
    elif page=="Shop":
        st.markdown('<div class="section-title">Discover your next favourite</div><p class="subtle">Demo catalogue · Product prices are illustrative.</p>',unsafe_allow_html=True)
        search=st.text_input("Search products",placeholder="Search shoes, clothing, accessories...")
        cats=["All","Shoes","Clothing","Accessories"]
        cat=st.radio("Category",cats,horizontal=True)
        products=[p for p in PRODUCTS if (cat=="All" or p["category"]==cat) and search.lower() in p["name"].lower()]
        cart=st.session_state.cart
        for i in range(0,len(products),3):
            cols=st.columns(3)
            for col,p in zip(cols,products[i:i+3]):
                with col:
                    with st.container(border=True):
                        st.markdown(f'<div style="background:linear-gradient(135deg,#E6FFFA,#F0F9FF);border-radius:14px;padding:1.8rem;text-align:center;font-size:3.5rem">{p["emoji"]}</div>',unsafe_allow_html=True)
                        st.markdown(f"**{p['name']}**")
                        st.caption(p["desc"])
                        st.markdown(f"### {money(p['price'])}")
                        qty=st.number_input("Quantity",min_value=1,max_value=10,value=cart.get(p["name"],1),key="qty_"+p["name"])
                        if st.button("Add to cart",key="add_"+p["name"],type="primary",use_container_width=True):
                            cart[p["name"]]=int(qty); st.session_state.cart=cart
                            st.toast(f"{p['name']} added to cart")
        st.write("")
        with st.container(border=True):
            st.subheader("Your cart")
            if not cart: st.write("Your cart is empty.")
            else:
                total=0
                for name,qty in cart.items():
                    p=next(x for x in PRODUCTS if x["name"]==name); total+=p["price"]*qty
                    st.write(f"{p['emoji']} **{name}** × {qty} — {money(p['price']*qty)}")
                st.markdown(f"**Subtotal: {money(total)}**")
                if st.button("Continue to checkout",type="primary"):
                    st.session_state["nav_Customer"]="My Orders"
                    st.session_state.page="Checkout"
                    st.rerun()
    elif page=="My Orders":
        st.markdown('<div class="section-title">My orders</div><p class="subtle">Your delivery IDs and parcel status.</p>',unsafe_allow_html=True)
        orders=[o for o in all_orders() if o["customer_id"]==user["id"]]
        if not orders: st.info("No orders yet. Go to Shop to place your first demo order.")
        for o in orders:
            with st.container(border=True):
                a,b,c=st.columns([2.2,1.3,1])
                a.markdown(f"**{o['product_name']} × {o['quantity']}**  \n`{o['delivery_id']}`  \n{money(o['amount'])}")
                b.markdown(f"<span class='status'>{o['status']}</span>",unsafe_allow_html=True)
                with c:
                    if st.button("View details",key="detail_"+o["delivery_id"]):
                        st.session_state.track_id=o["delivery_id"]; st.session_state["nav_Customer"]="Track a Parcel"; st.rerun()
        st.write("")
        if st.button("Shop now",type="primary"):
            st.session_state["nav_Customer"]="Shop"; st.rerun()
    elif page=="Track a Parcel":
        st.markdown('<div class="section-title">Track your parcel</div><p class="subtle">Enter a Delivery ID to see its latest status.</p>',unsafe_allow_html=True)
        default=st.session_state.get("track_id","")
        did=st.text_input("Delivery ID",value=default,placeholder="e.g. PP-AB12CD34")
        if st.button("Track parcel",type="primary"):
            st.session_state.track_id=did.strip().upper()
        did=st.session_state.get("track_id",did).strip().upper()
        o=get_order(did) if did else None
        if o and o["customer_id"]==user["id"]:
            st.success(f"{o['product_name']} · {o['status']}")
            st.write(f"**Delivery ID:** `{o['delivery_id']}`")
            st.write(f"**Preferred hub:** {o['preferred_hub']}  ·  **Backup hub:** {o['backup_hub']}")
            st.write(f"**Assigned hub:** {o['assigned_hub'] or 'Assigned after rider arrival confirmation'}")
            for ev in order_events(did):
                st.markdown(f"**{ev['status']}**  \n<span class='small-muted'>{ev['created_at']}</span>  \n{ev['note']}",unsafe_allow_html=True)
                st.markdown("---")
            if o["status"]=="Ready for Pickup":
                st.info("Demo pickup instructions are available. No physical locker will unlock from this prototype.")
                st.code("DEMO PICKUP TOKEN · "+secrets.token_urlsafe(12))
        elif did:
            st.warning("No order with that Delivery ID was found in your account.")
    elif page=="My Profile":
        st.markdown('<div class="section-title">My profile</div>',unsafe_allow_html=True)
        st.write(f"**Name:** {user['full_name']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Phone:** {user.get('phone','') or 'Not provided'}")
        st.caption("Prototype profile is read-only. Use demo data only.")
    elif page=="Checkout":
        cart=st.session_state.cart
        st.markdown('<div class="section-title">Checkout</div><p class="subtle">Confirm your order and choose a hub.</p>',unsafe_allow_html=True)
        if not cart:
            st.info("Your cart is empty.")
            if st.button("Go to shop",type="primary"): st.session_state["nav_Customer"]="Shop"; st.rerun()
        else:
            total=sum(next(p for p in PRODUCTS if p["name"]==n)["price"]*q for n,q in cart.items())
            with st.form("checkout_form"):
                st.subheader("Contact & delivery")
                phone=st.text_input("Phone number",value=user.get("phone",""))
                address=st.text_area("Home address (private; not shown to seller or rider)",placeholder="Enter your delivery contact address")
                c1,c2=st.columns(2)
                with c1: preferred=st.selectbox("Preferred locker hub",HUBS)
                with c2: backup=st.selectbox("Approved backup hub",[h for h in HUBS if h!=preferred])
                st.subheader("Order summary")
                for name,qty in cart.items(): st.write(f"{name} × {qty}")
                st.markdown(f"### Total: {money(total)}")
                submitted=st.form_submit_button("Place order",type="primary",use_container_width=True)
            if submitted:
                if not phone.strip() or not address.strip(): st.error("Please enter your phone number and address.")
                elif preferred==backup: st.error("Choose a different backup hub.")
                else:
                    p=next(p for p in PRODUCTS if p["name"] in cart)
                    did=create_order(user,p,cart[p["name"]],preferred,backup)
                    with connect() as con:
                        con.execute("UPDATE orders SET customer_phone=?,customer_address=? WHERE delivery_id=?",(phone.strip(),address.strip(),did)); con.commit()
                    st.session_state.cart={}
                    st.session_state.last_order=did
                    st.success("Order placed successfully.")
                    st.markdown(f"### Your Delivery ID: `{did}`")
                    st.write("Your order is now in the seller workspace. Track the status from My Orders.")
                    if st.button("View my order",type="primary"):
                        st.session_state.track_id=did; st.session_state["nav_Customer"]="Track a Parcel"; st.rerun()

def seller_dashboard(page):
    st.markdown('<div class="section-title">Seller workspace</div><p class="subtle">Prepare and dispatch orders with only the information needed for fulfilment.</p>',unsafe_allow_html=True)
    orders=all_orders()
    if page=="Overview":
        a,b,c=st.columns(3)
        for col,label,value in [(a,"Incoming orders",sum(o["status"]=="Sent to Seller" for o in orders)),(b,"Being prepared",sum(o["status"]=="Processing" for o in orders)),(c,"Dispatched",sum(o["status"] in ["Collected by Rider","At Locker Hub","Ready for Pickup","Collected"] for o in orders))]:
            with col: st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div></div>',unsafe_allow_html=True)
        st.write("")
        st.info("Privacy rule: customer home address and personal phone are not displayed on seller screens.")
        st.subheader("Recent incoming orders")
        visible=[o for o in orders if o["status"] in ["Sent to Seller","Processing"]][:5]
        if not visible: st.write("No incoming orders right now.")
        for o in visible: st.write(f"`{o['delivery_id']}` · {o['product_name']} · {o['status']}")
    elif page in ["Incoming Orders","Dispatch History"]:
        show=orders if page=="Incoming Orders" else [o for o in orders if o["status"] not in ["Sent to Seller","Processing"]]
        st.subheader(page)
        if not show: st.info("No orders to show yet.")
        for o in show:
            with st.container(border=True):
                a,b=st.columns([3,2])
                with a:
                    st.markdown(f"**{o['product_name']} × {o['quantity']}**")
                    st.code(o["delivery_id"])
                    st.write(f"Category: {o['product_category']} · Total: {money(o['amount'])}")
                    st.write(f"Delivery hub preference: {o['preferred_hub']} (backup approved: {o['backup_hub']})")
                    st.write("Customer home address and personal phone are hidden.")
                with b:
                    st.markdown(f"<span class='status'>{o['status']}</span>",unsafe_allow_html=True)
                    if o["status"]=="Sent to Seller":
                        if st.button("Start preparing",key="prep_"+o["delivery_id"],type="primary",use_container_width=True):
                            status_update(o,"Processing","Seller started preparing the parcel."); st.rerun()
                    elif o["status"]=="Processing":
                        if st.button("Mark ready for rider",key="ready_"+o["delivery_id"],type="primary",use_container_width=True):
                            status_update(o,"Ready for Rider","Parcel is ready for rider collection."); st.rerun()
                    elif o["status"] in ["Ready for Rider","Collected by Rider","At Locker Hub","Ready for Pickup","Collected"]:
                        st.caption("Order has moved to the next delivery stage.")
    elif page=="My Profile":
        st.write(f"**Account:** {current_user()['full_name']}")
        st.write("Seller role access is limited to order fulfilment.")

def rider_dashboard(page):
    st.markdown('<div class="section-title">Rider workspace</div><p class="subtle">Manage assigned collections and secure hub deliveries.</p>',unsafe_allow_html=True)
    orders=all_orders()
    if page=="Overview":
        a,b,c=st.columns(3)
        for col,label,value in [(a,"Ready to collect",sum(o["status"]=="Ready for Rider" for o in orders)),(b,"In transit",sum(o["status"]=="Collected by Rider" for o in orders)),(c,"At hub",sum(o["status"]=="At Locker Hub" for o in orders))]:
            with col: st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div></div>',unsafe_allow_html=True)
        st.write("")
        st.info("Privacy rule: the rider does not see the customer's home address or personal phone.")
    elif page in ["Assigned Deliveries","Delivery History"]:
        show=orders if page=="Assigned Deliveries" else [o for o in orders if o["status"] in ["At Locker Hub","Ready for Pickup","Collected"]]
        st.subheader(page)
        if not show: st.info("No delivery jobs right now. Orders appear here after the seller marks them ready for collection.")
        for o in show:
            if o["status"] not in ["Ready for Rider","Collected by Rider","At Locker Hub","Ready for Pickup","Collected"]: continue
            with st.container(border=True):
                a,b=st.columns([3,2])
                with a:
                    st.markdown(f"**{o['delivery_id']}** · {o['product_name']}")
                    st.write(f"Collect from seller fulfilment point → deliver to **{o['preferred_hub']}**")
                    st.write(f"Backup hub approved by customer: {o['backup_hub']}")
                    st.caption("Customer address and personal phone are hidden.")
                with b:
                    st.markdown(f"<span class='status'>{o['status']}</span>",unsafe_allow_html=True)
                    if o["status"]=="Ready for Rider":
                        if st.button("Confirm collection",key="collect_"+o["delivery_id"],type="primary",use_container_width=True):
                            status_update(o,"Collected by Rider","Rider confirmed parcel collection."); st.rerun()
                    elif o["status"]=="Collected by Rider":
                        hub=st.selectbox("Confirm destination hub",HUBS,index=HUBS.index(o["preferred_hub"]) if o["preferred_hub"] in HUBS else 0,key="hub_"+o["delivery_id"])
                        locker=st.selectbox("Locker compartment",["L-01 (small)","L-02 (small)","L-03 (medium)","L-04 (medium)","L-05 (large)"],key="locker_"+o["delivery_id"])
                        if st.button("Confirm deposit at hub",key="deposit_"+o["delivery_id"],type="primary",use_container_width=True):
                            with connect() as con:
                                con.execute("UPDATE orders SET assigned_hub=?,locker_no=? WHERE delivery_id=?",(hub,locker,o["delivery_id"])); con.commit()
                            status_update(o,"At Locker Hub",f"Rider recorded deposit at {hub}, compartment {locker}. Demo only; no hardware unlock is connected.")
                            status_update(get_order(o["delivery_id"]),"Ready for Pickup","Deposit recorded; pickup instructions can now be issued.")
                            st.rerun()
                    elif o["status"]=="Ready for Pickup":
                        st.write(f"Hub: {o['assigned_hub']} · Locker: {o['locker_no']}")
                        st.caption("Pickup timer/hardware is not active in this demo.")
    elif page=="My Profile":
        st.write(f"**Account:** {current_user()['full_name']}")
        st.write("Rider role access is limited to assigned delivery operations.")

def admin_dashboard(page):
    st.markdown('<div class="section-title">Admin control centre</div><p class="subtle">Operational overview for the academic prototype.</p>',unsafe_allow_html=True)
    orders=all_orders()
    with connect() as con: users=con.execute("SELECT id,full_name,email,role,created_at FROM users ORDER BY id").fetchall()
    if page=="Overview":
        a,b,c,d=st.columns(4)
        metrics=[("Total orders",len(orders)),("Registered users",len(users)),("Ready for pickup",sum(o["status"]=="Ready for Pickup" for o in orders)),("Demo hubs",len(HUBS))]
        for col,(label,value) in zip([a,b,c,d],metrics):
            with col: st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div></div>',unsafe_allow_html=True)
        st.write("")
        st.subheader("Recent activity")
        for o in orders[:8]: st.write(f"`{o['delivery_id']}` · {o['product_name']} · {o['status']}")
    elif page=="All Orders":
        st.subheader("All orders")
        if not orders: st.info("No orders have been placed yet.")
        for o in orders:
            with st.container(border=True):
                a,b=st.columns([3,2])
                a.markdown(f"**{o['delivery_id']}** · {o['product_name']} × {o['quantity']}")
                a.write(f"Customer: {o['customer_name']} · {money(o['amount'])}")
                b.write(f"Status: {o['status']}")
                new_status=st.selectbox("Admin status correction",["No change","Sent to Seller","Processing","Ready for Rider","Collected by Rider","At Locker Hub","Ready for Pickup","Collected","Returned"],key="admin_status_"+o["delivery_id"])
                if new_status!="No change" and st.button("Apply status",key="apply_"+o["delivery_id"]):
                    status_update(o,new_status,"Admin status update."); st.rerun()
    elif page=="Users":
        st.subheader("Registered users")
        for u in users: st.write(f"**{u['full_name']}** · {u['role']} · {u['email']}")
        st.caption("Demo admin tools are intentionally limited. Production requires audited privileged access.")
    elif page=="Hub & Locker Status":
        st.subheader("Demo hub overview")
        for hub in HUBS:
            assigned=[o for o in orders if o["assigned_hub"]==hub and o["status"]!="Collected"]
            with st.container(border=True):
                st.markdown(f"**📍 {hub}**")
                st.write(f"Active parcels recorded: {len(assigned)}")
                st.caption("Availability is a prototype record, not connected to physical locker sensors.")
    elif page=="System Notes":
        st.subheader("System notes")
        st.warning("This is an academic prototype. Before real deployment, configure hosted PostgreSQL, secure secrets, production-grade authentication, audit logs, QR validation and hardware integration.")
        st.write("Never store real customer data in this public demo.")

def dashboard_page():
    user=current_user()
    page=dashboard_shell()
    st.markdown(f'<div class="small-muted">PARCEL PRIVÉ  /  {user["role"].upper()} WORKSPACE</div>',unsafe_allow_html=True)
    st.write("")
    if user["role"]=="Customer": customer_dashboard(page)
    elif user["role"]=="Seller": seller_dashboard(page)
    elif user["role"]=="Rider": rider_dashboard(page)
    else: admin_dashboard(page)

# ---------- Router ----------
if current_user():
    dashboard_page()
else:
    page=st.session_state.page
    if page=="Home": home_page()
    elif page=="How It Works": how_page()
    elif page=="Privacy Policy": privacy_page()
    elif page=="Login": auth_page(False)
    elif page=="Create Account": auth_page(True)
    else:
        st.session_state.page="Home"
        st.rerun()
