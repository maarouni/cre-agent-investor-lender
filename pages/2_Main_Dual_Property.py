import streamlit as st
from io import BytesIO
import os
import sys  # ✅ Move this before using sys

sys.path.append(os.path.abspath(".."))  # ✅ Now valid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
import matplotlib.pyplot as plt
import pandas as pd

from calc_engine import calculate_metrics
from pdf_dual import generate_pdf, generate_comparison_pdf, generate_comparison_pdf_table_style
from pdf_dual import generate_ai_verdict

load_dotenv()

# ✅ Add this right below the imports — before any Streamlit UI code
st.set_page_config(
    page_title="Dual Property Comparison Evaluator",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔐 Password Gate — load from .env or fallback
load_dotenv()
APP_PASSWORD = os.getenv("APP_PASSWORD", "SmartInvest1!")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🏘️ Dual Property Deal Evaluator")
    password = st.text_input("🔒 Please enter access password", type="password")

    if password == APP_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("❌ Incorrect password. Please try again.")
    st.stop()


# ✅ Titles shown only after succesful login
st.markdown("## 🏡 Real Estate Deal Evaluator")
st.header("🔄 Side-by-Side Deal Comparison")

st.markdown(
    "<p style='font-size:18px; color:white; font-weight:bold;'>🔍 Compare investment options side-by-side to optimize ROI, cash flow, and equity growth.</p>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='font-size:18px; color:white; font-weight:bold;'>Input real numbers for Property A & B to model ROI, cash flow, and appreciation.</p>",
    unsafe_allow_html=True
)

st.markdown("---")

with open("Investment_Metrics_User_Guide.pdf", "rb") as f:
    st.download_button(
        label="📘 Download User Manual (PDF)",
        data=f,
        file_name="Investment_Metrics_User_Guide.pdf",
        mime="application/pdf"
    )


# ============================
# Sidebar Inputs
# ============================
st.sidebar.markdown(
    "<h2 style='color:white; font-size:24px;'>🧾 Shared Financial Inputs</h2>",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    "<p style='color:white; font-size:16px;'>These settings apply to both Property A and Property B</p>",
    unsafe_allow_html=True
)

st.sidebar.subheader("📍 Property Information")

address_a = st.sidebar.text_input("Address (Property A)", "")
zip_code_a = st.sidebar.text_input("ZIP Code (Property A)", "")

address_b = st.sidebar.text_input("Address (Property B)", "")
zip_code_b = st.sidebar.text_input("ZIP Code (Property B)", "")

st.sidebar.subheader("💰 Financing & Growth")

# ✅ Match Single-page CRE terminology (labels only)
mortgage_rate = st.sidebar.slider("📈 Loan Interest Rate (%)", 0.0, 15.0, 5.5, 0.1)
mortgage_term = st.sidebar.slider("📆 Amortization Term (years)", 5, 40, 30)
vacancy_rate = st.sidebar.slider("🏠 Economic Vacancy (%)", 0.0, 20.0, 5.0, 0.5)


# ============================
# Main Inputs A/B
# ============================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 Property A")
    purchase_price_a = st.number_input("Acquisition Price (A)", value=300000)
    # ✅ CRE label fix: Down Payment -> Equity Contribution (no logic change)
    down_payment_pct_a = st.slider("Equity Contribution (A) (%)", 0.0, 100.0, value=20.0, step=1.0)
    rent_a = st.number_input("In-Place Rent (A) ($/mo)", value=2000)
    monthly_expenses_a = st.number_input("Operating Expenses (A) (OpEx) ($/mo)", value=300, key="monthly_expenses_a")
    appreciation_rate_a = st.slider("Annual Appreciation (A) (%)", 0.0, 10.0, value=3.0, step=0.1, key="appreciation_rate_a")
    rent_growth_rate_a = st.slider("Annual Rent Growth (A) (%)", 0.0, 10.0, value=2.0, step=0.1, key="rent_growth_rate_a")
    # ✅ CRE label fix: Investment Time Horizon -> Hold Period
    time_horizon_a = st.slider("🏁 Hold Period (Years) A", 1, 30, value=10, key="time_horizon_a")

with col2:
    st.subheader("🏘️ Property B")
    purchase_price_b = st.number_input("Acquisition Price (B)", value=320000)
    # ✅ CRE label fix: Down Payment -> Equity Contribution (no logic change)
    down_payment_pct_b = st.slider("Equity Contribution (B) (%)", 0.0, 100.0, value=20.0, step=1.0)
    rent_b = st.number_input("In-Place Rent (B) ($/mo)", value=2100)
    monthly_expenses_b = st.number_input("Operating Expenses (B) (OpEx) ($/mo)", value=300, key="monthly_expenses_b")
    appreciation_rate_b = st.slider("Annual Appreciation (B) (%)", 0.0, 10.0, value=3.0, step=0.1, key="appreciation_rate_b")
    rent_growth_rate_b = st.slider("Annual Rent Growth (B) (%)", 0.0, 10.0, value=2.0, step=0.1, key="rent_growth_rate_b")
    # ✅ CRE label fix + typo fix (was incorrectly "A" before)
    time_horizon_b = st.slider("🏁 Hold Period (Years) B", 1, 30, value=10, key="time_horizon_b")


# ============================
# Calculate Metrics
# ============================
metrics_a = calculate_metrics(
    purchase_price_a,
    rent_a,
    down_payment_pct_a,
    mortgage_rate,
    mortgage_term,
    monthly_expenses_a,
    vacancy_rate,
    appreciation_rate_a,
    rent_growth_rate_a,
    time_horizon_a
)

metrics_b = calculate_metrics(
    purchase_price_b,
    rent_b,
    down_payment_pct_b,
    mortgage_rate,
    mortgage_term,
    monthly_expenses_b,
    vacancy_rate,
    appreciation_rate_b,
    rent_growth_rate_b,
    time_horizon_b
)


# ============================
# Download Comparison PDF
# ============================
if metrics_a and metrics_b:
    comparison_pdf = generate_comparison_pdf_table_style(
        metrics_a, metrics_b,
        address_a=address_a,
        zip_a=zip_code_a,
        address_b=address_b,
        zip_b=zip_code_b
    )

    st.download_button(
        label="📄 Download Comparison PDF",
        data=comparison_pdf,
        file_name="comparison_report.pdf",
        mime="application/pdf",
        key="download_comparison_pdf"
    )


# ============================
# AI Verdict + Grade
# ============================
verdict_input = {
    "ROI (%)": f"{metrics_a.get('ROI (%)', 0)} vs {metrics_b.get('ROI (%)', 0)}",
    "Multi-Year Cash Flow A": metrics_a.get("Multi-Year Cash Flow", []),
    "Multi-Year Cash Flow B": metrics_b.get("Multi-Year Cash Flow", []),
    "Cap Rate (%) A": metrics_a.get("Cap Rate (%)", 0),
    "Cap Rate (%) B": metrics_b.get("Cap Rate (%)", 0),
    "Cash-on-Cash Return (%) A": metrics_a.get("Cash-on-Cash Return (%)", 0),
    "Cash-on-Cash Return (%) B": metrics_b.get("Cash-on-Cash Return (%)", 0),
}

summary_text, grade = generate_ai_verdict(metrics_a, metrics_b)

metrics_a["AI Verdict"] = summary_text
metrics_a["Grade"] = grade
metrics_b["AI Verdict"] = summary_text
metrics_b["Grade"] = grade


# ============================
# Generate Dual PDF (Email uses this)
# ============================
summary_text = f"Property A is a {metrics_a['Grade']}-grade rental, and Property B is a {metrics_b['Grade']}-grade rental with upside potential"

pdf_bytes = generate_pdf(
    property_data_a={
        "Address": address_a,
        "ZIP Code": zip_code_a,
        "Purchase Price": purchase_price_a,
        "Monthly Rent": rent_a,
        "Monthly Expenses": monthly_expenses_a,
        # NOTE: keeping key name as-is to avoid breaking pdf generator expectations
        "Down Payment (%)": down_payment_pct_a,
        "Appreciation Rate (%)": appreciation_rate_a,
        "Rent Growth Rate (%)": rent_growth_rate_a,
        "Mortgage Rate (%)": mortgage_rate,
        "Mortgage Term (Years)": mortgage_term,
        "Vacancy Rate (%)": vacancy_rate,
    },
    property_data_b={
        "Address": address_b,
        "ZIP Code": zip_code_b,
        "Purchase Price": purchase_price_b,
        "Monthly Rent": rent_b,
        "Monthly Expenses": monthly_expenses_b,
        # NOTE: keeping key name as-is to avoid breaking pdf generator expectations
        "Down Payment (%)": down_payment_pct_b,
        "Appreciation Rate (%)": appreciation_rate_b,
        "Rent Growth Rate (%)": rent_growth_rate_b,
        "Mortgage Rate (%)": mortgage_rate,
        "Mortgage Term (Years)": mortgage_term,
        "Vacancy Rate (%)": vacancy_rate,
    },
    metrics_a=metrics_a,
    metrics_b=metrics_b,
    summary_text=summary_text
)


# ============================
# Plot
# ============================
cf_a = metrics_a.get("Multi-Year Cash Flow", [])
cf_b = metrics_b.get("Multi-Year Cash Flow", [])

if isinstance(cf_a, str):
    cf_a = [float(x.strip()) for x in cf_a.strip("[]").split(",") if x.strip()]
if isinstance(cf_b, str):
    cf_b = [float(x.strip()) for x in cf_b.strip("[]").split(",") if x.strip()]

st.subheader("📈 Multi-Year ROI, Rent & Cash Flow Comparison (A vs B)")
st.subheader("📈 Long-Term Metrics")

col1, col2, col3 = st.columns(3)
col1.metric("IRR A (Operational) (%)", f"{metrics_a.get('IRR (Operational) (%)', 0):.2f}")
col2.metric("IRR A (Total incl. Sale) (%)", f"{metrics_a.get('IRR (Total incl. Sale) (%)', 0):.2f}")
col3.metric("Equity Multiple A", f"{metrics_a.get('equity_multiple', 0):.2f}")

col4, col5, col6 = st.columns(3)
col4.metric("IRR B (Operational) (%)", f"{metrics_b.get('IRR (Operational) (%)', 0):.2f}")
col5.metric("IRR B (Total incl. Sale) (%)", f"{metrics_b.get('IRR (Total incl. Sale) (%)', 0):.2f}")
col6.metric("Equity Multiple B", f"{metrics_b.get('equity_multiple', 0):.2f}")

max_years = max(len(cf_a), len(cf_b))
cf_a += [0] * (max_years - len(cf_a))
cf_b += [0] * (max_years - len(cf_b))

rent_a_series = metrics_a.get("Annual Rents $ (by year)", [])
rent_b_series = metrics_b.get("Annual Rents $ (by year)", [])
roi_a = metrics_a.get("Annual ROI % (by year)", [])
roi_b = metrics_b.get("Annual ROI % (by year)", [])

fig, ax1 = plt.subplots()
years_a = list(range(1, len(cf_a) + 1))
years_b = list(range(1, len(cf_b) + 1))

years_a = years_a[:min(len(years_a), len(rent_a_series), len(roi_a), len(cf_a))]
years_b = years_b[:min(len(years_b), len(rent_b_series), len(roi_b), len(cf_b))]

cf_a = cf_a[:len(years_a)]
cf_b = cf_b[:len(years_b)]
rent_a_series = rent_a_series[:len(years_a)]
rent_b_series = rent_b_series[:len(years_b)]
roi_a = roi_a[:len(years_a)]
roi_b = roi_b[:len(years_b)]

ax1.plot(years_a, cf_a, marker='o', label="Cash Flow A ($)", color='blue')
ax1.plot(years_b, cf_b, marker='o', label="Cash Flow B ($)", color='skyblue')
ax1.plot(years_a, rent_a_series, marker='s', linestyle='--', label="Pro Forma Rent A ($/yr)", color='orange')
ax1.plot(years_b, rent_b_series, marker='s', linestyle='--', label="Pro Forma Rent B ($/yr)", color='goldenrod')
ax1.set_xlabel("Year")
ax1.set_ylabel("Cash Flow / Rent ($)")
ax1.grid(True)

ax2 = ax1.twinx()
ax2.plot(years_a, roi_a, marker='^', linestyle='-', label="ROI A (%)", color='green')
ax2.plot(years_b, roi_b, marker='^', linestyle='--', label="ROI B (%)", color='darkgreen')
ax2.set_ylabel("ROI (%)", color='green')
ax2.tick_params(axis='y', labelcolor='green')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

ax1.set_title("Projected Cash Flow, Rent, and ROI Over Time")
st.pyplot(fig)


# ============================
# Email Section
# ============================
st.markdown("### 📨 Email This Report")
recipient_email = st.text_input("Enter email address to send the report", placeholder="you@example.com")

if st.button("Send Email Report") and recipient_email:
    import re
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        st.error("❌ Please enter a valid email address.")
        st.stop()
    try:
        st.write("📤 Attempting to send email...")
        msg = EmailMessage()
        msg["Subject"] = "Your Real Estate Evaluation Report"
        msg["From"] = os.getenv("EMAIL_USER")
        msg["To"] = recipient_email
        msg.set_content("Please find attached your real estate evaluation report.")

        pdf_bytes.seek(0)
        msg.add_attachment(
            pdf_bytes.read(),
            maintype="application",
            subtype="pdf",
            filename="real_estate_report.pdf"
        )

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)

        st.success(f"✅ Report sent to {recipient_email}!")
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")


