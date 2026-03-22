import streamlit as st
from google import genai
from google.genai import types

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Satyam's AI Assistant", page_icon="🤖", layout="centered")

# Custom CSS for a professional "Messenger" look
st.markdown("""
    <style>
    .stApp { background-color: #F5F7FB; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Satyam's AI Assistant")
st.info("Batch 2024 AI Engineering Project")

# --- 2. SECURE API KEY & CLIENT SETUP ---
# This looks for the key in Streamlit's hidden "Secrets" vault
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    # Initialize the Gemini Client here
    client = genai.Client(api_key=API_KEY)
else:
    st.error("Setup required: Please add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

# --- 3. CHAT HISTORY LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 4. INPUT HANDLING ---
if prompt := st.chat_input("Ask me anything..."):
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                sys_msg = "You are a professional AI assistant built by Satyam, an AI Engineer (2024 batch)."
                response = client.models.generate_content(
                    model="models/gemini-1.5-flash", 
                    contents=f"{sys_msg} User: {prompt}"
                )
                full_response = response.text
                st.markdown(full_response)
                
                # 3. Save to History
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"An error occurred: {e}")
