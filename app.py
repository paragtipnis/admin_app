import streamlit as st
import pandas as pd
import uuid
from supabase import create_client, Client
import os

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
if 'uploaded' not in st.session_state:
    st.session_state.uploaded = False

st.title("📋 Admin Panel – Name Navigator")

uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

def upload_participants_to_supabase(df):
    st.write("🧹 Deleting old entries...")
    supabase.table("participants").delete().gt("position", -1).execute()

    # Prepare new records
    records = []
    for i, row in df.iterrows():
        records.append({
            "id": str(uuid.uuid4()),
            "name": row['name'],
            "registration_id": str(row['registration_id']),
            "position": i,
            "status": "none"
        })

    # Upload in batches of 50
    all_errors = []
    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        try:
            res = supabase.table("participants").insert(batch).execute()
#            st.write(f"🔄 Batch {i//50 + 1} response:", res)
            if res.data:
                st.write(f"✅ Inserted batch {i//50 + 1}")
            else:
                all_errors.append(f"Batch {i//50 + 1} returned no data.")
        except Exception as e:
            all_errors.append(f"Error in batch {i//50 + 1}: {str(e)}")

    if all_errors:
        st.error("❌ Upload had some issues:")
        st.write(all_errors)
    else:
        st.success("✅ Uploaded all records to Supabase successfully.")

if uploaded_file and st.session_state.df is None:
    df = pd.read_excel(uploaded_file)

    if df.shape[1] < 2:
        st.error("❌ The Excel file must have at least two columns: Name and Registration ID.")
    else:
        df = df.iloc[:, :2]
        df.columns = ['name', 'registration_id']
        st.session_state.df = df
        st.session_state.current_index = -1
        st.session_state.uploaded = True
        st.write("Preview of uploaded file:")
        st.dataframe(df.head())

# ✅ Always show Upload button when df exists
if st.session_state.df is not None:
    if st.button("Upload to Supabase"):
        st.write("🔁 Upload button clicked.")
        upload_participants_to_supabase(st.session_state.df)

# Scroll logic
def update_current_position(index):
    supabase.table("current_position").update({
        "index": index
    }).eq("id", CURRENT_POSITION_ID).execute()

    supabase.table("participants").update({"status": "none"}).gt("position", -1).execute()

#Update 1804-a01 Start - Added a new logic to update status to turn for current turn - updated on 18/04/2024
    new_turn = index
    if new_turn < len(st.session_state.df):
        supabase.table("participants").update({
            "status":"turn"
        }).eq ("position", new_turn).execute()
#Update 1804-a01 Finish

    next_row = index + 1
    if next_row < len(st.session_state.df):
        supabase.table("participants").update({
            "status": "next"
        }).eq("position", next_row).execute()

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

    if 0 <= st.session_state.current_index < len(st.session_state.df):
        row = st.session_state.df.iloc[st.session_state.current_index]
        st.success(f"🎯 Current Selection: **{row['name']}** (Reg ID: {row['registration_id']}) – #{st.session_state.current_index + 1}")

        if st.session_state.current_index + 1 < len(st.session_state.df):
            row = st.session_state.df.iloc[st.session_state.current_index + 1]
            st.info(f"👤 Next: {row['name']} (Reg ID: {row['registration_id']})")

        ready_list = []
        for i in range(st.session_state.current_index + 2, st.session_state.current_index + 7):
            if i < len(st.session_state.df):
                ready = st.session_state.df.iloc[i]
                ready_list.append(f"{ready['name']} (Reg ID: {ready['registration_id']})")

        if ready_list:
            st.warning("🟡 Be Ready: " + ", ".join(ready_list))

    else:
        st.info("Click 'Next' to begin navigating the list.")

if st.session_state.df is not None:
    st.divider()
    st.subheader("📜 Full Participant List (Click to Jump)")

    items_per_page = 20
    total_pages = (len(st.session_state.df) + items_per_page - 1) // items_per_page

    if 'page' not in st.session_state:
        st.session_state.page = 0

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Prev") and st.session_state.page > 0:
            st.session_state.page -= 1

    with col2:
        st.markdown(f"**Page {st.session_state.page + 1} of {total_pages}**")

    with col3:
        if st.button("➡️ Next") and st.session_state.page < total_pages - 1:
            st.session_state.page += 1

    start_idx = st.session_state.page * items_per_page
    end_idx = min(start_idx + items_per_page, len(st.session_state.df))
    page_data = st.session_state.df.iloc[start_idx:end_idx].copy()
    page_data.index = range(start_idx + 1, end_idx + 1)

    display_names = [
        f"{i}. {row[0]} (Reg ID: {row[1]})"
        for i, row in zip(page_data.index, page_data.itertuples(index=False, name=None))
    ]

    selected_name = st.radio("Select a participant to jump to:", display_names, key="select_name_radio")

    if st.button("Jump to Selected"):
        selected_index = int(selected_name.split('.')[0]) - 1  # Extract row number
        st.session_state.current_index = selected_index
        update_current_position(selected_index)
        st.rerun()

#if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 10000))
#    app.run(host="0.0.0.0", port=port)