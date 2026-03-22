import streamlit as st
from google import genai
from google.genai import types

# --- PAGE CONFIG ---
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

# --- SECURE API KEY ---
# When deployed, Streamlit will look for this in its 'Secrets' setting
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # This allows you to still test it locally on your Mac
    API_KEY = "AIzaSyCMpPyLybdthGF71BoRLJfxMSVWTrE6b3k"

client = genai.Client(api_key=API_KEY)

# --- CHAT HISTORY LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- INPUT HANDLING ---
if prompt := st.chat_input("Ask me anything..."):
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            sys_msg = "You are a professional AI assistant built by Satyam, an AI Engineer (2024 batch)."
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite", 
                contents=f"{sys_msg} User: {prompt}"
            )
            full_response = response.text
            st.markdown(full_response)
            
    # 3. Save to History
    st.session_state.messages.append({"role": "assistant", "content": full_response})