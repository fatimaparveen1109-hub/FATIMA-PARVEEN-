# Fatima-Parveen — Parcel Privé

Privacy-Based Automated Parcel Locker Delivery System — Streamlit academic prototype.

## Features
- Public landing page with How It Works and Privacy Policy
- Role-based login and account creation for Customer, Seller, Rider and Admin
- Product catalogue, cart, checkout, preferred/approved backup hub selection
- Delivery ID generation and order workflow across customer, seller, rider and admin dashboards
- Role-specific views that hide customer home address and phone from seller/rider screens
- SQLite database for local/demo persistence

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `pip install -r requirements.txt`
4. Run `streamlit run Fatima_app.py`

## Demo accounts
- Customer: `customer@parcelprive.demo` / `Customer123!`
- Seller: `seller@parcelprive.demo` / `Seller123!`
- Rider: `rider@parcelprive.demo` / `Rider123!`
- Admin: `admin@parcelprive.demo` / `Admin123!`

You can create new Customer, Seller and Rider accounts using the Create Account page. Admin sign-up is disabled.

## Deploy on Streamlit Community Cloud
1. Upload `Fatima_app.py`, `requirements.txt`, `README.md`, `.gitignore`, and `.streamlit/config.toml` to the root of your GitHub repository.
2. Create a new app in Streamlit Community Cloud.
3. Select your repository and branch `main`.
4. Set **Main file path** to `Fatima_app.py`.

## Important limitations
This is a demonstration/academic prototype, not a production-ready delivery platform. SQLite storage on hosted platforms may be ephemeral. For real multi-user use, migrate to hosted PostgreSQL and configure production-grade authentication, secure password hashing with unique salts, session controls, audit logs, payment verification, expiring one-time QR tokens and the other group's actual scanner/locker-controller interface. QR pickup is simulated and no physical lock is controlled. Use fictional data only. Do not put secrets or real customer data in GitHub.
