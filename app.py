import streamlit as st
from google import genai
from gtts import gTTS
import io
import base64

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Satyam's AI Assistant", page_icon="🤖", layout="centered")

# ── STYLES ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
:root { --bg:#080C14; --surface:#0F172A; --border:#1E293B; --accent:#38BDF8; --green:#34D399; --red:#F87171; --muted:#64748B; --text:#E2E8F0; }
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

# ── GEMINI CLIENT ──────────────────────────────────────────────────────────────
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "YOUR_GEMINI_API_KEY_HERE"

client = genai.Client(api_key=API_KEY)
SYS = "You are a professional AI assistant built by Satyam, an AI Engineer. Reply very briefly in 1 or 2 conversational sentences max."

# ── READ TRANSCRIPT FROM QUERY PARAM (set by JS before rerun) ─────────────────
user_text = st.query_params.get("q", "").strip()
if user_text:
    st.query_params.clear()

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="va-card"><h2>🤖 Satyam\'s AI Assistant</h2><p>Click the orb → speak → get an instant AI reply</p></div>', unsafe_allow_html=True)

# ── CONVERSATION DISPLAY ───────────────────────────────────────────────────────
for turn in st.session_state.conversation:
    icon = "YOU" if turn["role"] == "user" else "ASSISTANT"
    cls  = "bubble-user" if turn["role"] == "user" else "bubble-ai"
    st.markdown(f'<div class="bubble-label">{icon}</div><div class="{cls}">{turn["text"]}</div>', unsafe_allow_html=True)

# ── AUTOPLAY AUDIO ─────────────────────────────────────────────────────────────
if st.session_state.pending_audio:
    b64 = st.session_state.pending_audio
    st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{b64}"></audio>', unsafe_allow_html=True)
    st.session_state.pending_audio = None

# ── SPEECH ORB UI ──────────────────────────────────────────────────────────────
orb_html = """
<style>
#mic-orb {
  width:90px; height:90px; border-radius:50%;
  background:radial-gradient(circle at 35% 35%,#1e3a5f,#0c1a2e);
  border:2px solid #38BDF8; cursor:pointer;
  display:flex; align-items:center; justify-content:center;
  font-size:2rem; margin:16px auto; transition:all 0.3s ease;
}
#mic-orb.listening  { animation:orbPulse 1.5s ease-in-out infinite; border-color:#34D399; box-shadow:0 0 30px rgba(52,211,153,0.3); }
#mic-orb.processing { border-color:#38BDF8; animation:orbSpin 1s linear infinite; }
@keyframes orbPulse { 0%,100%{box-shadow:0 0 0 0 rgba(52,211,153,0.5);transform:scale(1)} 50%{box-shadow:0 0 0 18px rgba(52,211,153,0);transform:scale(1.05)} }
@keyframes orbSpin  { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
#badge { display:inline-block; padding:4px 14px; border-radius:999px; font-family:monospace; font-size:0.75rem; background:#1E293B; color:#64748B; transition:all 0.3s; }
#badge.listening  { background:rgba(52,211,153,0.15); color:#34D399; }
#badge.processing { background:rgba(56,189,248,0.15); color:#38BDF8; }
#badge.error      { background:rgba(248,113,113,0.15); color:#F87171; }
#live-box { background:#020617; border-left:3px solid #38BDF8; border-radius:8px; padding:12px 16px; margin:14px 0; font-family:monospace; font-size:0.8rem; color:#64748B; min-height:42px; }
#live-box.active { border-color:#34D399; color:#E2E8F0; }
</style>

<div style="text-align:center">
  <div id="mic-orb" onclick="toggleMic()">🎙️</div>
  <span id="badge">IDLE — click to start</span>
</div>
<div id="live-box">Your speech will appear here…</div>

<script>
(function(){
  const orb     = document.getElementById('mic-orb');
  const badge   = document.getElementById('badge');
  const liveBox = document.getElementById('live-box');
  let recognition = null;
  let isListening = false;

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { badge.textContent = 'Not supported — use Chrome/Edge'; badge.className = 'error'; }

  window.toggleMic = function() {
    if (isListening) { stopListening(); return; }
    startListening();
  };

  function startListening() {
    if (!SR) return;
    recognition = new SR();
    recognition.continuous     = false;
    recognition.interimResults = true;
    recognition.lang           = 'en-US';

    recognition.onresult = (e) => {
      let interim = '', final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final  += e.results[i][0].transcript;
        else                      interim += e.results[i][0].transcript;
      }
      liveBox.textContent = final || interim;
      liveBox.classList.add('active');
      if (final.trim()) {
        stopListening();
        sendToBackend(final.trim());
      }
    };

    recognition.onerror = (e) => {
      stopListening();
      badge.textContent = 'MIC ERROR: ' + e.error;
      badge.className = 'error';
    };

    recognition.onend = () => { if (isListening) stopListening(); };
    recognition.start();

    isListening = true;
    orb.classList.add('listening');
    orb.textContent = '⏹️';
    badge.textContent = 'LISTENING…';
    badge.className = 'listening';
    liveBox.textContent = 'Listening…';
    liveBox.classList.add('active');
  }

  function stopListening() {
    isListening = false;
    orb.classList.remove('listening');
    orb.textContent = '🎙️';
    liveBox.classList.remove('active');
    try { recognition.stop(); } catch(e) {}
  }

  function sendToBackend(text) {
    orb.classList.add('processing');
    orb.textContent = '✨';
    badge.textContent = 'PROCESSING…';
    badge.className = 'processing';

    // Set query param on PARENT window URL then navigate — Streamlit picks it up on reload
    const url = new URL(window.parent.location.href);
    url.searchParams.set('q', text);
    window.parent.location.href = url.toString();   // full navigation = guaranteed Streamlit rerun
  }
})();
</script>
"""

st.components.v1.html(orb_html, height=240, scrolling=False)

# ── PROCESS SPEECH ─────────────────────────────────────────────────────────────
if user_text:
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
        st.rerun()