# =============================
# 🔧 Optional Enhancements
# =============================
with st.expander("🔧 Optional Enhancements", expanded=False):

    st.subheader("🏗️ Capital Improvements Tracker")
    st.caption("Use this to record upgrades like kitchen remodels, HVAC systems, or roof replacements.")

    initial_data = pd.DataFrame({
        "Year": [""],
        "Amount ($)": [""],
        "Description": [""],
        "Rent Uplift ($/mo)": [""]
    })

    improvements_df = st.data_editor(
        initial_data,
        num_rows="dynamic",
        width='stretch',
        key="improvements_editor"
    )

    improvements_df["Amount ($)"] = pd.to_numeric(improvements_df["Amount ($)"], errors="coerce")
    improvements_df["Rent Uplift ($/mo)"] = pd.to_numeric(improvements_df["Rent Uplift ($/mo)"], errors="coerce")
    improvements_df["Annual Uplift ($)"] = improvements_df["Rent Uplift ($/mo)"] * 12
    improvements_df["ROI (%)"] = (improvements_df["Annual Uplift ($)"] / improvements_df["Amount ($)"]) * 100

    valid_df = improvements_df.dropna(subset=["Amount ($)", "Annual Uplift ($)", "ROI (%)"])

    total_cost = valid_df["Amount ($)"].sum()
    weighted_roi = (
        (valid_df["Amount ($)"] * valid_df["ROI (%)"]).sum() / total_cost
        if total_cost > 0 else 0
    )

    st.success(f"📊 Weighted ROI from Capital Improvements: {weighted_roi:.2f}% (based on ${total_cost:,.0f} spent)")
