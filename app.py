import datetime
import streamlit as st
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CIS Electronic Tender & Attendance Portal",
    page_icon="📋",
    layout="wide"
)

# --- SUPABASE CONFIGURATION ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- APP HEADER ---
st.title("📋 CIS Electronic Tender & Attendance Portal")
st.markdown("---")

# --- FETCH ACTIVE TENDERS ---
try:
    response = supabase.table("active_tenders").select("*").execute()
    tenders = response.data
except Exception as e:
    st.error(f"Error fetching active tenders: {e}")
    tenders = []

if not tenders:
    st.warning("No active tenders available at the moment.")
else:
    # Tender Selection with safe fallback for keys
    tender_options = {}
    for t in tenders:
        t_num = t.get("tender_no") or t.get("id") or t.get("tender_id") or "UNKNOWN"
        t_ttl = t.get("tender_title") or t.get("title") or ""
        label = f"{t_num} - {t_ttl}" if t_ttl else str(t_num)
        tender_options[label] = t

    selected_tender_label = st.selectbox("Select Tender for Verification", options=list(tender_options.keys()))
    
    selected_tender = tender_options[selected_tender_label]
    t_no = selected_tender.get("tender_no") or selected_tender.get("id") or selected_tender.get("tender_id") or "UNKNOWN"
    t_title = selected_tender.get("tender_title") or selected_tender.get("title") or "N/A"
    
    st.markdown(f"### Tender Details: **{t_no}**")
    st.info(f"**Title:** {t_title}")
    
    st.markdown("---")
    
    # --- ATTENDANCE & VERIFICATION FORM ---
    with st.form(key="attendance_verification_form"):
        st.subheader("Section 1: Verifier Details")
        
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name (as per ID) *")
        with col2:
            department = st.selectbox(
                "Department *",
                ["-- Please Select Department --", "Information Technology", "Procurement", "Internal Audit", "Engineering", "Finance & Administration"]
            )
            
        designation = st.text_input("Designation / Job Title *")
        
        st.markdown("---")
        st.subheader("Section 2: Attendance Status")
        present = st.radio("Attendance Confirmation *", ["Present / In Attendance", "Absent / Represented"], horizontal=True)
        
        st.markdown("---")
        st.subheader("Section 3: Tender Verification Declarations")
        st.markdown("Please check all boxes to confirm your verification:")
        
        d1 = st.checkbox("I verified the tenderers and amounts listed against the online tender system.")
        d2 = st.checkbox("I confirm that the information recorded during the tender opening is true and complete to the best of my knowledge.")
        d3 = st.checkbox("I observed proper compliance procedures during the opening session.")
        d4 = st.checkbox("I am authorized to execute this verification record.")
        
        remarks = st.text_area("Remarks (Optional)", placeholder="Enter any observation or exceptions noted during the tender opening.")
        
        st.markdown("---")
        st.subheader("Section 4: Electronic Acknowledgement")
        st.markdown("By entering your full name below and submitting this form, you acknowledge that this submission, together with your system-generated timestamp, constitutes your official attendance and verification record.")
        
        sig_name = st.text_input("Electronic Signature (Full Name) *")
        
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
                
                # Combine extra fields into remarks to prevent schema mismatch errors
                declarations_str = f"Present Status: {present} | Declarations: [1:{d1}, 2:{d2}, 3:{d3}, 4:{d4}]"
                full_remarks = f"Designation: {designation} | {declarations_str}"
                if remarks:
                    full_remarks += f" | Remarks: {remarks}"

                try:
                    payload = {
                        "tender_no": str(t_no),
                        "verified_by": str(full_name),
                        "department": str(department),
                        "timestamp": str(timestamp),
                        "remarks": str(full_remarks)
                    }
                    
                    supabase.table("submissions").insert(payload).execute()
                    st.success(
                        f"Verification successfully recorded for {t_no} and timestamped at {timestamp}!"
                    )
                except Exception as e:
                    st.error(f"Supabase Insertion Error Details: {e}")
