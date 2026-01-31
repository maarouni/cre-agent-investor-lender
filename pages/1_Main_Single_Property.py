import streamlit as st
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
from calc_engine import calculate_metrics
from pdf_single import generate_pdf, generate_ai_verdict
from pdf_single_agent import generate_pdf as generate_agent_pdf  # 🔹 new import (agent PDF)

import matplotlib.pyplot as plt
from email.message import EmailMessage
import smtplib
import re
import pandas as pd
import numpy as np

load_dotenv()

st.set_page_config(page_title="Single Property Evaluator", layout="centered")
st.title("🏡 Real Estate Deal Evaluator")
st.markdown("Analyze the investment potential of a single property.")

# ===================================
# 🔐 CLEAN PASSWORD GATE (No extra icons)
# ===================================
APP_PASSWORD = os.getenv("APP_PASSWORD", "SmartInvest1!")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "pw_error" not in st.session_state:
    st.session_state.pw_error = False

# If user is NOT authenticated, show password UI and stop the app below
if not st.session_state.authenticated:

    # Show error only after a failed attempt
    if st.session_state.pw_error:
        st.error("❌ Incorrect password. Please try again.")
        st.session_state.pw_error = False  # reset flag for next run

    # Password input (masked, with browser eye icon)
    password = st.text_input(
        "🔒 Please enter access password",
        type="password"
    )

    # Validate ONLY when Unlock is pressed
    if st.button("Unlock"):
        if password == APP_PASSWORD:
            # ✅ Mark session as authenticated and rerun so field disappears
            st.session_state.authenticated = True
            st.rerun()
        else:
            # ❌ Wrong password → set flag and rerun to show error
            st.session_state.pw_error = True
            st.rerun()

    # If still not authenticated after this run, stop the rest of the app
    st.stop()

# ================================
# 📌 INPUT SIDEBAR
# ================================
st.sidebar.header("📌 Property Information")
street_address = st.sidebar.text_input("Street Address (optional)")
zip_code = st.sidebar.text_input("ZIP Code (optional)")
purchase_price = st.sidebar.number_input("Purchase Price ($)", min_value=10000, value=300000, step=1000)
monthly_rent = st.sidebar.number_input("Expected Monthly Rent ($)", min_value=0, value=2000, step=100)
monthly_expenses = st.sidebar.number_input(
    "Monthly Expenses ($: property tax + insurance + miscellaneous)",
    min_value=0, value=300, step=50
)

# 💰 Financing & Growth
st.sidebar.header("💰 Financing & Growth")
down_payment_pct = st.sidebar.slider("Down Payment (%)", 0, 100, 20)
mortgage_rate = st.sidebar.slider("Mortgage Rate (%)", 0.0, 15.0, 6.5)
mortgage_term = st.sidebar.number_input("Mortgage Term (years)", min_value=1, value=30)
vacancy_rate = st.sidebar.slider("Vacancy Rate (%)", 0, 100, 5)
appreciation_rate = st.sidebar.slider("Annual Appreciation Rate (%)", 0, 10, 3)
rent_growth_rate = st.sidebar.slider("Annual Rent Growth Rate (%)", 0, 10, 3)
time_horizon = st.sidebar.slider("🏁 Investment Time Horizon (Years)", 1, 30, 10)

# 👤 Agent Information (always available; used for Agent Report tab)
#st.sidebar.header("👤 Agent Information")
#agent_name = st.sidebar.text_input("Agent Name")
#brokerage_name = st.sidebar.text_input("Brokerage Name")
#client_name = st.sidebar.text_input("Client Name")
#agent_notes = st.sidebar.text_area("Notes for Client")

# ================================
# 🔢 RUN CALCULATIONS
# ================================
metrics = calculate_metrics(
    purchase_price, monthly_rent, down_payment_pct,
    mortgage_rate, mortgage_term,
    monthly_expenses, vacancy_rate, appreciation_rate, rent_growth_rate,
    time_horizon
)

# Build property_data once so both Investor & Agent PDFs can use it
property_data = {
    "street_address": street_address,
    "zip_code": zip_code,
    "purchase_price": purchase_price,
    "monthly_rent": monthly_rent,
    "monthly_expenses": monthly_expenses,
    "down_payment_pct": down_payment_pct,
    "mortgage_rate": mortgage_rate,
    "mortgage_term": mortgage_term,
    "vacancy_rate": vacancy_rate,
    "appreciation_rate": appreciation_rate,
    "rent_growth_rate": rent_growth_rate,
    "time_horizon": time_horizon
}
improvements_list = []

