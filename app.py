import base64
import datetime
import hashlib
import sqlite3
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


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


# Initialize Database and handle schema migrations safely
def init_db():
  conn = sqlite3.connect("cis_tender.db")
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS tender_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_no TEXT,
            tender_title TEXT,
            closing_date TEXT,
            opening_date TEXT,
            tenderer_name TEXT,
            amount REAL,
            verified_by TEXT,
            department TEXT,
            designation TEXT,
            timestamp TEXT,
            remarks TEXT
        )
    """)

  # Safe migration: add columns if they don't exist yet in older tables
  cursor.execute("PRAGMA table_info(tender_submissions)")
  existing_columns = [col[1] for col in cursor.fetchall()]

  if "present_status" not in existing_columns:
    cursor.execute(
        "ALTER TABLE tender_submissions ADD COLUMN present_status TEXT"
    )
  if "declarations" not in existing_columns:
    cursor.execute("ALTER TABLE tender_submissions ADD COLUMN declarations TEXT")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_tender (
            tender_no TEXT PRIMARY KEY,
            tender_title TEXT,
            closing_date TEXT,
            opening_date TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenderers_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenderer_name TEXT,
            amount TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_name TEXT UNIQUE
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)

  conn.commit()

  # Seed defaults if empty
  cursor.execute("SELECT COUNT(*) FROM active_tender")
  if cursor.fetchone()[0] == 0:
    cursor.execute(
        "INSERT INTO active_tender VALUES (?, ?, ?, ?)",
        (
            "T2027/001",
            "Supply of Clinker",
            "9 October 2026, 10:00 AM",
            "9 October 2026, 10:30 AM",
        ),
    )
    default_tenderers = [
        ("ABC Sdn. Bhd.", "1245600.00"),
        ("XYZ Trading Sdn. Bhd.", "1287500.00"),
        ("Maju Engineering Sdn. Bhd.", "1318900.00"),
        ("PQR Resources Sdn. Bhd.", "1356400.00"),
    ]
    cursor.executemany(
        "INSERT INTO tenderers_summary (tenderer_name, amount) VALUES (?, ?)",
        default_tenderers,
    )

  cursor.execute("SELECT COUNT(*) FROM departments")
  if cursor.fetchone()[0] == 0:
    default_depts = [
        ("Finance",),
        ("Procurement",),
        ("IT",),
        ("Operations",),
    ]
    cursor.executemany(
        "INSERT INTO departments (department_name) VALUES (?)", default_depts
    )

  cursor.execute("SELECT COUNT(*) FROM users")
  if cursor.fetchone()[0] == 0:
    admin_pass = make_hash("password123")
    auditor_pass = make_hash("audit123")
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?)", ("admin", admin_pass, "Admin")
    )
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?)",
        ("auditor", auditor_pass, "Auditor"),
    )

  conn.commit()
  conn.close()


init_db()

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
      conn = sqlite3.connect("cis_tender.db")
      cursor = conn.cursor()
      cursor.execute(
          "SELECT password, role FROM users WHERE username = ?", (username,)
      )
      user_record = cursor.fetchone()
      conn.close()

      if user_record and check_password(password, user_record[0]):
        st.session_state["logged_in"] = True
        st.session_state["user"] = username
        st.session_state["role"] = user_record[1]
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

conn = sqlite3.connect("cis_tender.db")
active_tender_df = pd.read_sql_query("SELECT * FROM active_tender", conn)
raw_tenderers_df = pd.read_sql_query(
    "SELECT tenderer_name, amount FROM tenderers_summary", conn
)
dept_df = pd.read_sql_query("SELECT department_name FROM departments", conn)
conn.close()

dept_list = (
    ["-- Please Select Department --"] + dept_df["department_name"].tolist()
    if not dept_df.empty
    else ["-- Please Select Department --"]
)

tenderers_df = pd.DataFrame()
if not raw_tenderers_df.empty:
  tenderers_df["Tenderer Name"] = raw_tenderers_df["tenderer_name"]
  tenderers_df["Tendered Amount (RM)"] = raw_tenderers_df["amount"].apply(
      format_rm
  )

if not active_tender_df.empty:
  t_no = active_tender_df.iloc[0]["tender_no"]
  t_title = active_tender_df.iloc[0]["tender_title"]
  t_close = active_tender_df.iloc[0]["closing_date"]
  t_open = active_tender_df.iloc[0]["opening_date"]
else:
  t_no, t_title, t_close, t_open = "", "", "", ""

# --- VIEW: COMMITTEE MEMBER (PUBLIC FORM) ---
if role == "Committee Member":
  st.markdown(
      '<div class="section-title">Section 1: Active Tender Details</div>',
      unsafe_allow_html=True,
  )
  col1, col2 = st.columns(2)
  with col1:
    st.text_input("Tender No.", value=t_no, disabled=True)
    st.text_input("Tender Closing Date & Time", value=t_close, disabled=True)
  with col2:
    st.text_input("Tender Title", value=t_title, disabled=True)
    st.text_input("Tender Opening Date & Time", value=t_open, disabled=True)

  st.markdown(
      '<div class="section-title">Section 2: Tender Submission Summary</div>',
      unsafe_allow_html=True,
  )
  if not tenderers_df.empty:
    display_df = tenderers_df.copy()
    display_df.insert(0, "No.", range(1, len(display_df) + 1))
    st.dataframe(
        display_df, hide_index=True, use_container_width=True
    )
  else:
    st.info("No tender submissions listed yet.")

  st.markdown(
      '<div class="section-title">Section 3: Committee Member Details</div>',
      unsafe_allow_html=True,
  )
  with st.form("verification_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
      full_name = st.text_input("Full Name *")
    with c2:
      department = st.selectbox("Department *", dept_list)
    with c3:
      designation = st.text_input("Designation * (e.g., Finance Manager)")

    st.markdown(
        '<div class="section-title" style="margin-top: 15px !important;">Section'
        " 4: Attendance & Verification</div>",
        unsafe_allow_html=True,
    )
    present = st.radio(
        "Were you present throughout the tender opening session? *",
        ["Yes", "No"],
    )

    st.markdown("*Electronic Declaration :")
    d1 = st.checkbox("I was present during the tender opening session")
    d2 = st.checkbox(
        "I witnessed the opening of the online tender after the official"
        " closing date and time"
    )
    d3 = st.checkbox(
        "I verified the tenderers and amounts listed in Section 2 against the"
        " online tender system"
    )
    d4 = st.checkbox(
        "I confirm that the information recorded during the tender opening is"
        " true and complete to the best of my knowledge"
    )

    remarks = st.text_area(
        "Remarks (Optional)",
        placeholder=(
            "Enter any observation or exceptions noted during the tender"
            " opening."
        ),
    )

    st.markdown(
        '<div class="section-title" style="margin-top: 15px !important;">Section'
        " 5: Electronic Acknowledgement</div>",
        unsafe_allow_html=True,
    )
    st.info(
        "By entering my full name below and submitting this form, I"
        " acknowledge that this submission, together with my company email"
        " address and the system-generated timestamp, constitutes my official"
        " attendance and verification record for this tender opening."
    )
    sig_name = st.text_input("Electronic Signature (Full Name) *")

    submitted = st.form_submit_button("Submit Verification Record")

    if submitted:
      if (
          not full_name
          or department == "-- Please Select Department --"
          or not designation
          or not sig_name
          or not (d1 and d2 and d3 and d4)
      ):
        st.error(
            "Please complete all mandatory fields, select a valid department,"
            " and check all declaration boxes."
        )
      else:
        conn = sqlite3.connect("cis_tender.db")
        cursor = conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        declarations_str = (
            f"Present Throughout: {present} | Checked Declarations: [1. Present"
            f" Session: {d1}, 2. Witnessed Opening Time: {d2}, 3. Verified"
            f" Amounts: {d3}, 4. Confirmed True: {d4}]"
        )
        cursor.execute(
            """
                    INSERT INTO tender_submissions (tender_no, tender_title, closing_date, opening_date, tenderer_name, amount, verified_by, department, designation, present_status, declarations, timestamp, remarks) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                t_no,
                t_title,
                t_close,
                t_open,
                "Multiple Tenderers",
                0.0,
                full_name,
                department,
                designation,
                present,
                declarations_str,
                timestamp,
                remarks,
            ),
        )
        conn.commit()
        conn.close()
        st.success(
            f"Verification successfully recorded and timestamped at"
            f" {timestamp}!"
        )

