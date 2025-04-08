import streamlit as st
import pandas as pd
import uuid
from supabase import create_client, Client

# Supabase project config
SUPABASE_URL = "https://kiwfjvsvhbxujgnpjhim.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtpd2ZqdnN2aGJ4dWpnbnBqaGltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQwNDk2NDMsImV4cCI6MjA1OTYyNTY0M30.svQXOgCRC4Hx-xdUwACZDqq4No7_oPkowpf5OPWKJ18"
CURRENT_POSITION_ID = "0e195afe-c751-48f2-96b2-144aa081aa28"  # Insert this UUID once manually in Supabase

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

st.title("📋 Admin Panel – Name Navigator")

uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

def upload_participants_to_supabase(df):
    # First clear existing entries (optional)
    supabase.table("participants").delete().gt("position", -1).execute()

    # Prepare and insert new data
    records = []
    for i, row in df.iterrows():
        records.append({
            "id": str(uuid.uuid4()),
            "name": row[0],
            "position": i,
            "status": "none"
        })

    for i in range(0, len(records), 50):  # Chunked inserts
        supabase.table("participants").insert(records[i:i+50]).execute()

    st.success("✅ Uploaded to Supabase successfully.")

if uploaded_file and st.session_state.df is None:
    df = pd.read_excel(uploaded_file)

    if df.shape[1] < 1:
        st.error("❌ The Excel file must have at least one column (names).")
    else:
        st.session_state.df = df
        st.session_state.current_index = -1
        st.session_state.uploaded = True
        st.write("Preview of uploaded file:")
        st.dataframe(df.head())
        if st.button("Upload to Supabase"):
            upload_participants_to_supabase(df)

if 'uploaded' not in st.session_state:
    st.session_state.uploaded = False

# Scroll logic
def update_current_position(index):
    supabase.table("current_position").update({
        "index": index
    }).eq("id", CURRENT_POSITION_ID).execute()

    # Reset all participant statuses
    supabase.table("participants").update({"status": "none"}).gt("position", -1).execute()

    # Set 'you are next'
    next_row = index + 1
    if next_row < len(st.session_state.df):
        supabase.table("participants").update({
            "status": "next"
        }).eq("position", next_row).execute()

    # Set 'be ready'
    ready_rows = list(range(next_row + 1, next_row + 6))
    for row in ready_rows:
        if row < len(st.session_state.df):
            supabase.table("participants").update({
                "status": "ready"
            }).eq("position", row).execute()

if st.session_state.df is not None:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Next"):
            if st.session_state.current_index + 1 >= len(st.session_state.df):
                st.warning("Reached the end of the list.")
            else:
                st.session_state.current_index += 1
                update_current_position(st.session_state.current_index)
                st.rerun()

    with col2:
        if st.button("Reset"):
            st.session_state.current_index = -1
            update_current_position(-1)
            st.rerun()

    # ✅ Now show current, next, ready only if index is valid
    if 0 <= st.session_state.current_index < len(st.session_state.df):
        current_name = st.session_state.df.iloc[st.session_state.current_index, 0]
        st.success(f"🎯 Current Selection: **{current_name}** (#{st.session_state.current_index + 1} of {len(st.session_state.df)})")

        # 👤 Next
        if st.session_state.current_index + 1 < len(st.session_state.df):
            next_name = st.session_state.df.iloc[st.session_state.current_index + 1, 0]
            st.info(f"👤 Next: {next_name}")

        # 🟡 Be Ready
        ready_list = []
        for i in range(st.session_state.current_index + 2, st.session_state.current_index + 7):
            if i < len(st.session_state.df):
                ready_list.append(st.session_state.df.iloc[i, 0])

        if ready_list:
            st.warning("🟡 Be Ready: " + ", ".join(ready_list))

    else:
        st.info("Click 'Next' to begin navigating the list.")