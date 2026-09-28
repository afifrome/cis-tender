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


# Format amount to RM currency style (e.g. 1245800 -> RM 1,245,800.00)
def format_rm(val):
  try:
    clean_val = str(val).replace("RM", "").replace(",", "").strip()
    f_val = float(clean_val)
    return f"RM {f_val:,.2f}"
  except ValueError:
    return val


# Convert local image to Base64 with proper MIME type handling
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


# Initialize Database for Tender Management with Users Table
def init_db():
  conn = sqlite3.connect("cis_tender.db")
  cursor = conn.cursor()

  # Submissions table
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

  # Active Tender configuration table
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_tender (
            tender_no TEXT PRIMARY KEY,
            tender_title TEXT,
            closing_date TEXT,
            opening_date TEXT
        )
    """)

  # Tenderers summary table
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenderers_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenderer_name TEXT,
            amount TEXT
        )
    """)

  # Departments table
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_name TEXT UNIQUE
        )
    """)

  # Users table for secure RBAC
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)

  conn.commit()

  # Seed default active tender if empty
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

  # Seed default departments if empty
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
    conn.commit()

  # Seed default admin user if empty (username: admin, password: password123)
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

# --- LOAD DEDICATED REPORT LOGO AS BASE64 ---
logo_data_uri = get_base64_image("cis_logo.jpg")
if not logo_data_uri:
  logo_data_uri = get_base64_image("cis_logo.png")

# --- PROFESSIONAL STYLING (LARGER & BOLD TEXT, NO BACKGROUND IMAGE) ---
bg_css = """
    .stApp {
        background-color: #0e1117;
        color: #f8f9fa;
        font-size: 16px;
    }
    """

st.markdown(
    f"""
    <style>
    {bg_css}
    
    /* Make all headings bigger and bold */
    h1, h2, h3, h4, h5, h6 {{
        color: #ffffff !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700 !important;
    }}
    
    h3 {{
        font-size: 22px !important;
        margin-top: 15px !important;
    }}
    
    /* Make general body text, labels, and widget texts larger & bold */
    p, label, span, div {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #f1f3f5 !important;
    }}
    
    /* Input field text styling */
    input, textarea {{
        font-size: 16px !important;
        font-weight: 600 !important;
    }}

    .corporate-header {{
        background: linear-gradient(90deg, rgba(31, 64, 104, 0.95) 0%, rgba(22, 36, 71, 0.95) 100%);
        padding: 20px 25px;
        border-radius: 8px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        border-left: 5px solid #f39c12;
        display: flex;
        align-items: center;
        gap: 20px;
    }}
    .corporate-logo {{
        max-height: 70px;
        max-width: 150px;
        object-fit: contain;
        background: white;
        padding: 5px;
        border-radius: 4px;
        mix-blend-mode: multiply;
    }}
    .corporate-header-text h1 {{
        color: #ffffff !important;
        margin: 0;
        font-size: 26px !important;
        font-weight: 700 !important;
    }}
    .corporate-header-text p {{
        margin: 5px 0 0 0;
        color: #e2e8f0 !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- CORPORATE BANNER HEADER WITH LOGO ON LEFT ---
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
            <p>Sepanggar Industrial Estate | Electronic Tender Opening Attendance & Verification System</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Session state handling for authentication
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
  st.session_state["user"] = None
  st.session_state["role"] = "Committee Member"  # Default public view

# Sidebar Access Control
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

# Fetch active tender details, tenderers, and departments from database
conn = sqlite3.connect("cis_tender.db")
active_tender_df = pd.read_sql_query("SELECT * FROM active_tender", conn)
raw_tenderers_df = pd.read_sql_query(
    "SELECT tenderer_name, amount FROM tenderers_summary", conn
)
dept_df = pd.read_sql_query("SELECT department_name FROM departments", conn)
conn.close()

# Prepare department options list for selectboxes
dept_list = (
    ["-- Please Select Department --"] + dept_df["department_name"].tolist()
    if not dept_df.empty
    else ["-- Please Select Department --"]
)

# Format dataframe values for visual presentation
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
  st.markdown("### Section 1: Active Tender Details")
  col1, col2 = st.columns(2)
  with col1:
    st.text_input("Tender No.", value=t_no, disabled=True)
    st.text_input("Tender Closing Date & Time", value=t_close, disabled=True)
  with col2:
    st.text_input("Tender Title", value=t_title, disabled=True)
    st.text_input("Tender Opening Date & Time", value=t_open, disabled=True)

  st.markdown("### Section 2: Tender Submission Summary")
  if not tenderers_df.empty:
    display_df = tenderers_df.copy()
    display_df.insert(0, "No.", range(1, len(display_df) + 1))
    st.dataframe(display_df, hide_index=True, use_container_width=True)
  else:
    st.info("No tender submissions listed yet.")

  st.markdown("### Section 3: Committee Member Details")
  with st.form("verification_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
      full_name = st.text_input("Full Name *")
    with c2:
      department = st.selectbox("Department *", dept_list)
    with c3:
      designation = st.text_input("Designation * (e.g., Finance Manager)")

    st.markdown("### Section 4: Attendance & Verification")
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

    st.markdown("### Section 5: Electronic Acknowledgement")
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
        cursor.execute(
            """
                    INSERT INTO tender_submissions (tender_no, tender_title, closing_date, opening_date, tenderer_name, amount, verified_by, department, designation, timestamp, remarks) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
      st.dataframe(
          admin_display_df, hide_index=True, use_container_width=True
      )
    else:
      st.info("No tenderers listed.")

    with st.form("add_tenderer_form"):
      st.markdown("**Add Vendor Entry**")
      new_tenderer_name = st.text_input("Tenderer Company Name")
      new_amount = st.text_input(
          "Tendered Amount (RM) - e.g. 1245800.00 or 1245800"
      )
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
      logo_html = f'<div style="text-align: center; margin-bottom: 15px;"><img src="{logo_data_uri}" style="max-height: 80px; max-width: 220px; object-fit: contain; mix-blend-mode: multiply; display: inline-block;" alt="CIS Logo"></div>'

    html_rows = ""
    for idx, row in raw_audit_df.iterrows():
      html_rows += f"""
            <tr>
                <td>{idx + 1}</td>
                <td>{row['tender_no']} - {row['tender_title']}</td>
                <td>{row['verified_by']} ({row['department']})</td>
                <td>{row['designation']}</td>
                <td>{row['timestamp']}</td>
                <td>{row['remarks'] if row['remarks'] else '-'}</td>
            </tr>
            """

    print_html = f"""
        <html>
        <head>
            <title>CIS Tender Audit Verification Report</title>
            <style>
                @page {{
                    margin: 15mm;
                }}
                body {{ 
                    font-family: Arial, sans-serif; 
                    color: #333; 
                    margin: 0; 
                    background-color: transparent; 
                    text-align: left; 
                }}
                .toolbar {{
                    display: flex;
                    justify-content: flex-end;
                    margin-bottom: 10px;
                }}
                .report-container {{
                    display: none;
                }}
                @media print {{
                    .toolbar {{ display: none; }}
                    .report-container {{ display: block !important; }}
                }}
                .header {{ 
                    text-align: center; 
                    margin: 0 auto 25px auto; 
                    border-bottom: 2px solid #1f4068; 
                    padding-bottom: 15px; 
                    width: 100%; 
                }}
                .header h2 {{ 
                    margin: 5px auto 0 auto; 
                    color: #1f4068; 
                    font-size: 20px; 
                    text-align: center; 
                }}
                .header p {{ 
                    margin: 4px auto; 
                    font-size: 13px; 
                    color: #555; 
                    text-align: center; 
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin-top: 15px; 
                    font-size: 12px; 
                }}
                th, td {{ 
                    border: 1px solid #ddd; 
                    padding: 8px; 
                    text-align: left; 
                }}
                th {{ 
                    background-color: #1f4068; 
                    color: white; 
                }}
                tr:nth-child(even) {{ 
                    background-color: #f9f9f9; 
                }}
                .footer {{ 
                    margin-top: 30px; 
                    font-size: 11px; 
                    text-align: right; 
                    color: #777; 
                }}
                .print-btn {{ 
                    background-color: #1f4068; 
                    color: white; 
                    padding: 10px 20px; 
                    border: none; 
                    border-radius: 4px; 
                    cursor: pointer; 
                    font-size: 14px; 
                    font-weight: bold;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }}
                .print-btn:hover {{ 
                    background-color: #163254; 
                }}
            </style>
        </head>
        <body>
            <div class="toolbar">
                <button class="print-btn" onclick="window.print();">🖨️ Print / Save Report as PDF</button>
            </div>
            
            <div class="report-container">
                <div class="header">
                    {logo_html}
                    <h2>CEMENT INDUSTRIES (SABAH) SDN. BHD.</h2>
                    <p>Sepanggar Industrial Estate | Official Tender Audit Verification Report</p>
                    <p>Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <h3>Verification Trail Records</h3>
                <table>
                    <thead>
                        <tr>
                            <th>No.</th>
                            <th>Tender Details</th>
                            <th>Committee Member</th>
                            <th>Designation</th>
                            <th>Timestamp</th>
                            <th>Remarks</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_rows}
                    </tbody>
                </table>
                <div class="footer">
                    <p>This is a system-generated audit report from the CIS Electronic Tender Portal.</p>
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
    audit_df["Closing Date"] = raw_audit_df["closing_date"]
    audit_df["Opening Date"] = raw_audit_df["opening_date"]
    audit_df["Verified By"] = raw_audit_df["verified_by"]
    audit_df["Department"] = raw_audit_df["department"]
    audit_df["Designation"] = raw_audit_df["designation"]
    audit_df["Timestamp"] = raw_audit_df["timestamp"]
    audit_df["Remarks"] = raw_audit_df["remarks"]

    st.dataframe(audit_df, use_container_width=True, hide_index=True)
  else:
    st.info("No audit verification entries logged yet.")
