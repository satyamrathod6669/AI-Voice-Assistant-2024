import streamlit as st
import streamlit.components.v1 as components
from google import genai
from gtts import gTTS
import io
import base64
import os

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Satyam's AI Assistant", page_icon="🤖", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
:root { --bg:#080C14; --surface:#0F172A; --border:#1E293B; --accent:#38BDF8; --green:#34D399; --muted:#64748B; --text:#E2E8F0; }
html,body,.stApp { background:var(--bg) !important; color:var(--text); font-family:'Syne',sans-serif; }
#MainMenu,footer,header { visibility:hidden; }
.block-container { padding-top:1.5rem !important; }
.va-card { background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:28px 32px; margin-bottom:20px; text-align:center; }
.va-card h2 { font-size:1.6rem; font-weight:800; letter-spacing:-0.5px; margin:0 0 6px; }
.va-card p  { color:var(--muted); font-size:0.88rem; margin:0; }
.bubble-user  { background:#1e3a5f; border-radius:12px 12px 4px 12px; padding:10px 16px; margin:6px 0 6px auto; max-width:78%; font-size:0.9rem; }
.bubble-ai    { background:var(--surface); border:1px solid var(--border); border-radius:12px 12px 12px 4px; padding:10px 16px; margin:6px auto 6px 0; max-width:78%; font-size:0.9rem; }
.bubble-label { font-size:0.68rem; color:var(--muted); font-family:'Space Mono',monospace; margin-bottom:2px; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None
if "last_processed" not in st.session_state:
    st.session_state.last_processed = None

# ── GEMINI CLIENT ──────────────────────────────────────────────────────────────
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "YOUR_GEMINI_API_KEY_HERE"

client = genai.Client(api_key=API_KEY)
SYS = "You are a professional AI assistant built by Satyam, an AI Engineer. Reply very briefly in 1 or 2 conversational sentences max."

# ── REGISTER CUSTOM COMPONENT ──────────────────────────────────────────────────
# voice_component/ folder must sit next to app.py in the repo root
COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_component")
voice_orb = components.declare_component("voice_orb", path=COMPONENT_DIR)

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="va-card"><h2>🤖 Satyam\'s AI Assistant</h2><p>Click the orb → speak → get an instant AI reply</p></div>', unsafe_allow_html=True)

# ── CONVERSATION DISPLAY ───────────────────────────────────────────────────────
for turn in st.session_state.conversation:
    icon = "YOU" if turn["role"] == "user" else "ASSISTANT"
    cls  = "bubble-user" if turn["role"] == "user" else "bubble-ai"
    st.markdown(f'<div class="bubble-label">{icon}</div><div class="{cls}">{turn["text"]}</div>', unsafe_allow_html=True)

# ── AUTOPLAY AUDIO ─────────────────────────────────────────────────────────────
if st.session_state.pending_audio:
    st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{st.session_state.pending_audio}"></audio>', unsafe_allow_html=True)
    st.session_state.pending_audio = None

# ── RENDER VOICE ORB COMPONENT ─────────────────────────────────────────────────
transcript = voice_orb(key="voice_orb_main", default=None)

# ── PROCESS TRANSCRIPT ─────────────────────────────────────────────────────────
if transcript and isinstance(transcript, str) and transcript.strip():
    user_text = transcript.strip()

    if st.session_state.last_processed != user_text:
        st.session_state.last_processed = user_text
        st.session_state.conversation.append({"role": "user", "text": user_text})

        with st.spinner("Thinking…"):
            try:
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{SYS}\nUser: {user_text}"
                )
                reply = resp.text

                tts = gTTS(text=reply, lang="en", slow=False)
                buf = io.BytesIO()
                tts.write_to_fp(buf)
                b64 = base64.b64encode(buf.getvalue()).decode()

                st.session_state.conversation.append({"role": "assistant", "text": reply})
                st.session_state.pending_audio = b64

            except Exception as e:
                st.error(f"Gemini Error: {e}")

        st.rerun()

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Session Log")
    if st.session_state.conversation:
        for t in st.session_state.conversation:
            icon = "🧑" if t["role"] == "user" else "🤖"
            st.markdown(f"**{icon} {t['role'].title()}:** {t['text']}")
    else:
        st.caption("No conversation yet. Click the orb and speak!")
    if st.button("🗑️ Clear History"):
        st.session_state.conversation = []
        st.session_state.last_processed = None
        st.rerun()
