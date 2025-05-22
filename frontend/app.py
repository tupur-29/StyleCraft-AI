import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
GENERATE_ENDPOINT = f"{API_BASE_URL}/generate/"

# --- Initialize session state ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = "" # Mock user ID

if 'history' not in st.session_state:
    st.session_state.history = [] # To store past interactions: [ {query, casual, formal, timestamp}, ... ]

if 'current_casual_response' not in st.session_state:
    st.session_state.current_casual_response = ""

if 'current_formal_response' not in st.session_state:
    st.session_state.current_formal_response = ""

if 'error_message' not in st.session_state:
    st.session_state.error_message = ""

# --- Helper Functions ---
def add_to_history(query, casual_response, formal_response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.history.insert(0, { 
        "query": query,
        "casual": casual_response,
        "formal": formal_response,
        "timestamp": timestamp
    })

# --- UI Sections ---
st.sidebar.header("User Settings")
user_id_input = st.sidebar.text_input(
    "Enter Your User ID (for tracking history):",
    value=st.session_state.user_id if st.session_state.user_id else "default_user" # Default if empty
)
if user_id_input:
    st.session_state.user_id = user_id_input
else:
    
    if not st.session_state.user_id:
        st.session_state.user_id = "default_user"


# --- Main App Interface ---
st.title("🔄 StyleCraft AI")
st.write(f"Interacting as User: `{st.session_state.user_id}`")


# --- 2. Input Section ---
with st.form(key="query_form"):
    user_query = st.text_area("Enter your query:", height=100, key="user_query_input")

    submit_button = st.form_submit_button(label="✨ Generate Responses")

if submit_button:
    st.session_state.error_message = "" 
    st.session_state.current_casual_response = "" 
    st.session_state.current_formal_response = ""

    if not user_query.strip():
        st.session_state.error_message = "⚠️ Please enter a query."
    elif not st.session_state.user_id:
        st.session_state.error_message = "⚠️ Please set a User ID in the sidebar."
    else:
        with st.spinner("🤖 Generating AI responses... Please wait."):
            try:
                payload = {
                    "query": user_query,
                    "user_id": st.session_state.user_id
                }
                
                print(f"DEBUG: Sending POST to: {GENERATE_ENDPOINT}") 
                print(f"DEBUG: Payload: {payload}") 
                response = requests.post(GENERATE_ENDPOINT, json=payload)

                if response.status_code == 201:
                    data = response.json()
                    st.session_state.current_casual_response = data.get("casual_response", "N/A")
                    st.session_state.current_formal_response = data.get("formal_response", "N/A")
                    add_to_history(
                        user_query,
                        st.session_state.current_casual_response,
                        st.session_state.current_formal_response
                    )
                    
                else:
                    try:
                        error_data = response.json()
                        detail = error_data.get("detail", "Unknown error from API.")
                        st.session_state.error_message = f"API Error ({response.status_code}): {detail}"
                    except requests.exceptions.JSONDecodeError:
                        st.session_state.error_message = f"API Error ({response.status_code}): {response.text}"

            except requests.exceptions.RequestException as e:
                st.session_state.error_message = f"Connection Error: Could not reach API. ({e})"
            except Exception as e:
                st.session_state.error_message = f"An unexpected error occurred: {e}"

# --- Display Error Messages ---
if st.session_state.error_message:
    st.error(st.session_state.error_message)

# --- Response Display Section ---
st.subheader("AI Generated Responses")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🗣️ Casual Style")
    if st.session_state.current_casual_response:
        st.info(st.session_state.current_casual_response) 
    else:
        st.markdown("_Casual response will appear here._")

with col2:
    st.markdown("#### 👔 Formal Style")
    if st.session_state.current_formal_response:
        st.success(st.session_state.current_formal_response) 
    else:
        st.markdown("_Formal response will appear here._")


# --- History Sidebar ---
st.sidebar.header("📜 Interaction History")
if not st.session_state.history:
    st.sidebar.caption("No interactions yet.")
else:
    for i, item in enumerate(st.session_state.history):
        with st.sidebar.expander(f"{item['timestamp']} - Query: {item['query'][:30]}..."):
            st.markdown(f"**Query:**\n```\n{item['query']}\n```")
            st.markdown(f"**Casual Response:**\n```\n{item['casual']}\n```")
            st.markdown(f"**Formal Response:**\n```\n{item['formal']}\n```")
            if st.button(f"Re-view #{len(st.session_state.history)-i}", key=f"review_btn_{i}"):
                st.session_state.current_casual_response = item['casual']
                st.session_state.current_formal_response = item['formal']
                
                st.experimental_rerun() 


st.markdown("---")
st.caption("StyleCraft AI Prototype")
