import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder

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
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # Fallback for local testing
    API_KEY = "AIzaSyCMpPyLybdthGF71BoRLJfxMSVWTrE6b3k"

client = genai.Client(api_key=API_KEY)
sys_msg = "You are a professional AI assistant built by Satyam, an AI Engineer (2024 batch)."

# --- CHAT HISTORY LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- SIDEBAR VOICE CONTROL ---
with st.sidebar:
    st.header("🎙️ Voice Dashboard")
    st.write("Click below to speak to the assistant.")
    
    # Microphone component
    audio = mic_recorder(
        start_prompt="⏺️ Record Voice",
        stop_prompt="⏹️ Stop & Send",
        key='voice_recorder'
    )
    
    # Clear Chat Button
    st.write("---")
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

# --- AUDIO INPUT PROCESSING ---
if audio:
    # 1. Save user placeholder to history
    st.session_state.messages.append({"role": "user", "content": "🎤 *Sent a voice message*"})
    
    # 2. Process audio bytes safely via Gemini's multimodal engine
    with st.chat_message("assistant"):
        with st.spinner("Listening to audio and generating response..."):
            try:
                # Use Part.from_bytes helper to avoid validation crashes
                from google.genai.types import Part
                
                audio_part = Part.from_bytes(
                    data=audio['bytes'],
                    mime_type="audio/wav"
                )
                
                # Combine system instruction directly inside the call logic
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
                    contents=[f"{sys_msg} Please listen to this raw audio input and answer directly.", audio_part])
                
                full_response = response.text
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # Clean refresh to render inside the viewport timeline
                st.rerun()
                
            except Exception as e:
                st.error(f"Audio Processing Error: {e}")
# --- TEXT INPUT HANDLING ---
if prompt := st.chat_input("Ask me anything..."):
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite", 
                contents=f"{sys_msg} User: {prompt}"
            )
            full_response = response.text
            st.markdown(full_response)
            
    # 3. Save to History
    st.session_state.messages.append({"role": "assistant", "content": full_response})