# AI verdict once, shared by all tabs
summary_text, grade = generate_ai_verdict(metrics)

# ================================
# 🧭 TABS
# ================================
tab1, tab2, tab3 = st.tabs(["Deal Analyzer", "Insights", "Agent Report"])

# ===================================================================
# TAB 1 — DEAL ANALYZER (EXISTING PRODUCTION FLOW)
# ===================================================================
with tab1:

    # =============================
    # 🧾 Generate Investor PDF (existing)
    # =============================
    pdf_bytes = generate_pdf(property_data, metrics, summary_text)

    # =============================
    # 📊 Long-Term Metrics
    # =============================
    st.subheader("📈 Long-Term Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("IRR (Operational) (%)", f"{metrics.get('IRR (Operational) (%)', 0):.2f}")
    col2.metric("IRR (Total incl. Sale) (%)", f"{metrics.get('IRR (Total incl. Sale) (%)', 0):.2f}")
    col3.metric("Equity Multiple", f"{metrics.get('equity_multiple', 0):.2f}")

    # =============================
    # 📈 Multi-Year Cash Flow Projection
    # =============================
    st.subheader("📈 Multi-Year Cash Flow Projection")
    fig, ax = plt.subplots()
    years = list(range(1, time_horizon + 1))

    ax.plot(years, metrics["Multi-Year Cash Flow"], marker='o', label="Multi-Year Cash Flow ($)")
    ax.plot(years, metrics["Annual Rents $ (by year)"], marker='s', linestyle='--', label="Projected Rent ($)")

    ax.set_xlabel("Year")
    ax.set_ylabel("Projected Cash Flow / Rent ($)")
    ax.grid(True)

    ax2 = ax.twinx()
    ax2.plot(years, metrics["Annual ROI % (by year)"], color='green', marker='^', label="ROI (%)")
    ax2.set_ylabel("ROI (%)", color='green')

    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left")

    ax.set_title("Multi - Year Projected Cash Flow & ROI")
    st.pyplot(fig)

    # =============================
    # 📘 Download User Manual
    # =============================
    st.markdown("---")
    try:
        with open("Investment_Metrics_User_Guide.pdf", "rb") as f:
            st.download_button(
                label="📘 Download User Manual (PDF)",
                data=f,
                file_name="Investment_Metrics_User_Guide.pdf",
                mime="application/pdf"
            )
    except FileNotFoundError:
        st.error("📄 User Manual PDF is missing from directory.")

    # =============================
    # 📄 PDF Download (Investor version)
    # =============================
    if pdf_bytes is not None:
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name="real_estate_report.pdf",
            mime="application/pdf",
            key="download_pdf_unique"
        )
    else:
        st.error("⚠️ PDF generation failed. Please check your input or logs.")

    # =============================
    # ✉️ Email This Report
    # =============================
    st.markdown("### 📨 Email This Report")
    recipient_email = st.text_input("Enter email address to send the report", placeholder="you@example.com")

    if st.button("Send Email Report") and recipient_email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
            st.error("❌ Please enter a valid email address.")
            st.stop()

        try:
            msg = EmailMessage()
            msg["Subject"] = "Your Real Estate Evaluation Report"
            msg["From"] = os.getenv("EMAIL_USER")
            msg["To"] = recipient_email
            msg.set_content("Please find attached your real estate evaluation report.")

            pdf_bytes.seek(0)
            msg.add_attachment(
                pdf_bytes.read(),
                maintype='application',
                subtype='pdf',
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
        # HYBRID MODEL: use user uplift if present, otherwise fallback to 65× rule
        def compute_uplift(row):
            # If user provided a numeric uplift → keep it
            if pd.notna(row["Rent Uplift ($/mo)"]):
                return row["Rent Uplift ($/mo)"]

            # If Amount is missing or zero → no uplift, avoid NaN division
            if pd.isna(row["Amount ($)"]) or row["Amount ($)"] <= 0:
                return 0

            # Otherwise use 65× rule
            return round(row["Amount ($)"] / 65)


        improvements_df["Rent Uplift ($/mo)"] = improvements_df.apply(compute_uplift, axis=1)

        improvements_df["Annual Uplift ($)"] = improvements_df["Rent Uplift ($/mo)"] * 12
        improvements_df["ROI (%)"] = (
            improvements_df["Annual Uplift ($)"] / improvements_df["Amount ($)"]
        ) * 100

        valid_df = improvements_df.dropna(subset=["Amount ($)"])
        valid_df = valid_df[valid_df["Amount ($)"] > 0]
        # Always reset improvements_list so it never carries over from a prior run
        if valid_df.empty:
            improvements_list = []
        else:
            improvements_list = valid_df.to_dict(orient="records")

        total_cost = valid_df["Amount ($)"].sum()
        weighted_roi = (
            (valid_df["Amount ($)"] * valid_df["ROI (%)"]).sum() / total_cost
            if total_cost > 0 else 0
        )

        st.success(f"📊 Weighted ROI from Capital Improvements: {weighted_roi:.2f}% (based on ${total_cost:,.0f} spent)")
        # ---- Extract first improvement for Agent PDF (simple 1-item support) ----
        #improvement_name = None
        #improvement_cost = 0.0

        #if not valid_df.empty:
            #first_row = valid_df.iloc[0]
            #improvement_name = str(first_row["Description"])
            #if pd.notna(first_row["Amount ($)"]):
                #improvement_cost = float(first_row["Amount ($)"])
        # ---- Send full list of improvements to the Agent PDF ----
        #improvements_list = valid_df.to_dict(orient="records")


# ===================================================================
# TAB 2 — REAL INSIGHTS (UNCHANGED)
# ===================================================================
with tab2:

    st.markdown("### 📊 Insights Dashboard")

    # ---------------------------------------
    # 1️⃣ BREAK-EVEN ANALYSIS
    # ---------------------------------------
    annual_cash_flows = metrics["Multi-Year Cash Flow"]
    break_even = next((i for i, v in enumerate(annual_cash_flows, start=1) if v > 0), None)

    if break_even:
        st.success(
            f"📅 Break-Even achieved in **Year {break_even}**\n"
            "( Expected based on Rent increases, Expenses and fixed Mortgage.)"
        )
    else:
        st.warning("❗ This property does not break even within the selected time horizon.")

    # ---------------------------------------
    # 2️⃣ ANNUAL INCOME ALLOCATION — Investor Preferred
    # ---------------------------------------
    st.markdown("### 🥧 Where Does the Rent Go?")
    st.subheader("📊 Annual Income Allocation")

    effective_rent = monthly_rent * (1 - vacancy_rate / 100.0)

    annual_rent = effective_rent * 12
    annual_expenses = monthly_expenses * 12
    annual_mortgage = metrics.get("Monthly Mortgage ($)", 0) * 12
    annual_cash_flow = annual_rent - annual_expenses - annual_mortgage

    labels = ["Operating Expenses", "Mortgage", "Cash Flow"]
    values = [
        max(annual_expenses, 0),
        max(annual_mortgage, 0),
        max(annual_cash_flow, 0)
    ]

    value_labels = [
        f"${annual_expenses:,.0f}",
        f"${annual_mortgage:,.0f}",
        f"${annual_cash_flow:,.0f}"
    ]

    fig_exp, ax_exp = plt.subplots(figsize=(6, 6))

    wedges, texts, autotexts = ax_exp.pie(
        values,
        labels=None,
        autopct="%1.1f%%",
        pctdistance=0.75,
        startangle=90
    )

    for i, w in enumerate(wedges):
        ang = (w.theta2 + w.theta1) / 2
        x = 1.25 * np.cos(np.deg2rad(ang))
        y = 1.25 * np.sin(np.deg2rad(ang))
        ax_exp.text(
            x, y,
            f"{value_labels[i]}\n{labels[i]}",
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold"
        )

    ax_exp.legend(
        wedges,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.1),
        frameon=False,
        ncol=3
    )

    ax_exp.axis("equal")
    st.pyplot(fig_exp)

    st.markdown(
        """
### 📝 Interpretation  
- **Operating Expenses** — property tax, insurance, maintenance, HOA  
- **Mortgage** — annual principal + interest payments  
- **Cash Flow** — annual proceeds after all costs  

_All slices shown as % of **annual** income — aligned with investor metrics._
"""
    )

    # ---------------------------------------
    # ⭐ NET CAP RATE DONUT
    # ---------------------------------------
    st.subheader("🍩 Net Cap Rate Efficiency Donut")
    st.markdown(
        """
    <div style="font-size:18px; color:white; font-weight:500; margin-top:-10px;">
        Shows how efficiently the property produces income <em>after expenses and reserves</em>.
    </div>
    """,
        unsafe_allow_html=True
    )

    NOI = max(annual_rent - annual_expenses, 0)
    reserves = max(0.05 * annual_rent, 0)
    net_noi = max(NOI - reserves, 0)
    net_cap_rate = (net_noi / purchase_price * 100) if purchase_price > 0 else 0
    non_income_portion = max(purchase_price - net_noi, 0)

    labels_cap = ["Net Operating Income (after reserves)", "Non-Income-Producing Portion"]
    values_cap = [net_noi, non_income_portion]

    if sum(values_cap) == 0:
        st.warning("⚠️ Net Cap Rate cannot be computed — values are zero.")
    else:
        fig_cap, ax_cap = plt.subplots(figsize=(6, 6))
        wedges, _ = ax_cap.pie(
            values_cap,
            wedgeprops=dict(width=0.35),
            startangle=90
        )

        # CENTER TEXT — 2 lines
        ax_cap.text(
            0, 0.05,
            f"{net_cap_rate:.2f}%",
            ha="center", va="center",
            fontsize=20,
            fontweight="bold"
        )

        ax_cap.text(
            0, -0.12,
            "earned from your property",
            ha="center", va="center",
            fontsize=11,
            color="gray"
        )

        ax_cap.axis("equal")
        st.pyplot(fig_cap)

        st.markdown(
            f"""
📘 **Meaning:** **{net_cap_rate:.2f}%** of your property's value actually comes back  
to you as *yearly income after expenses and reserves.*
        
- Net NOI: **${net_noi:,.0f}**  
- Reserves (5% of rent): **${reserves:,.0f}**
➡️ **This tells you how efficiently this property turns its value into real income.**
"""
        )

