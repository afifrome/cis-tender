import os
import base64
import datetime
import hashlib
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

# --- SUPABASE CLIENT CONNECTION ---
SUPABASE_URL = "https://wswwovvogioefktgwazk.supabase.co"
SUPABASE_KEY = st.secrets["supabase"]["key"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()


# Hash passwords securely
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_password(password, hashed_password):
    return make_hash(password) == hashed_password


# Format amount to RM currency style
def format_rm(val):
    try:
        clean_val = str(val).replace("RM", "").replace(",", "").strip()
        f_val = float(clean_val)
        return f"RM {f_val:,.2f}"
    except ValueError:
        return val


# Convert local image to Base64
def get_base64_image(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        ext = file_path.split(".")[-1].lower()
        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
        encoded = base64.b64encode(data).decode()
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None


# Fetch data helpers from Supabase with automatic column mapping & error handling
def fetch_active_tenders():
    try:
        res = supabase.table("active_tenders").select("*").execute()
    except Exception:
        return pd.DataFrame(columns=["tender_no", "tender_title", "closing_date", "opening_date"])
        
    if not res.data:
        return pd.DataFrame(columns=["tender_no", "tender_title", "closing_date", "opening_date"])
    
    df = pd.DataFrame(res.data)
    col_map = {}
    for col in df.columns:
        c_lower = col.lower()
        if "no" in c_lower or "number" in c_lower:
            col_map[col] = "tender_no"
        elif "title" in c_lower or "name" in c_lower:
            col_map[col] = "tender_title"
        elif "close" in c_lower:
            col_map[col] = "closing_date"
        elif "open" in c_lower:
            col_map[col] = "opening_date"
            
    df = df.rename(columns=col_map)
    
    if "tender_no" not in df.columns:
        df["tender_no"] = [f"T2027/00{i+1}" for i in range(len(df))]
    if "tender_title" not in df.columns:
        df["tender_title"] = [f"Tender Event {i+1}" for i in range(len(df))]
    if "closing_date" not in df.columns:
        df["closing_date"] = "9 October 2026, 10:00 AM"
    if "opening_date" not in df.columns:
        df["opening_date"] = "9 October 2026, 10:30 AM"
        
    return df

def fetch_departments():
    return pd.DataFrame([
        {"department_name": "Finance"},
        {"department_name": "Procurement"},
        {"department_name": "IT"},
        {"department_name": "Operations"}
    ])

def fetch_tenderers_summary(tender_no=None):
    try:
        query = supabase.table("tenderers_summary").select("*")
        if tender_no:
            query = query.eq("tender_no", tender_no)
        res = query.execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["id", "tender_no", "tenderer_name", "amount"])
    except Exception:
        try:
            query = supabase.table("tenderer_summary").select("*")
            if tender_no:
                query = query.eq("tender_no", tender_no)
            res = query.execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["id", "tender_no", "tenderer_name", "amount"])
        except Exception:
            return pd.DataFrame(columns=["id", "tender_no", "tenderer_name", "amount"])

def fetch_submissions():
    try:
        res = supabase.table("submissions").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


st.set_page_config(
    page_title="CIS Tender Verification & Opening Portal",
    page_icon="🏗️",
    layout="wide",
)

logo_data_uri = get_base64_image("cis_logo.jpg")
if not logo_data_uri:
    logo_data_uri = get_base64_image("cis_logo.png")

