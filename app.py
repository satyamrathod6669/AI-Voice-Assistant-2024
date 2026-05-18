import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import io
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="Satyam's AI Assistant", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .assistant-card { background-color: #1E293B; border-radius: 15px; padding: 25px; border: 1px solid #334155; text-align: center; margin-bottom: 20px;}
    .status-listening { color: #10B981; font-weight: bold; animation: pulse 2s infinite; }
    .status-stopped { color: #EF4444; font-weight: bold; }
    .live-transcript-box { background-color: #020617; border-left: 4px solid #3B82F6; padding: 12px; border-radius: 6px; margin: 15px 0; font-style: italic; color: #94A3B8; text-align: left; }
    @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE STATE ---
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "listening" not in st.session_state:
    st.session_state.listening = True
if "voice_prompt" not in st.session_state:
    st.session_state.voice_prompt = None

# --- UI HEADER ---
st.markdown('<div class="assistant-card"><h2>🤖 Satyam\'s Voice Assistant</h2>', unsafe_allow_html=True)

if st.session_state.listening:
    st.markdown('<p>Status: <span class="status-listening">● Microphone Streaming Live...</span></p>', unsafe_allow_html=True)
    if st.button("🛑 Stop Listening", use_container_width=True):
        st.session_state.listening = False
        st.rerun()
else:
    st.markdown('<p>Status: <span class="status-stopped">■ Assistant Paused</span></p>', unsafe_allow_html=True)
    if st.button("🎙️ Start Listening", use_container_width=True):
        st.session_state.listening = True
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# --- SECURE API KEY ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "AIzaSyCMpPyLybdthGF71BoRLJfxMSVWTrE6b3k"

client = genai.Client(api_key=API_KEY)
sys_msg = "You are a professional AI assistant built by Satyam, an AI Engineer. Reply very briefly in 1 or 2 conversational sentences max."

st.markdown('<div id="transcript-container" class="live-transcript-box">🎙️ Say something... (Your live speech will appear here)</div>', unsafe_allow_html=True)

# --- AMBIENT JAVASCRIPT & PYTHON BRIDGE COMPONENT ---
if st.session_state.listening:
    # We use Streamlit's official HTML component callback trick to securely pipe data back
    html_bridge = """
    <div id="transcript-container-inner" style="display:none;"></div>
    <script>
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onresult = (event) => {
                let interimTranscript = '';
                let finalTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }
                
                // Dynamically modify parent layout container text safely
                const parentDoc = window.parent.document;
                const targetBox = parentDoc.getElementById("transcript-container");
                if (targetBox) {
                    targetBox.innerHTML = "<b>Listening:</b> " + (finalTranscript || interimTranscript);
                }
                
                // Securely notify Python backend via Streamlit's query bridge channel
                if (finalTranscript.trim().length > 0) {
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: finalTranscript.trim()
                    }, '*');
                }
            };
            
            recognition.onend = () => { recognition.start(); };
            recognition.start();
        }
    </script>
    """
    # This captures the `value` sent by postMessage instantly into Python!
    captured_speech = st.components.v1.html(html_bridge, height=0, width=0)
    
    if captured_speech and captured_speech != st.session_state.get("last_processed_speech"):
        st.session_state.voice_prompt = captured_speech
        st.session_state["last_processed_speech"] = captured_speech

# --- BACKEND CORE ENGINE EXECUTOR ---
if st.session_state.voice_prompt:
    user_prompt = st.session_state.voice_prompt
    st.session_state.voice_prompt = None  # Flush buffer immediately
    
    st.session_state.conversation.append({"role": "user", "text": user_prompt})
    
    with st.spinner("Thinking..."):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=f"{sys_msg} User: {user_prompt}"
            )
            full_response = response.text
            
            tts = gTTS(text=full_response, lang='en', slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            ai_audio_bytes = audio_fp.getvalue()
            
            st.session_state.conversation.append({"role": "Assistant", "text": full_response})
            
            # Autoplay delivery pipeline injection
            b64 = base64.b64encode(ai_audio_bytes).decode()
            autoplay_html = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}"></audio>'
            st.markdown(autoplay_html, unsafe_allow_html=True)
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Voice Assistant Engine Error: {e}")

# --- DISPLAY CONVERSATION STREAM ---
for turn in st.session_state.conversation:
    with st.chat_message(turn["role"].lower()):
        st.write(turn["text"])
