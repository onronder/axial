import streamlit as st
import requests
import os
import json
import time

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
# If running locally (not docker), backend might be localhost
if "backend" in BACKEND_URL and "localhost" not in os.getenv("BACKEND_URL", ""):
     # Fallback for local testing if env var not set correctly for local
     if not os.getenv("BACKEND_URL"):
        BACKEND_URL = "http://localhost:8000"

API_KEY = "default-insecure-key"

# Page Config
st.set_page_config(
    page_title="Axial Newton", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Chat Bubbles */
    .stChatMessage {
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
    }
    [data-testid="stChatMessageContent"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #2E7D32; /* Premium Green */
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #1B5E20;
        transform: scale(1.02);
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Sidebar Style */
    section[data-testid="stSidebar"] {
        background-color: #111;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: CONTROL CENTER ---
with st.sidebar:
    st.title("🎛️ Control Center")
    st.caption(f"Backend: `{BACKEND_URL}`")
    
    # Health Check
    try:
        res = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if res.status_code == 200:
            st.success("System Online 🟢")
        else:
            st.error(f"Status: {res.status_code} 🔴")
    except:
        st.error("System Unreachable 🔴")
        
    st.divider()
    
    # File Ingestion
    st.subheader("📚 Knowledge Base")
    st.info("Upload documents to train the RAG brain.")
    
    uploaded_file = st.file_uploader("Upload File", type=["pdf", "txt", "docx", "png", "jpg"])
    
    if uploaded_file:
        if st.button("🚀 Ingest Document", use_container_width=True):
            with st.spinner("Processing & Embedding..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    data = {"metadata": json.dumps({"source": "frontend_upload", "client_id": "web-ui"})}
                    headers = {"X-API-KEY": API_KEY}
                    
                    # POST to Backend
                    response = requests.post(
                        f"{BACKEND_URL}/api/v1/ingest", 
                        files=files, 
                        data=data, 
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        st.balloons()
                        st.toast("Document Successfully Ingested! ✅", icon="🧠")
                        time.sleep(1)
                    else:
                        st.error(f"Ingestion Failed: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {str(e)}")

# --- MAIN CHAT INTERFACE ---
st.title("Axial Newton 🧠")
st.markdown("### Enterprise RAG Assistant")
st.caption("Ask questions about your uploaded documents. I will answer with citations.")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If there are sources, show them nicely
        if "sources" in message and message["sources"]:
            with st.expander("🔎 View Sources"):
                for src in message["sources"]:
                    st.markdown(f"- 📄 `{src}`")

# Chat Input & Logic
if prompt := st.chat_input("Ask me anything..."):
    # 1. Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate Assistant Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            payload = {"query": prompt, "model": "gpt-4o"}
            headers = {"X-API-KEY": API_KEY}
            
            # Show a nice spinner while waiting
            with st.spinner("Analyzing documents..."):
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/chat", 
                    json=payload, 
                    headers=headers
                )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                
                # Display Answer
                message_placeholder.markdown(answer)
                
                # Display Sources
                if sources:
                    with st.expander("📚 Referenced Sources"):
                        for src in sources:
                            st.write(f"- {src}")
                
                # 3. Save Context
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer, 
                    "sources": sources
                })
            else:
                error_msg = f"Server Error: {response.text}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
        except Exception as e:
            error_msg = f"Connection Error: {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
