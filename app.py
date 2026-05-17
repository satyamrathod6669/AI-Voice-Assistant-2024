import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import io
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="Satyam's AI Assistant", page_icon="🤖", layout="centered")

# Enhanced CSS for high-contrast visibility
st.markdown("""
    <style>
    .stApp { background-color: #EBF0F5; }
    .stChatMessage p, .stChatMessage span, .stChatMessage div { 
        color: #1E293B !important; 
    }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Satyam's AI Assistant")
st.info("Batch 2024 AI Engineering Project")

# --- SECURE API KEY ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "AIzaSyCMpPyLybdthGF71BoRLJfxMSVWTrE6b3k"

client = genai.Client(api_key=API_KEY)
sys_msg = "You are a professional AI assistant built by Satyam, an AI Engineer (2024 batch). Respond very briefly and cleanly in 1-2 sentences max."

# --- HELPER FUNCTION FOR AUTOPLAY AUDIO ---
def play_audio_automatically(audio_bytes):
    """Converts audio bytes into an autoplaying HTML audio element"""
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True)

# --- CHAT HISTORY LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "audio_bytes" in message:
            # Traditional audio layout bar kept for history playback control
            st.audio(message["audio_bytes"], format="audio/mp3")

# --- SIDEBAR VOICE CONTROL ---
with st.sidebar:
    st.header("🎙️ Voice Dashboard")
    st.write("Click below to speak to the assistant.")
    
    from streamlit_mic_recorder import mic_recorder
    audio = mic_recorder(
        start_prompt="⏺️ Record Voice",
        stop_prompt="⏹️ Stop & Send",
        key='voice_recorder'
    )
    
    st.write("---")
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        if 'last_audio_id' in st.session_state:
            del st.session_state['last_audio_id']
        st.rerun()

# --- AUDIO INPUT PROCESSING ---
if audio and st.session_state.get('last_audio_id') != audio['id']:
    st.session_state['last_audio_id'] = audio['id']
    
    with st.chat_message("assistant"):
        with st.spinner("Listening to audio and generating response..."):
            try:
                from google.genai.types import Part
                
                audio_part = Part.from_bytes(
                    data=audio['bytes'],
                    mime_type="audio/wav"
                )
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash", 
                    contents=[f"{sys_msg} Listen to this audio prompt and reply directly.", audio_part]
                )
                
                full_response = response.text
                
                # Convert text response into spoken voice bytes
                tts = gTTS(text=full_response, lang='en', slow=False)
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                ai_audio_bytes = audio_fp.getvalue()
                
                st.session_state.messages.append({"role": "user", "content": "🎤 *Sent a voice message*"})
                
                msg_data = {"role": "assistant", "content": full_response, "audio_bytes": ai_audio_bytes}
                st.session_state.messages.append(msg_data)
                
                # Trigger instant vocal autoplay before the interface state resets
                play_audio_automatically(ai_audio_bytes)
                st.rerun()
                
            except Exception as e:
                st.error(f"Audio Processing Error: {e}")

# --- TEXT INPUT HANDLING ---
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=f"{sys_msg} User: {prompt}"
            )
            full_response = response.text
            
            tts = gTTS(text=full_response, lang='en', slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            ai_audio_bytes = audio_fp.getvalue()
            
            st.markdown(full_response)
            if ai_audio_bytes:
                play_audio_automatically(ai_audio_bytes)
            
    msg_data = {"role": "assistant", "content": full_response, "audio_bytes": ai_audio_bytes}
    st.session_state.messages.append(msg_data)