# --- VIEW: ADMIN PANEL ---
elif role == "Admin":
  st.markdown("### ⚙️ Administration Console")
  tab1, tab2, tab3, tab4 = st.tabs([
      "Active Tender Setup",
      "Tender Submissions",
      "Department Settings",
      "User Security",
  ])

  with tab1:
    st.markdown("#### Configure Active Tender Parameters")
    with st.form("admin_tender_form"):
      new_t_no = st.text_input("Tender No.", value=t_no)
      new_t_title = st.text_input("Tender Title", value=t_title)
      new_t_close = st.text_input("Tender Closing Date & Time", value=t_close)
      new_t_open = st.text_input("Tender Opening Date & Time", value=t_open)
      update_tender = st.form_submit_button("Update Active Tender Settings")

      if update_tender:
        conn = sqlite3.connect("cis_tender.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_tender")
        cursor.execute(
            "INSERT INTO active_tender VALUES (?, ?, ?, ?)",
            (new_t_no, new_t_title, new_t_close, new_t_open),
        )
        conn.commit()
        conn.close()
        st.success("Active tender settings updated successfully!")
        st.rerun()

  with tab2:
    st.markdown("#### Manage Tender Summary Entry List")
    if not tenderers_df.empty:
      admin_display_df = tenderers_df.copy()
      admin_display_df.insert(0, "No.", range(1, len(admin_display_df) + 1))
      st.dataframe(admin_display_df, hide_index=True, use_container_width=True)
    else:
      st.info("No tenderers listed.")

    with st.form("add_tenderer_form"):
      st.markdown("**Add Vendor Entry**")
      new_tenderer_name = st.text_input("Tenderer Company Name")
      new_amount = st.text_input("Tendered Amount (RM)")
      add_btn = st.form_submit_button("Add Vendor to Summary")

      if add_btn and new_tenderer_name and new_amount:
        conn = sqlite3.connect("cis_tender.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tenderers_summary (tenderer_name, amount) VALUES (?,"
            " ?)",
            (new_tenderer_name, new_amount),
        )
        conn.commit()
        conn.close()
        st.success(f"Added vendor '{new_tenderer_name}' successfully!")
        st.rerun()

    if st.button("Clear Complete Vendor Summary List", type="secondary"):
      conn = sqlite3.connect("cis_tender.db")
      cursor = conn.cursor()
      cursor.execute("DELETE FROM tenderers_summary")
      conn.commit()
      conn.close()
      st.warning("All vendor records wiped out.")
      st.rerun()

  with tab3:
    st.markdown("#### Department Master List Settings")
    if not dept_df.empty:
      dept_display_df = dept_df.copy()
      dept_display_df.columns = ["Department Name"]
      dept_display_df.insert(0, "No.", range(1, len(dept_display_df) + 1))
      st.dataframe(dept_display_df, use_container_width=True, hide_index=True)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
      with st.form("add_dept_form"):
        st.markdown("**Add Department**")
        new_dept = st.text_input("New Department Name")
        add_dept_btn = st.form_submit_button("Save Department")

        if add_dept_btn and new_dept:
          try:
            conn = sqlite3.connect("cis_tender.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO departments (department_name) VALUES (?)",
                (new_dept.strip(),),
            )
            conn.commit()
            conn.close()
            st.success(f"Department '{new_dept.strip()}' added successfully!")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Error: Department already exists.")

    with col_d2:
      with st.form("remove_dept_form"):
        st.markdown("**Remove Department**")
        dept_to_remove = st.selectbox(
            "Select Target Department", dept_df["department_name"].tolist()
        )
        remove_dept_btn = st.form_submit_button("Delete Department")

        if remove_dept_btn and dept_to_remove:
          conn = sqlite3.connect("cis_tender.db")
          cursor = conn.cursor()
          cursor.execute(
              "DELETE FROM departments WHERE department_name = ?",
              (dept_to_remove,),
          )
          conn.commit()
          conn.close()
          st.success(f"Department '{dept_to_remove}' removed successfully!")
          st.rerun()

  with tab4:
    st.markdown("#### System Users & Credential Management")
    conn = sqlite3.connect("cis_tender.db")
    users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
    conn.close()

    if not users_df.empty:
      users_display_df = users_df.copy()
      users_display_df.columns = ["Username", "Assigned Role"]
      users_display_df.insert(
          0, "Item No.", range(1, len(users_display_df) + 1)
      )
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
            conn = sqlite3.connect("cis_tender.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hashed_pw, selected_user),
            )
            conn.commit()
            conn.close()
            st.success(
                f"Password profile updated for username '{selected_user}'!"
            )
            st.rerun()
          else:
            st.error("Please enter a valid new password string.")