# ===================================================================
# TAB 3 — AGENT REPORT (NEW)
# ===================================================================
with tab3:
    st.subheader("📄 Agent-Branded Property Report")

    st.markdown(
        """
Use this tab to generate a **client-ready PDF** with your name, brokerage,
and personalized notes. All property numbers come from the same inputs
on the left; this tab just adds your branding.
"""
    )
    # 🔹 Agent inputs (now only visible in this tab)
    st.markdown("### 👤 Agent Information")

    agent_name = st.text_input("Agent Name")
    brokerage_name = st.text_input("Brokerage Name")
    client_name = st.text_input("Client Name")
    agent_notes = st.text_area("Notes for Client")

    # Generate Agent PDF using agent-specific fields
    agent_pdf_bytes = generate_agent_pdf(
        property_data=property_data,
        metrics=metrics,
        summary_text=summary_text,
        agent_name=agent_name or "Agent",
        brokerage_name=brokerage_name or "Your Brokerage",
        client_name=client_name or "Client",
        agent_notes=agent_notes or "",
        #improvements=valid_df.to_dict(orient="records") # ⭐ NEW
        #improvement_name=improvement_name,
        #improvement_cost=improvement_cost
        improvements_list=improvements_list  # ⭐ NEW
    )

    if agent_pdf_bytes is not None:
        st.download_button(
            label="📄 Download Agent PDF",
            data=agent_pdf_bytes,
            file_name="agent_property_report.pdf",
            mime="application/pdf",
            key="download_agent_pdf"
        )
    else:
        st.error("⚠️ Agent PDF generation failed. Please check your inputs or logs.")

    # =============================
    # ✉️ Email Agent-Branded PDF
    # =============================
    st.markdown("### 📨 Email This Client-Branded Report")
    agent_email = st.text_input(
        "Enter email address to send the report",
        placeholder="client@example.com"
    )

    if st.button("Send Agent-Branded PDF") and agent_email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", agent_email):
            st.error("❌ Please enter a valid email address.")
            st.stop()

        try:
            msg = EmailMessage()
            msg["Subject"] = "Your Personalized Real Estate Report"
            msg["From"] = os.getenv("EMAIL_USER")
            msg["To"] = agent_email
            msg.set_content(
                f"Hi {client_name},\n\n"
                "Please find attached your personalized real estate investment report.\n"
                "Let me know if you'd like to walk through the numbers together.\n\n"
                f"Best,\n{agent_name}"
            )

            agent_pdf_bytes.seek(0)
            msg.add_attachment(
                agent_pdf_bytes.read(),
                maintype='application',
                subtype='pdf',
                filename="client_real_estate_report.pdf"
            )

            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.starttls()
                smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                smtp.send_message(msg)

            st.success(f"✅ Client-Branded Report sent to {agent_email}!")

        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")
        
