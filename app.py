import streamlit as st
import streamlit.components.v1 as components
from google import genai
from gtts import gTTS
import io, base64, os, tempfile, pathlib

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
if "conversation"    not in st.session_state: st.session_state.conversation    = []
if "pending_audio"   not in st.session_state: st.session_state.pending_audio   = None
if "last_processed"  not in st.session_state: st.session_state.last_processed  = None
if "component_ready" not in st.session_state: st.session_state.component_ready = False

# ── GEMINI CLIENT ──────────────────────────────────────────────────────────────
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "YOUR_GEMINI_API_KEY_HERE"

client = genai.Client(api_key=API_KEY)
SYS = "You are a professional AI assistant built by Satyam, an AI Engineer. Reply very briefly in 1 or 2 conversational sentences max."

# ── BUILD COMPONENT DIR AT RUNTIME ────────────────────────────────────────────
# Write index.html next to app.py at startup — works on any host including
# Streamlit Cloud where we can't rely on working directory or __file__ tricks.

COMPONENT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:transparent; font-family:monospace; display:flex; flex-direction:column; align-items:center; padding:10px; }
  #mic-orb {
    width:90px; height:90px; border-radius:50%;
    background:radial-gradient(circle at 35% 35%,#1e3a5f,#0c1a2e);
    border:2px solid #38BDF8; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    font-size:2rem; margin:10px auto; transition:all 0.3s ease; user-select:none;
  }
  #mic-orb.listening  { animation:orbPulse 1.5s ease-in-out infinite; border-color:#34D399; box-shadow:0 0 30px rgba(52,211,153,0.35); }
  #mic-orb.processing { border-color:#38BDF8; animation:orbSpin 1s linear infinite; }
  @keyframes orbPulse { 0%,100%{box-shadow:0 0 0 0 rgba(52,211,153,0.5);transform:scale(1)} 50%{box-shadow:0 0 0 18px rgba(52,211,153,0);transform:scale(1.05)} }
  @keyframes orbSpin  { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
  #badge { display:inline-block; padding:4px 16px; border-radius:999px; font-size:0.72rem; background:#1E293B; color:#64748B; transition:all 0.3s; margin-bottom:10px; }
  #badge.listening  { background:rgba(52,211,153,0.15); color:#34D399; }
  #badge.processing { background:rgba(56,189,248,0.15); color:#38BDF8; }
  #badge.error      { background:rgba(248,113,113,0.15); color:#F87171; }
  #live-box { width:100%; background:#020617; border-left:3px solid #38BDF8; border-radius:8px; padding:10px 14px; font-size:0.78rem; color:#64748B; min-height:40px; transition:border-color 0.3s; }
  #live-box.active { border-color:#34D399; color:#E2E8F0; }
</style>
</head>
<body>
<div id="mic-orb" onclick="toggleMic()">&#127897;&#65039;</div>
<span id="badge">IDLE &mdash; click to start</span>
<div id="live-box">Your speech will appear here&hellip;</div>
<script>
(function(){
  var orb=document.getElementById('mic-orb'),badge=document.getElementById('badge'),liveBox=document.getElementById('live-box');
  var recognition=null,isListening=false,lastSent=null;
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){badge.textContent='Use Chrome or Edge';badge.className='error';}

  function send(val){
    window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setComponentValue',value:val,dataType:'json'},'*');
  }
  window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');
  window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:210},'*');

  window.addEventListener('message',function(e){
    if(e.data&&e.data.isStreamlitMessage&&e.data.type==='streamlit:render'){
      orb.classList.remove('processing','listening');
      orb.innerHTML='&#127897;&#65039;';
      badge.textContent='IDLE \u2014 click to start';
      badge.className='';
      liveBox.textContent='Your speech will appear here\u2026';
      liveBox.classList.remove('active');
      lastSent=null;
    }
  });

  window.toggleMic=function(){if(isListening){stopL();return;}startL();};

  function startL(){
    if(!SR)return;
    recognition=new SR();
    recognition.continuous=false;recognition.interimResults=true;recognition.lang='en-US';
    recognition.onresult=function(e){
      var interim='',final='';
      for(var i=e.resultIndex;i<e.results.length;i++){
        if(e.results[i].isFinal)final+=e.results[i][0].transcript;
        else interim+=e.results[i][0].transcript;
      }
      liveBox.textContent=final||interim;liveBox.classList.add('active');
      if(final.trim()&&final.trim()!==lastSent){
        lastSent=final.trim();stopL();setProc();send(final.trim());
      }
    };
    recognition.onerror=function(e){stopL();badge.textContent='MIC ERROR: '+e.error;badge.className='error';};
    recognition.onend=function(){if(isListening)stopL();};
    recognition.start();
    isListening=true;
    orb.classList.add('listening');orb.innerHTML='&#9209;&#65039;';
    badge.textContent='LISTENING\u2026';badge.className='listening';
    liveBox.textContent='Listening\u2026';liveBox.classList.add('active');
  }
  function stopL(){
    isListening=false;orb.classList.remove('listening');orb.innerHTML='&#127897;&#65039;';
    liveBox.classList.remove('active');try{recognition.stop();}catch(e){}
  }
  function setProc(){
    orb.classList.add('processing');orb.innerHTML='&#10024;';
    badge.textContent='PROCESSING\u2026';badge.className='processing';
  }
})();
</script>
</body>
</html>"""

# Write component folder next to app.py — guaranteed to exist at runtime
_app_dir = pathlib.Path(__file__).parent.resolve()
_comp_dir = _app_dir / "voice_component_runtime"
_comp_dir.mkdir(exist_ok=True)
(_comp_dir / "index.html").write_text(COMPONENT_HTML, encoding="utf-8")

voice_orb = components.declare_component("voice_orb", path=str(_comp_dir))

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="va-card"><h2>&#129302; Satyam\'s AI Assistant</h2><p>Click the orb &rarr; speak &rarr; get an instant AI reply</p></div>', unsafe_allow_html=True)

# ── CONVERSATION DISPLAY ───────────────────────────────────────────────────────
for turn in st.session_state.conversation:
    icon = "YOU" if turn["role"] == "user" else "ASSISTANT"
    cls  = "bubble-user" if turn["role"] == "user" else "bubble-ai"
    st.markdown(f'<div class="bubble-label">{icon}</div><div class="{cls}">{turn["text"]}</div>', unsafe_allow_html=True)

# ── AUTOPLAY AUDIO ─────────────────────────────────────────────────────────────
if st.session_state.pending_audio:
    st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{st.session_state.pending_audio}"></audio>', unsafe_allow_html=True)
    st.session_state.pending_audio = None

# ── VOICE ORB ──────────────────────────────────────────────────────────────────
transcript = voice_orb(key="voice_orb_main", default=None)

# ── PROCESS TRANSCRIPT ─────────────────────────────────────────────────────────
if transcript and isinstance(transcript, str) and transcript.strip():
    user_text = transcript.strip()
    if st.session_state.last_processed != user_text:
        st.session_state.last_processed = user_text
        st.session_state.conversation.append({"role": "user", "text": user_text})
        with st.spinner("Thinking…"):
            try:
                # Build full conversation history so model has context
                history = [
                    {"role": "user",  "parts": [{"text": SYS}]},
                    {"role": "model", "parts": [{"text": "Understood. I will reply briefly in 1-2 sentences."}]}
                ]
                for turn in st.session_state.conversation:
                    role = "user" if turn["role"] == "user" else "model"
                    history.append({"role": role, "parts": [{"text": turn["text"]}]})

                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=history
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
    st.markdown("### Session Log")
    if st.session_state.conversation:
        for t in st.session_state.conversation:
            icon = "🧑" if t["role"] == "user" else "🤖"
            st.markdown(f"**{icon} {t['role'].title()}:** {t['text']}")
    else:
        st.caption("No conversation yet. Click the orb and speak!")
    if st.button("Clear History"):
        st.session_state.conversation = []
        st.session_state.last_processed = None
        st.rerun()
