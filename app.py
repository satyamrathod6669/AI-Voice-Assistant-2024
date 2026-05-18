import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import io
import base64
import json

# --- PAGE CONFIG ---
st.set_page_config(page_title="Satyam's AI Assistant", page_icon="🤖", layout="centered")

# Dark, futuristic theme styling
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .assistant-card { background-color: #1E293B; border-radius: 15px; padding: 25px; border: 1px solid #334155; text-align: center; margin-bottom: 20px;}
    .status-listening { color: #10B981; font-weight: bold; animation: pulse 2s infinite; }
    .status-stopped { color: #EF4444; font-weight: bold; }
    @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE STATE ---
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "listening" not in st.session_state:
    st.session_state.listening = True  # Default to listening on startup

# --- UI HEADER & TOGGLE BUTTON ---
st.markdown('<div class="assistant-card"><h2>🤖 Satyam\'s Voice Assistant</h2>', unsafe_allow_html=True)

if st.session_state.listening:
    st.markdown('<p>Status: <span class="status-listening">● Listening live... Speak anytime</span></p>', unsafe_allow_html=True)
    if st.button("🛑 Stop Listening", use_container_width=True):
        st.session_state.listening = False
        st.rerun()
else:
    st.markdown('<p>Status: <span class="status-stopped">■ Microphone Off</span></p>', unsafe_allow_html=True)
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
sys_msg = "You are a professional AI assistant built by Satyam, an AI Engineer. Reply very briefly in 1 or 2 sentences max."

# --- INJECT AMBIENT JAVASCRIPT MIC LISTENER (Only if active) ---
if st.session_state.listening:
    ctx_js = """
    <script>
        const parentDoc = window.parent.document;
        if (!window.audioInitialized) {
            window.audioInitialized = true;
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    window.localAudioStream = stream; // Keep track of stream to close later
                    const audioContext = new AudioContext();
                    window.localAudioContext = audioContext;
                    
                    const mediaStreamSource = audioContext.createMediaStreamSource(stream);
                    const processor = audioContext.createScriptProcessor(2048, 1, 1);
                    
                    let silenceStart = Date.now();
                    let speaking = false;
                    
                    mediaStreamSource.connect(processor);
                    processor.connect(audioContext.destination);
                    
                    processor.onaudioprocess = (e) => {
                        const inputData = e.inputBuffer.getChannelData(0);
                        let sum = 0.0;
                        for (let i = 0; i < inputData.length; i++) {
                            sum += inputData[i] * inputData[i];
                        }
                        let rms = Math.sqrt(sum / inputData.length);
                        
                        if (rms > 0.02) { 
                            if (!speaking) { speaking = true; }
                            silenceStart = Date.now();
                        } else {
                            if (speaking && (Date.now() - silenceStart > 1500)) {
                                speaking = false;
                                console.log("Voice pause detected. Sending parameter trigger...");
                                
                                // Direct, modern query param trigger to signal backend processing
                                window.parent.location.search = "?voice_trigger=true";
                            }
                        }
                    };
                }).catch(err => console.error("Mic Access Error: ", err));
        }
    </script>
    """
    st.components.v1.html(ctx_js, height=0, width=0)
else:
    # JavaScript snippet to securely close the microphone if user pressed stop
    stop_js = """
    <script>
        if (window.audioInitialized) {
            if (window.localAudioStream) {
                window.localAudioStream.getTracks().