# --- VIEW: AUDITOR DASHBOARD ---
elif role == "Auditor":
  st.markdown("### 📊 Internal Audit & Verification Trail Portal")

  conn = sqlite3.connect("cis_tender.db")
  raw_audit_df = pd.read_sql_query("SELECT * FROM tender_submissions", conn)
  conn.close()

  if not raw_audit_df.empty:
    logo_html = ""
    if logo_data_uri:
      logo_html = f'<img src="{logo_data_uri}" style="max-height: 55px; max-width: 140px; object-fit: contain; display: inline-block; vertical-align: middle;" alt="CIS Logo">'

    html_rows = ""
    for idx, row in raw_audit_df.iterrows():
      p_status = (
          row["present_status"]
          if "present_status" in raw_audit_df.columns
          and pd.notna(row["present_status"])
          else "Yes"
      )
      decls = (
          row["declarations"]
          if "declarations" in raw_audit_df.columns
          and pd.notna(row["declarations"])
          else "All declarations confirmed"
      )

      html_rows += f"""
            <tr>
                <td>{idx + 1}</td>
                <td>{row['tender_no']} - {row['tender_title']}</td>
                <td>{row['verified_by']}<br><small>{row['department']} / {row['designation']}</small></td>
                <td><b>Present:</b> {p_status}<br><small>{decls}</small></td>
                <td>{row['timestamp']}</td>
                <td>{row['remarks'] if pd.notna(row['remarks']) and row['remarks'] else '-'}</td>
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
                        <td style="width: 25%;">
                            {logo_html}
                        </td>
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
    audit_df["ID"] = raw_audit_df["id"]
    audit_df["Tender No."] = raw_audit_df["tender_no"]
    audit_df["Tender Title"] = raw_audit_df["tender_title"]
    audit_df["Verified By"] = raw_audit_df["verified_by"]
    audit_df["Department"] = raw_audit_df["department"]
    audit_df["Designation"] = raw_audit_df["designation"]
    audit_df["Present"] = (
        raw_audit_df["present_status"]
        if "present_status" in raw_audit_df.columns
        else "Yes"
    )
    audit_df["Declarations Checked"] = (
        raw_audit_df["declarations"]
        if "declarations" in raw_audit_df.columns
        else "-"
    )
    audit_df["Timestamp"] = raw_audit_df["timestamp"]
    audit_df["Remarks"] = raw_audit_df["remarks"]

    st.dataframe(audit_df, use_container_width=True, hide_index=True)

    st.markdown("### Audit Trail Record Management")
    col_del1, col_del2 = st.columns(2)

    with col_del1:
      with st.form("delete_audit_form"):
        st.markdown("**Remove Specific Record**")
        record_options = {
            f"ID {row['id']} | {row['verified_by']} ({row['department']}) - {row['timestamp']}": row[
                "id"
            ]
            for _, row in raw_audit_df.iterrows()
        }
        selected_label = st.selectbox(
            "Select Entry", list(record_options.keys())
        )
        delete_record_btn = st.form_submit_button(
            "🗑️ Remove Selected Record"
        )

        if delete_record_btn and selected_label:
          target_id = record_options[selected_label]
          conn = sqlite3.connect("cis_tender.db")
          cursor = conn.cursor()
          cursor.execute(
              "DELETE FROM tender_submissions WHERE id = ?", (target_id,)
          )
          conn.commit()
          conn.close()
          st.success(f"Removed audit record (ID: {target_id}).")
          st.rerun()

    with col_del2:
      with st.form("clear_all_audit_form"):
        st.markdown("**Clear Entire Audit Trail**")
        st.write(
            "⚠️ This action will delete all logged verification records."
        )
        confirm_clear = st.checkbox(
            "I confirm that I want to delete all audit records"
        )
        clear_all_btn = st.form_submit_button("⚠️ Clear All Audit Records")

        if clear_all_btn:
          if confirm_clear:
            conn = sqlite3.connect("cis_tender.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tender_submissions")
            conn.commit()
            conn.close()
            st.warning("All audit verification records have been cleared.")
            st.rerun()
          else:
            st.error(
                "Please check the confirmation box before clearing all records."
            )
  else:
    st.info("No audit verification entries logged yet.")