st.markdown(
    """
    <style>
    [data-testid="InputInstructions"] { display: none !important; }
    .stApp { background-color: #0e1117; color: #e2e8f0; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; font-weight: 700 !important; }
    p, label, span { font-size: 17px !important; font-weight: 600 !important; color: #cbd5e1 !important; }
    .section-title {
        font-size: 20px !important; font-weight: 700 !important; color: #ffffff !important;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 12px 18px; border-radius: 8px; border-left: 5px solid #3b82f6;
        margin-top: 35px !important; margin-bottom: 20px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); letter-spacing: 0.5px;
    }
    .corporate-header {
        background: linear-gradient(135deg, #1a365d 0%, #0f172a 100%);
        padding: 25px 30px; border-radius: 10px; color: white; margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4); border-left: 6px solid #f39c12;
        display: flex; align-items: center; gap: 25px; border: 1px solid #2d3748;
    }
    .corporate-logo { max-height: 75px; max-width: 160px; object-fit: contain; background: white; padding: 6px; border-radius: 6px; }
    .corporate-header-text h1 { color: #ffffff !important; margin: 0; font-size: 26px !important; font-weight: 700 !important; }
    .corporate-header-text p { margin: 6px 0 0 0; color: #94a3b8 !important; font-size: 15px !important; font-weight: 500 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

header_logo_html = (
    f'<img src="{logo_data_uri}" class="corporate-logo" alt="CIS Logo">'
    if logo_data_uri
    else ""
)
st.markdown(
    f"""
    <div class="corporate-header">
        {header_logo_html}
        <div class="corporate-header-text">
            <h1>CEMENT INDUSTRIES (SABAH) SDN. BHD.</h1>
            <p>Sepanggar Industrial Estate &bull; Electronic Tender Opening Attendance & Verification System</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = "Committee Member"

st.sidebar.header("Portal Access Control")

if not st.session_state["logged_in"]:
    st.sidebar.markdown(
        "**Public Portal Mode**\nCommittee Member Verification Access."
    )
    st.sidebar.markdown("---")
    with st.sidebar.form("login_form"):
        st.subheader("Staff Secure Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Authenticate")

        if login_btn:
            try:
                res = supabase.table("users").select("password, role").eq("username", username).execute()
                user_record = res.data[0] if res.data else None
            except Exception:
                user_record = None

            if user_record and check_password(password, user_record["password"]):
                st.session_state["logged_in"] = True
                st.session_state["user"] = username
                st.session_state["role"] = user_record["role"]
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

    role = "Committee Member"
else:
    st.sidebar.success(
        f"Authenticated User:\n**{st.session_state['user']}**"
        f" \n*(Role: {st.session_state['role']})*"
    )
    role = st.session_state["role"]
    st.sidebar.markdown("---")
    if st.sidebar.button("Sign Out", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        st.session_state["role"] = "Committee Member"
        st.rerun()

active_tenders_df = fetch_active_tenders()
dept_df = fetch_departments()

dept_list = (
    ["-- Please Select Department --"] + dept_df["department_name"].tolist()
    if not dept_df.empty and "department_name" in dept_df.columns
    else ["-- Please Select Department --"]
)

# --- VIEW: COMMITTEE MEMBER ---
if role == "Committee Member":
    if active_tenders_df.empty:
        st.info("No active tenders currently available.")
    else:
        st.markdown(
            f"### 📌 Active Tender Opening Sessions ({len(active_tenders_df)} Concurrent Events)"
        )
        st.markdown(
            "Multiple tender events are scheduled for opening. Please select the respective tab below to review details, view submissions, and submit your attendance verification."
        )

        tab_titles = [
            f"📌 {row['tender_no']} - {row['tender_title']}"
            for _, row in active_tenders_df.iterrows()
        ]
        tabs = st.tabs(tab_titles)

        for idx, tab in enumerate(tabs):
            tender_row = active_tenders_df.iloc[idx]
            t_no = tender_row["tender_no"]
            t_title = tender_row["tender_title"]
            t_close = tender_row["closing_date"]
            t_open = tender_row["opening_date"]

            with tab:
                st.markdown(
                    f'<div class="section-title">Section 1: Active Tender Details ({t_no})</div>',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Tender No.", value=t_no, disabled=True, key=f"no_{t_no}")
                    st.text_input("Tender Closing Date & Time", value=t_close, disabled=True, key=f"close_{t_no}")
                with col2:
                    st.text_input("Tender Title", value=t_title, disabled=True, key=f"title_{t_no}")
                    st.text_input("Tender Opening Date & Time", value=t_open, disabled=True, key=f"open_{t_no}")

                st.markdown(
                    f'<div class="section-title">Section 2: Tender Submission Summary ({t_no})</div>',
                    unsafe_allow_html=True,
                )
                
                raw_t_summary = fetch_tenderers_summary(t_no)
                tenderers_df = pd.DataFrame()
                if not raw_t_summary.empty:
                    # Safe mapping for summary columns
                    c_name_col = next((c for c in raw_t_summary.columns if "name" in c.lower() or "tenderer" in c.lower()), "tenderer_name")
                    c_amt_col = next((c for c in raw_t_summary.columns if "amount" in c.lower() or "price" in c.lower()), "amount")
                    
                    tenderers_df["Tenderer Name"] = raw_t_summary[c_name_col]
                    tenderers_df["Tendered Amount (RM)"] = raw_t_summary[c_amt_col].apply(format_rm)

                if not tenderers_df.empty:
                    display_df = tenderers_df.copy()
                    display_df.insert(0, "No.", range(1, len(display_df) + 1))
                    st.dataframe(
                        display_df, hide_index=True, use_container_width=True
                    )
                else:
                    st.info(f"No tender submissions listed yet for {t_no}.")

                st.markdown(
                    f'<div class="section-title">Section 3: Committee Member Details ({t_no})</div>',
                    unsafe_allow_html=True,
                )
                with st.form(key=f"verification_form_{t_no}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        full_name = st.text_input("Full Name *", key=f"name_{t_no}")
                    with c2:
                        department = st.selectbox("Department *", dept_list, key=f"dept_{t_no}")
                    with c3:
                        designation = st.text_input("Designation * (e.g., Finance Manager)", key=f"desig_{t_no}")

                    st.markdown(
                        '<div class="section-title" style="margin-top: 15px !important;">Section 4: Attendance & Verification</div>',
                        unsafe_allow_html=True,
                    )
                    present = st.radio(
                        "Were you present throughout the tender opening session? *",
                        ["Yes", "No"],
                        key=f"present_{t_no}"
                    )

                    st.markdown("*Electronic Declaration :")
                    d1 = st.checkbox("I was present during the tender opening session", key=f"d1_{t_no}")
                    d2 = st.checkbox(
                        "I witnessed the opening of the online tender after the official closing date and time",
                        key=f"d2_{t_no}"
                    )
                    d3 = st.checkbox(
                        "I verified the tenderers and amounts listed in Section 2 against the online tender system",
                        key=f"d3_{t_no}"
                    )
                    d4 = st.checkbox(
                        "I confirm that the information recorded during the tender opening is true and complete to the best of my knowledge",
                        key=f"d4_{t_no}"
                    )

                    remarks = st.text_area(
                        "Remarks (Optional)",
                        placeholder="Enter any observation or exceptions noted during the tender opening.",
                        key=f"remarks_{t_no}"
                    )

                    st.markdown(
                        '<div class="section-title" style="margin-top: 15px !important;">Section 5: Electronic Acknowledgement</div>',
                        unsafe_allow_html=True,
                    )
                    st.info(
                        "By entering my full name below and submitting this form, I acknowledge that this submission, together with my company email address and the system-generated timestamp, constitutes my official attendance and verification record for this tender opening."
                    )
                    sig_name = st.text_input("Electronic Signature (Full Name) *", key=f"sig_{t_no}")

                    submitted = st.form_submit_button(f"Submit Verification Record for {t_no}")

                    if submitted:
                        if (
                            not full_name
                            or department == "-- Please Select Department --"
                            or not designation
                            or not sig_name
                            or not (d1 and d2 and d3 and d4)
                        ):
                            st.error(
                                "Please complete all mandatory fields, select a valid department, and check all declaration boxes."
                            )
                        else:
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            declarations_str = (
                                f"Present Throughout: {present} | Checked Declarations: [1. Present Session: {d1}, 2. Witnessed Opening Time: {d2}, 3. Verified Amounts: {d3}, 4. Confirmed True: {d4}]"
                            )
                        try:
                                # Keep the payload strictly minimal based on what Supabase has
                                payload = {
                                    "tender_no": str(t_no),
                                    "verified_by": str(full_name),
                                    "department": str(department),
                                    "designation": str(designation),
                                    "present_status": str(present),
                                    "timestamp": str(timestamp),
                                    "remarks": str(remarks) if remarks else "No remarks"
                                }
                                
                                supabase.table("submissions").insert(payload).execute()
                                st.success(
                                    f"Verification successfully recorded for {t_no} and timestamped at {timestamp}!"
                                )
                            except Exception as e:
                                st.error(f"Supabase Insertion Error Details: {e}")

# --- VIEW: ADMIN PANEL ---
elif role == "Admin":
    st.markdown("### ⚙ Administration Console")
    tab1, tab2, tab3, tab4 = st.tabs([
        "Active Tenders Setup",
        "Tender Submissions Summary",
        "Department Settings",
        "User Security"
    ])

    with tab1:
        st.markdown("#### Configure Active Tender Events")
        if not active_tenders_df.empty:
            st.dataframe(active_tenders_df, use_container_width=True, hide_index=True)

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            with st.form("add_new_active_tender_form"):
                st.markdown("**Add New Concurrent Tender Event**")
                new_t_no = st.text_input("Tender No. (e.g., T2027/003)")
                new_t_title = st.text_input("Tender Title")
                new_t_close = st.text_input("Tender Closing Date & Time", value="9 October 2026, 10:00 AM")
                new_t_open = st.text_input("Tender Opening Date & Time", value="9 October 2026, 10:30 AM")
                add_tender_btn = st.form_submit_button("Add Active Tender")

                if add_tender_btn and new_t_no and new_t_title:
                    try:
                        payload = {
                            "tender_no": new_t_no.strip(),
                            "tender_title": new_t_title.strip(),
                            "closing_date": new_t_close,
                            "opening_date": new_t_open
                        }
                        supabase.table("active_tenders").insert(payload).execute()
                        st.success(f"Tender {new_t_no} added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding tender: {e}")

        with col_a2:
            with st.form("remove_active_tender_form"):
                st.markdown("**Remove Active Tender Event**")
                tender_to_remove = st.selectbox(
                    "Select Tender No. to Remove", active_tenders_df["tender_no"].tolist() if not active_tenders_df.empty else []
                )
                remove_tender_btn = st.form_submit_button("Delete Tender Event")

                if remove_tender_btn and tender_to_remove:
                    supabase.table("active_tenders").delete().eq("tender_no", tender_to_remove).execute()
                    supabase.table("tenderers_summary").delete().eq("tender_no", tender_to_remove).execute()
                    st.success(f"Tender {tender_to_remove} removed successfully!")
                    st.rerun()

    with tab2:
        st.markdown("#### Manage Vendor Summary Entries by Tender")
        all_summary_df = fetch_tenderers_summary()

        if not all_summary_df.empty:
            st.dataframe(all_summary_df, hide_index=True, use_container_width=True)
        else:
            st.info("No vendor entries listed.")

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            with st.form("add_vendor_entry_form"):
                st.markdown("**Add Vendor Entry**")
                target_tender = st.selectbox(
                    "Select Tender No.", active_tenders_df["tender_no"].tolist() if not active_tenders_df.empty else []
                )
                vendor_name = st.text_input("Tenderer Company Name")
                vendor_amount = st.text_input("Tendered Amount (RM)")
                add_vendor_btn = st.form_submit_button("Add Vendor Entry")

                if add_vendor_btn and target_tender and vendor_name and vendor_amount:
                    payload = {
                        "tender_no": target_tender,
                        "tenderer_name": vendor_name,
                        "amount": vendor_amount
                    }
                    supabase.table("tenderers_summary").insert(payload).execute()
                    st.success(f"Added vendor '{vendor_name}' to tender {target_tender}!")
                    st.rerun()

        with col_v2:
            with st.form("delete_vendor_entry_form"):
                st.markdown("**Remove Specific Vendor Entry**")
                vendor_options = {
                    f"ID: {row.get('id')} | Tender: {row.get('tender_no')} | Company: {row.get('tenderer_name')} (RM {row.get('amount')})": row.get('id')
                    for _, row in all_summary_df.iterrows()
                } if not all_summary_df.empty else {}
                
                selected_vendor_label = st.selectbox(
                    "Select Company Entry to Delete", list(vendor_options.keys()) if vendor_options else ["No entries available"]
                )
                delete_vendor_btn = st.form_submit_button("🗑️ Delete Company Entry")

                if delete_vendor_btn and selected_vendor_label and selected_vendor_label != "No entries available":
                    target_id = vendor_options[selected_vendor_label]
                    supabase.table("tenderers_summary").delete().eq("id", target_id).execute()
                    st.success("Selected vendor company entry removed successfully!")
                    st.rerun()

    with tab3:
        st.markdown("#### Department Master List Settings")
        if not dept_df.empty:
            dept_display_df = dept_df.copy()
            dept_display_df.insert(0, "No.", range(1, len(dept_display_df) + 1))
            st.dataframe(dept_display_df, use_container_width=True, hide_index=True)
        st.info("Departments are managed centrally.")

    with tab4:
        st.markdown("#### System Users & Credential Management")
        try:
            users_res = supabase.table("users").select("username, role").execute()
            users_df = pd.DataFrame(users_res.data) if users_res.data else pd.DataFrame()
        except Exception:
            users_df = pd.DataFrame()

        if not users_df.empty:
            users_display_df = users_df.copy()
            users_display_df.columns = ["Username", "Assigned Role"]
            users_display_df.insert(0, "Item No.", range(1, len(users_display_df) + 1))
            st.dataframe(users_display_df, use_container_width=True, hide_index=True)

            with st.form("edit_user_form"):
                st.markdown("**Reset User Password**")
                selected_user = st.selectbox(
                    "Select Account Username", users_df["username"].tolist()
                )
                new_password = st.text_input("New Secure Password", type="password")
                update_pass_btn = st.form_submit_button("Update Password Credentials")

                if update_pass_btn:
                    if new_password:
                        hashed_pw = make_hash(new_password)
                        supabase.table("users").update({"password": hashed_pw}).eq("username", selected_user).execute()
                        st.success(f"Password profile updated for username '{selected_user}'!")
                        st.rerun()
                    else:
                        st.error("Please enter a valid new password string.")

# --- VIEW: AUDITOR DASHBOARD ---
elif role == "Auditor":
    st.markdown("### 📊 Internal Audit & Verification Trail Portal")

    raw_audit_df = fetch_submissions()

    if not raw_audit_df.empty:
        logo_html = ""
        if logo_data_uri:
            logo_html = f'<img src="{logo_data_uri}" style="max-height: 55px; max-width: 140px; object-fit: contain; display: inline-block; vertical-align: middle;" alt="CIS Logo">'

        html_rows = ""
        for idx, row in raw_audit_df.iterrows():
            p_status = row.get("present_status", "Yes")
            decls = row.get("declarations", "All declarations confirmed")

            html_rows += f"""
                <tr>
                    <td>{idx + 1}</td>
                    <td><b>{row.get('tender_no')}</b><br>{row.get('tender_title')}</td>
                    <td>{row.get('verified_by')}<br><small>{row.get('department')} / {row.get('designation')}</small></td>
                    <td><b>Present:</b> {p_status}<br><small>{decls}</small></td>
                    <td>{row.get('timestamp')}</td>
                    <td>{row.get('remarks') if row.get('remarks') else '-'}</td>
                </tr>
                """

        current_gen_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print_html = f"""
        <html>
        <head>
            <title>CIS Tender Audit Verification Report</title>
            <style>
                @page {{ size: landscape; margin: 10mm; }}
                body {{ font-family: Arial, sans-serif; color: #333; margin: 0; background-color: transparent; text-align: left; }}
                .toolbar {{ display: flex; justify-content: flex-end; margin-bottom: 10px; }}
                .report-container {{ display: none; }}
                @media print {{
                    .toolbar {{ display: none; }}
                    .report-container {{ display: block !important; }}
                }}
                .header-table {{ width: 100%; border-collapse: collapse; border: none; margin-bottom: 15px; border-bottom: 2px solid #1f4068; padding-bottom: 8px; }}
                .header-table td {{ border: none; padding: 0; vertical-align: middle; }}
                .header-title-box {{ text-align: right; }}
                .header-title-box h2 {{ margin: 0; color: #1f4068; font-size: 16px; font-weight: bold; letter-spacing: 0.5px; }}
                .header-title-box p {{ margin: 3px 0 0 0; font-size: 11px; color: #444; font-weight: bold; text-transform: uppercase; }}
                .doc-ref {{ font-size: 10px; color: #555; text-align: right; margin-top: 4px; }}
                table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
                table.data-table th, table.data-table td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }}
                table.data-table th {{ background-color: #1f4068; color: white; }}
                table.data-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .footer {{ margin-top: 20px; font-size: 10px; text-align: right; color: #777; }}
                .print-btn {{ background-color: #1f4068; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
                .print-btn:hover {{ background-color: #163254; }}
            </style>
        </head>
        <body>
            <div class="toolbar">
                <button class="print-btn" onclick="window.print();">🖨️ Print / Save Report as PDF (Landscape)</button>
            </div>
            
            <div class="report-container">
                <table class="header-table">
                    <tr>
                        <td style="width: 25%;">{logo_html}</td>
                        <td style="width: 75%;" class="header-title-box">
                            <h2>CEMENT INDUSTRIES (SABAH) SDN. BHD.</h2>
                            <p>SEPANGGAR INDUSTRIAL ESTATE &bull; OFFICIAL TENDER AUDIT VERIFICATION REGISTER</p>
                            <div class="doc-ref">Document Ref: CIS/OTC/AUD/2026/10 | Generated: {current_gen_time}</div>
                        </td>
                    </tr>
                </table>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="width: 4%;">No.</th>
                            <th style="width: 18%;">Tender Details</th>
                            <th style="width: 20%;">Committee Member Info</th>
                            <th style="width: 33%;">Attendance & Declarations Chosen</th>
                            <th style="width: 13%;">Timestamp</th>
                            <th style="width: 12%;">Remarks</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_rows}
                    </tbody>
                </table>
                <div class="footer">
                    <p>This is a system-generated detailed compliance report from the CIS Electronic Tender Portal.</p>
                </div>
            </div>
        </body>
        </html>
        """

        components.html(print_html, height=52)

        audit_df = pd.DataFrame()
        audit_df["ID"] = raw_audit_df.get("id")
        audit_df["Tender No."] = raw_audit_df.get("tender_no")
        audit_df["Tender Title"] = raw_audit_df.get("tender_title")
        audit_df["Verified By"] = raw_audit_df.get("verified_by")
        audit_df["Department"] = raw_audit_df.get("department")
        audit_df["Designation"] = raw_audit_df.get("designation")
        audit_df["Present"] = raw_audit_df.get("present_status", "Yes")
        audit_df["Declarations Checked"] = raw_audit_df.get("declarations", "-")
        audit_df["Timestamp"] = raw_audit_df.get("timestamp")
        audit_df["Remarks"] = raw_audit_df.get("remarks")

        st.dataframe(raw_audit_df, use_container_width=True, hide_index=True)

        st.markdown("### Audit Trail Record Management")
        col_del1, col_del2 = st.columns(2)

        with col_del1:
            with st.form("delete_audit_form"):
                st.markdown("**Remove Specific Record**")
                record_options = {
                    f"ID {row.get('id')} | Tender: {row.get('tender_no')} | {row.get('verified_by')} ({row.get('department')}) - {row.get('timestamp')}": row.get("id")
                    for _, row in raw_audit_df.iterrows()
                } if not raw_audit_df.empty else {}
                
                selected_label = st.selectbox(
                    "Select Entry", list(record_options.keys()) if record_options else ["No records available"]
                )
                delete_record_btn = st.form_submit_button("🗑️ Remove Selected Record")

                if delete_record_btn and selected_label and selected_label != "No records available":
                    target_id = record_options[selected_label]
                    supabase.table("submissions").delete().eq("id", target_id).execute()
                    st.success(f"Removed audit record (ID: {target_id}).")
                    st.rerun()

        with col_del2:
            with st.form("clear_all_audit_form"):
                st.markdown("**Clear Entire Audit Trail**")
                confirm_clear = st.checkbox("I confirm that I want to delete all audit records")
                clear_all_btn = st.form_submit_button("⚠️ Clear All Audit Records")

                if clear_all_btn:
                    if confirm_clear:
                        supabase.table("submissions").delete().gt("id", 0).execute()
                        st.warning("All audit verification records have been cleared.")
                        st.rerun()
                    else:
                        st.error("Please check the confirmation box before clearing all records.")
    else:
        st.info("No audit verification entries logged yet.")
