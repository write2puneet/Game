"""
Mansam Sales Coach v4 — Stable
================================
Key changes from v3:
- Replaced st.audio_input (buggy, shows play/stop/download) with a clean
  custom HTML5 recorder component via st.components.v1.html
- Session state is iron-clad: every key checked with 'in' not .get()
- Single mic button, no extra controls visible
- Question bubble never flickers (only updates after full round-trip)

Groq secret:  GROQ_API_KEY = "gsk_..."
"""

import os, io, json, base64, time, hashlib
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from gtts import gTTS
from loguru import logger
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Mansam Sales Coach",
    page_icon="🕌",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"],.stApp{
    background:#F5F5F5 !important;
    color:#1A1A1A !important;
    font-family:'Inter',-apple-system,sans-serif !important;
}
.block-container{
    max-width:480px !important;
    padding:0 1.1rem 2rem !important;
    margin:0 auto !important;
}
#MainMenu,footer,header,
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"]{display:none !important;}
.stTextInput input{
    background:#fff !important;color:#1A1A1A !important;
    border:1.5px solid #E0E0E0 !important;border-radius:14px !important;
    font-size:16px !important;padding:.85rem 1rem !important;
}
.stTextInput input::placeholder{color:#B0B0B0 !important;}
.stButton>button{
    background:#1A1A1A !important;color:#fff !important;
    border:none !important;border-radius:14px !important;
    font-family:'Inter',sans-serif !important;font-weight:500 !important;
    font-size:.95rem !important;min-height:52px !important;width:100% !important;
}
.stButton>button:hover{background:#333 !important;}
.topbar{display:flex;align-items:center;justify-content:space-between;
        padding:.9rem 0 .6rem;border-bottom:1px solid #E8E8E8;margin-bottom:1.2rem;}
.topbar .brand{font-size:.88rem;font-weight:600;color:#1A1A1A;}
.topbar .pts{font-size:.8rem;color:#888;}
.card{background:#fff;border-radius:14px;padding:1.2rem 1.3rem;
      margin-bottom:.8rem;box-shadow:0 1px 6px rgba(0,0,0,.06);}
.card-dark{background:#1A1A1A;border-radius:14px;padding:1.3rem 1.4rem;margin-bottom:.8rem;}
.score-pair{display:flex;gap:.8rem;margin-bottom:.9rem;}
.score-card{flex:1;background:#fff;border-radius:14px;padding:1rem .8rem;
            text-align:center;box-shadow:0 1px 6px rgba(0,0,0,.06);}
.score-card .num{font-size:2rem;font-weight:700;color:#1A1A1A;line-height:1;}
.score-card .lbl{font-size:.7rem;color:#B0B0B0;text-transform:uppercase;letter-spacing:.08em;margin-top:.3rem;}
.score-card .just{font-size:.72rem;color:#888;margin-top:.3rem;line-height:1.4;}
.chip{display:inline-block;background:#FBF6E9;color:#8B6914;
      border-radius:20px;padding:4px 11px;font-size:.76rem;font-weight:500;margin:2px;}
.grow-item{background:#fff;border-left:3px solid #E0E0E0;border-radius:0 10px 10px 0;
           padding:.8rem 1rem;margin:.3rem 0;font-size:.87rem;line-height:1.55;}
.grow-item .try{margin-top:.3rem;font-style:italic;color:#C9A84C;font-size:.84rem;}
.div{border:none;border-top:1px solid #EBEBEB;margin:1rem 0;}
audio{width:100%;height:34px;border-radius:8px;margin:.3rem 0;accent-color:#C9A84C;}
</style>
""", unsafe_allow_html=True)

# ── constants ──────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
SESSION_SECS = 4 * 60

MANSAM_KB = """
MANSAM — Luxury Arabian Fragrance House. Four collections: Oud, Nayat, Qanun, Buzuq & Riqq.
Brand voice: quiet nobility, heritage, craftsmanship, calm authority.
Sales philosophy: storytelling > pushing. Discover the customer first, match emotion to bottle.
Never apologise for price. Anchor on heritage, rarity, emotional outcome.

FULL SKU LIBRARY (20 EDPs):

OUD COLLECTION
• Hams Min Al Sahraa — Men/family gifting. Rose/Floral/Musk-Oud. "Quiet nobility, inner depth."
• Naseem Al Ward — Unisex top-seller. Bergamot/Rose-Jasmine/Soft woods. "Graceful optimism, charm."
• Qublat Ward — Travel gifting. Bergamot/Rose/Oud. "Romantic authority, refined elegance."
• Shatha Biladi — Winter, Saudi identity. Citrus/Floral/Oud. "Pride of origin, rooted identity."

NAYAT COLLECTION
• Aala Taj Warda — Summer evenings. Saffron-Cinnamon/Rose/Warm spicy. "Passion, rise, grandeur."
• Aala Sathi Al Qamar — Men gifting. White flowers/Musk-Sandalwood. "Joy, glow."
• Fakhamat Al Warda — Women. Rose/Fresh florals/Soft woods. "Royal elegance, visible status."
• Hadeeth Al Rooh — Women. Warm spices/Oriental woods/Amber. "Inner depth, soulfulness."
• Hamsa — Women. Fruity/Patchouli/Sandalwood. "Warmth, social ease."
• Sarhan — Men top-seller. Saffron/Leather-Oud/Deep woods. "Vision, pioneering spirit."
• Tahta Al Noujoum — Women top-seller. Neroli/Orange blossom/Musk-rum. "Dreamy playful charm."
• Min Ana — Travel gifting. Oriental woods/Warm spices. "Self-discovery, individuality."
• Horr Fi Al Riyah — Women. Soft almond/Lily/Sandalwood-Amber. "Freedom, independence."

QANUN COLLECTION
• Safaa Al Nada — Men/family. Bergamot/Rose/Sandalwood. "Purity, calm clarity."
• Mamlakati — Winter. Musk/Strong woods/Vanilla. "Ownership, command."
• Al Hawa Ghallab — Women top-seller. Juniper-Saffron/Floral/Woody. "Magnetism, desire."
• Al Shaghaf Al Ahmar — Expressive. Spices/Rose/Woody. "Passion, intensity."

BUZUQ & RIQQ COLLECTION
• Khatiiiir — Men hero. Saffron/Leather-Rose/Oud-Frankincense. "Power, danger, bold charisma."
• Amtar — Women summer. Fruity/Patchouli/Sandalwood. "Fresh optimism, renewal."
• Thawrat Al Ahasseess — Men top-seller. Saffron/Rose/Oud-Incense. "Emotional intensity, rebellion."

EMOTIONAL MAP:
NOBILITY  → Shatha Biladi, Hams Min Al Sahraa, Al Shaghaf Al Ahmar
HAPPINESS → Tahta Al Noujoum, Naseem Al Ward
PLEASURE  → Aala Taj Warda, Hadeeth Al Rooh, Fakhamat Al Warda
PASSION   → Thawrat Al Ahasseess, Khatiiiir, Qublat Ward
DESIRE    → Safaa Al Nada, Al Hawa Ghallab, Mamlakati
PRIDE     → Sarhan, Min Ana

SERVICE STANDARDS:
- Warm greeting, no rushing
- Ask "For yourself or a gift?" before recommending
- Speak of notes as story, not chemistry
- Never rush — silence while smelling is sacred
- Close: "Shall I wrap this one for you, or try one more?"
"""

PROFILES = {
    1: {
        "emoji": "🧔", "name": "First-Time Browser", "name_ar": "زائر لأول مرة",
        "difficulty": 1,
        "brief": "Curious, no perfume knowledge. Needs gentle guidance.",
        "opening_en": "Hello… I've never bought an oud before. I was just walking past. Everything looks so expensive. Can you tell me what makes this different?",
        "opening_ar": "السلام عليكم… ما اشتريت عود من قبل. كنت أمشي وشفت المحل. كل شي يبدو غالي. وش اللي يخلي هذا مختلف؟",
        "persona": """You are a first-time browser in a luxury Arabian perfume boutique in Riyadh.
Curious but intimidated by price and the unfamiliar world of oud.
You know almost nothing about perfume notes.
You warm up ONLY when the salesperson slows down, discovers what YOU like, and tells a story.
If they rush or dump information you say: "I think I need to come back later."
Buy signal: confident recommendation of ONE bottle with a reason tied to your mood.
Objections: "It's a lot of money", "Is it too strong?", "I won't know if I like it."
Short natural sentences.""",
    },
    2: {
        "emoji": "👩", "name": "Gift Shopper", "name_ar": "مشتري هدية",
        "difficulty": 1,
        "brief": "Sister's birthday this weekend. Indecisive. Needs confident direction.",
        "opening_en": "I need a gift for my sister. Her birthday is this weekend. I honestly have no idea what she'd like. Help me — you pick something.",
        "opening_ar": "أبغى هدية لأختي. عيد ميلادها هذا الأسبوع. والله ما عندي فكرة. أنت اختار لي شي.",
        "persona": """You are shopping for your sister's birthday gift this weekend.
You don't wear perfume yourself. Your sister is elegant, quiet, works in an office.
You want the salesperson to TAKE CHARGE and reassure you.
You get annoyed at too many vague questions without direction.
You love: "For a sister who is elegant and composed, most gift-givers choose X because..."
Buy signal: they pick ONE bottle, justify in two sentences, mention wrapping.
Objections: "What if she already has this?", "Is this too personal?", "Can it be returned?"
Warm but in a hurry.""",
    },
    3: {
        "emoji": "👴", "name": "Oud Loyalist", "name_ar": "عاشق العود الكلاسيكي",
        "difficulty": 2,
        "brief": "Expert. 30 years of oud. Tests your knowledge ruthlessly.",
        "opening_en": "As-salamu alaykum. I've been wearing oud for thirty years. Tell me — what's the oud origin in Shatha Biladi? Cambodi? Hindi? And is it real oud or a reconstruction?",
        "opening_ar": "السلام عليكم. أنا ألبس عود من ثلاثين سنة. قول لي — العود في شذى بلادي من وين؟ كامبودي؟ هندي؟ وهو عود حقيقي ولا تركيب؟",
        "persona": """You are a Saudi gentleman, 50s, wearing oud daily for 30 years.
You own Ajmal, Arabian Oud, Amouage, Abdul Samad Al Qurashi.
Polite but testing. You catch bluffs about oud origins immediately.
Respect: genuine knowledge OR honest humility ("let me check with our perfumer").
Buy signal: real expertise shown OR humble offer to get expert backup.
Objections: "Higher price than Arabian Oud for less pedigree", "How do I know it's not synthetic?", "Who is your nose?"
Calm, formal, occasional Arabic: "ma sha Allah", "tayyib".""",
    },
}

LANG_OPTIONS = {
    "English 🇬🇧":  {"code": "en",    "gtts": "en"},
    "العربية 🇸🇦":   {"code": "ar",    "gtts": "ar"},
    "Mixed 🔀":      {"code": "mixed", "gtts": "ar"},
}

# ── database ────────────────────────────────────────────────────────────────────
engine = create_engine("sqlite:///mansam.db", connect_args={"check_same_thread": False})

def init_db():
    with engine.connect() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT, profile_id INTEGER, language TEXT,
            sale_score REAL, svc_score REAL, points INTEGER DEFAULT 0,
            transcript TEXT, debrief TEXT,
            created_at TEXT DEFAULT (datetime('now')))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS agents(
            name TEXT PRIMARY KEY,
            total_points INTEGER DEFAULT 0, sessions INTEGER DEFAULT 0)"""))
        c.commit()

init_db()

def upsert_agent(name):
    with engine.connect() as c:
        c.execute(text(
            "INSERT INTO agents(name) VALUES(:n) ON CONFLICT(name) DO NOTHING"), {"n": name})
        c.commit()

def save_session(agent, pid, lang, sale, svc, pts, transcript, debrief):
    with engine.connect() as c:
        c.execute(text("""INSERT INTO sessions
            (agent,profile_id,language,sale_score,svc_score,points,transcript,debrief)
            VALUES(:a,:p,:l,:s,:sv,:pt,:t,:db)"""),
            dict(a=agent, p=pid, l=lang, s=sale, sv=svc, pt=pts,
                 t=json.dumps(transcript), db=debrief))
        c.execute(text(
            "UPDATE agents SET total_points=total_points+:pt,sessions=sessions+1 WHERE name=:n"),
            {"pt": pts, "n": agent})
        c.commit()

def load_agent(name):
    with engine.connect() as c:
        row = c.execute(
            text("SELECT total_points,sessions FROM agents WHERE name=:n"),
            {"n": name}).fetchone()
    return dict(row._mapping) if row else {"total_points": 0, "sessions": 0}

# ── Groq ───────────────────────────────────────────────────────────────────────
def groq_client():
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try: key = st.secrets["GROQ_API_KEY"]
        except Exception: pass
    if not key:
        st.error("⚠️ Add GROQ_API_KEY to Streamlit Secrets.")
        st.stop()
    return Groq(api_key=key)

# ── TTS ────────────────────────────────────────────────────────────────────────
def tts_b64(text: str, lang: str, profile_id: int = 1):
    """Groq PlayAI TTS with gTTS fallback."""
    VOICE_MAP = {
        1: ("Fritz-PlayAI",  "Aaliya-PlayAI"),
        2: ("Arista-PlayAI", "Aaliya-PlayAI"),
        3: ("Mufasa-PlayAI", "Aaliya-PlayAI"),
    }
    en_v, ar_v = VOICE_MAP.get(profile_id, ("Fritz-PlayAI", "Aaliya-PlayAI"))
    voice = ar_v if lang in ("ar", "mixed") else en_v
    try:
        client = groq_client()
        resp = client.audio.speech.create(
            model="playai-tts", voice=voice,
            input=text, response_format="mp3")
        audio_bytes = (resp.content
                       if hasattr(resp, "content")
                       else b"".join(resp.iter_bytes()))
        return base64.b64encode(audio_bytes).decode()
    except Exception as e:
        logger.warning(f"Groq TTS failed ({e}), trying gTTS")
    try:
        l = "ar" if lang in ("ar", "mixed") else "en"
        buf = io.BytesIO()
        gTTS(text=text, lang=l, slow=False).write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        logger.warning(f"gTTS failed: {e}")
    return None

# ── STT ────────────────────────────────────────────────────────────────────────
def stt(audio_bytes: bytes, lang: str) -> str:
    hint = {"en": "en", "ar": "ar", "mixed": None}.get(lang)
    f = io.BytesIO(audio_bytes)
    f.name = "recording.webm"
    kw = dict(file=f, model="whisper-large-v3",
              response_format="text", temperature=0.0)
    if hint:
        kw["language"] = hint
    r = groq_client().audio.transcriptions.create(**kw)
    return (r if isinstance(r, str) else r.text).strip()

# ── LLM ────────────────────────────────────────────────────────────────────────
def customer_reply(profile, messages, lang) -> str:
    if lang == "ar":
        lang_rule = f"تكلّم فقط بالعربية السعودية العامية. جملة الافتتاح: {profile['opening_ar']}"
    elif lang == "mixed":
        lang_rule = f"Mix Saudi Arabic and English freely. Start: {profile['opening_ar']}"
    else:
        lang_rule = f"Speak natural English. Opening: {profile['opening_en']}"

    system = f"""{profile['persona']}
LANGUAGE: {lang_rule}
KNOWLEDGE BASE:\n{MANSAM_KB}
RULES:
- Stay in character. Never reveal you are an AI.
- MAX 2 short sentences per reply. Voice conversation — be concise.
- React warmly to good technique; push back on generic pitches."""

    msgs = [{"role": "system", "content": system}]
    if not messages:
        msgs.append({"role": "user",
                     "content": "[Session starts. Say your opening line — one sentence only.]"})
    else:
        msgs.extend(messages)

    r = groq_client().chat.completions.create(
        model=GROQ_MODEL, messages=msgs, max_tokens=90, temperature=0.9)
    return r.choices[0].message.content.strip()

def score_transcript(transcript, lang) -> dict:
    lang_note = {
        "ar":    "Arabic session — include Arabic fluency in Service.",
        "mixed": "Code-switching — reward natural blending in Service.",
        "en":    "English session.",
    }.get(lang, "")
    system = f"""Warm, encouraging sales coach for Mansam Parfumery. {lang_note}
{MANSAM_KB}
SALE (1-10): discovery, product knowledge, storytelling, objections, close.
SERVICE (1-10): warmth, patience, listening, cultural fit, pacing.
Tone: POSITIVE and ENCOURAGING. Find genuine praise. Frame growth as opportunity.
Return ONLY valid JSON:
{{"sale_score":<1-10>,"sale_justification":"<warm sentence>",
  "service_score":<1-10>,"service_justification":"<warm sentence>",
  "strong_points":["<moment>","<moment>","<moment>"],
  "growth_areas":[{{"observation":"<what>","tip":"<exact phrase>"}},
                  {{"observation":"<what>","tip":"<exact phrase>"}}],
  "next_challenge":"<profile + focus>",
  "encouragement":"<2 specific encouraging sentences>"}}"""
    tx = "\n".join(
        f"{'SALESPERSON' if m['role']=='user' else 'CUSTOMER'}: {m['content']}"
        for m in transcript)
    r = groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role":"system","content":system},
                  {"role":"user","content":f"Score:\n\n{tx}"}],
        max_tokens=700, temperature=0.15)
    raw = r.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```"); raw = parts[1] if len(parts)>1 else raw
        if raw.startswith("json"): raw = raw[4:].strip()
    return json.loads(raw)

# ── helpers ─────────────────────────────────────────────────────────────────────
def ss(k, d=None):  return st.session_state.get(k, d)
def sset(k, v):     st.session_state[k] = v

def topbar(right=""):
    pts = ss("total_points", 0)
    r   = right or (f"⭐ {pts} pts" if ss("agent_name") else "")
    st.markdown(
        f'<div class="topbar">'
        f'<span class="brand">🕌 Mansam Sales Coach</span>'
        f'<span class="pts">{r}</span></div>',
        unsafe_allow_html=True)

def fmt_time(s):
    m, sec = divmod(max(0, int(s)), 60)
    return f"{m}:{sec:02d}"

# ══════════════════════════════════════════════════════════════════════════════
# RECORDER COMPONENT
# One-button HTML5 recorder. Returns base64 WebM via Streamlit component value.
# No play / stop / download controls visible. Just the mic button.
# ══════════════════════════════════════════════════════════════════════════════
RECORDER_HTML = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:transparent;display:flex;flex-direction:column;
     align-items:center;padding:12px 0 8px;font-family:-apple-system,sans-serif}
#btn{
  width:82px;height:82px;border-radius:50%;
  background:#E8521A;border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 6px 24px rgba(232,82,26,.42);
  -webkit-tap-highlight-color:transparent;touch-action:manipulation;
  transition:transform .1s,background .15s;
  outline:none;
}
#btn:active{transform:scale(.93);}
#btn.recording{background:#B02A08;animation:pulse 1.1s infinite;}
#btn.processing{background:#888;cursor:not-allowed;}
@keyframes pulse{
  0%,100%{box-shadow:0 4px 18px rgba(176,42,8,.5);}
  50%{box-shadow:0 4px 44px rgba(176,42,8,.85);}
}
#hint{font-size:12px;color:#B0B0B0;margin-top:10px;
      letter-spacing:.04em;text-transform:uppercase;text-align:center;}
#err{font-size:11px;color:#E07000;margin-top:6px;text-align:center;display:none}
</style>

<button id="btn" title="Record">
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
       stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="9" y="2" width="6" height="12" rx="3"/>
    <path d="M5 10a7 7 0 0 0 14 0"/>
    <line x1="12" y1="19" x2="12" y2="22"/>
    <line x1="8"  y1="22" x2="16" y2="22"/>
  </svg>
</button>
<div id="hint">Tap to speak</div>
<div id="err"></div>

<script>
(function(){
  var btn   = document.getElementById('btn');
  var hint  = document.getElementById('hint');
  var err   = document.getElementById('err');
  var mr, stream, chunks=[], recording=false;

  btn.addEventListener('click', async function(){
    if(btn.classList.contains('processing')) return;

    if(!recording){
      // ── start ──
      err.style.display='none';
      try{
        stream = await navigator.mediaDevices.getUserMedia({
          audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}
        });
      }catch(e){
        err.textContent='Microphone access denied. Please allow mic and reload.';
        err.style.display='block'; return;
      }
      var mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
               ? 'audio/webm;codecs=opus' : 'audio/webm';
      mr = new MediaRecorder(stream,{mimeType:mime});
      chunks=[];
      mr.ondataavailable=function(e){if(e.data.size>0)chunks.push(e.data)};
      mr.onstop=function(){
        var blob = new Blob(chunks,{type:mr.mimeType});
        stream.getTracks().forEach(function(t){t.stop()});
        var reader = new FileReader();
        reader.onloadend=function(){
          var b64 = reader.result.split(',')[1];
          btn.classList.remove('recording');
          btn.classList.add('processing');
          hint.textContent='Processing…';
          // Send to Streamlit
          window.parent.postMessage({
            isStreamlitMessage:true,
            type:'streamlit:setComponentValue',
            value:b64
          },'*');
        };
        reader.readAsDataURL(blob);
      };
      mr.start();
      recording=true;
      btn.classList.add('recording');
      hint.textContent='Tap to stop';
    } else {
      // ── stop ──
      recording=false;
      if(mr && mr.state==='recording') mr.stop();
      hint.textContent='Sending…';
    }
  });

  // Reset button after Streamlit processes (re-renders component)
  // The component is re-rendered each turn with a new key, so this runs fresh.
})();
</script>
"""

# ══════════════════════════════════════════════════════════════════════════════
# SCREENS
# ══════════════════════════════════════════════════════════════════════════════

def screen_welcome():
    topbar()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## What's your name?")
    st.markdown(
        "<p style='color:#888;font-size:.88rem;margin:.2rem 0 1.2rem'>"
        "We'll track your progress and personalise your coaching.</p>",
        unsafe_allow_html=True)
    name = st.text_input("name", placeholder="Enter your name…",
                         label_visibility="collapsed", key="name_input")
    if st.button("Continue →"):
        if name.strip():
            sset("agent_name", name.strip())
            upsert_agent(name.strip())
            data = load_agent(name.strip())
            sset("total_points", data["total_points"])
            sset("screen", "pick_profile")
            st.rerun()
        else:
            st.warning("Please enter your name.")


def screen_pick_profile():
    topbar()
    st.markdown(f"<br><p style='color:#888;font-size:.85rem'>Hi {ss('agent_name','')} 👋</p>",
                unsafe_allow_html=True)
    st.markdown("## Choose your customer")
    st.markdown(
        "<p style='color:#888;font-size:.87rem;margin:.2rem 0 1.2rem'>"
        "You'll have a real sales conversation with this AI customer.</p>",
        unsafe_allow_html=True)
    for pid, p in PROFILES.items():
        dots = "●"*p["difficulty"] + "○"*(3-p["difficulty"])
        st.markdown(f"""
<div style="background:#fff;border-radius:14px;padding:1.1rem 1.2rem;
            margin-bottom:.5rem;box-shadow:0 1px 6px rgba(0,0,0,.06);
            display:flex;align-items:center;gap:1rem">
  <span style="font-size:2.2rem;line-height:1">{p['emoji']}</span>
  <div>
    <div style="font-weight:600;font-size:.97rem">{p['name']}</div>
    <div style="font-size:.78rem;color:#8C7A5A;margin:.1rem 0">{p['name_ar']}</div>
    <div style="font-size:.82rem;color:#888">{p['brief']}</div>
    <div style="font-size:.72rem;color:#C0C0C0;margin-top:.2rem">Difficulty: {dots}</div>
  </div>
</div>""", unsafe_allow_html=True)
        if st.button(f"Start with {p['name']}", key=f"p{pid}", use_container_width=True):
            sset("selected_profile", pid)
            sset("screen", "pick_language")
            st.rerun()


def screen_pick_language():
    topbar()
    pid = ss("selected_profile", 1)
    p   = PROFILES[pid]
    st.markdown(f"<br><p style='color:#888;font-size:.84rem'>{p['emoji']} {p['name']}</p>",
                unsafe_allow_html=True)
    st.markdown("## Session language")
    st.markdown(
        "<p style='color:#888;font-size:.87rem;margin:.2rem 0 1.3rem'>"
        "Speak however feels natural on your shop floor.</p>",
        unsafe_allow_html=True)
    for label, cfg in LANG_OPTIONS.items():
        if st.button(label, key=f"l{cfg['code']}", use_container_width=True):
            sset("session_lang", cfg["code"])
            sset("screen", "instructions")
            st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back", use_container_width=False):
        sset("screen", "pick_profile"); st.rerun()


def screen_instructions():
    topbar()
    pid  = ss("selected_profile", 1)
    p    = PROFILES[pid]
    lang = ss("session_lang", "en")
    ll   = {"en":"English","ar":"Arabic","mixed":"Arabic + English"}.get(lang)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"## Ready, {ss('agent_name','')}?")
    st.markdown(f"""
<div class="card-dark" style="margin-bottom:1.2rem">
  <p style="color:#C9A84C;font-weight:600;font-size:.78rem;
            text-transform:uppercase;letter-spacing:.07em;margin:0 0 .6rem">Your session</p>
  <p style="color:#E5E5E5;font-size:.92rem;line-height:1.8;margin:0">
    {p['emoji']} &nbsp;Customer: <b style="color:#fff">{p['name']}</b><br>
    🗣️ &nbsp;Language: <b style="color:#fff">{ll}</b><br>
    ⏱️ &nbsp;Duration: <b style="color:#fff">4 minutes</b>
  </p>
</div>""", unsafe_allow_html=True)
    steps = [
        ("Customer speaks first","Listen to their opening line."),
        ("Tap the orange button","Speak your response naturally."),
        ("Tap again to send","Customer replies automatically."),
        ("Keep going for 4 minutes","Natural back-and-forth."),
        ("Coaching at the end","Scores, strengths, personalised tips."),
    ]
    for i,(t,d) in enumerate(steps,1):
        st.markdown(f"""
<div style="display:flex;gap:.8rem;align-items:flex-start;margin:.45rem 0">
  <div style="min-width:24px;height:24px;border-radius:50%;background:#C9A84C;
              color:#1A1A1A;display:flex;align-items:center;justify-content:center;
              font-weight:700;font-size:.76rem;flex-shrink:0">{i}</div>
  <div style="font-size:.87rem;line-height:1.5;padding-top:.1rem">
    <b>{t}</b><br><span style="color:#888">{d}</span>
  </div>
</div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 Allow microphone when the browser asks — required once only.")
    if st.button("Start Session →", use_container_width=True):
        # Clean slate for new session
        for k in ["messages","session_start","opening_done","pending_audio",
                  "last_audio_hash","processing"]:
            if k in st.session_state: del st.session_state[k]
        sset("screen", "session")
        st.rerun()
    if st.button("← Change customer", use_container_width=False):
        sset("screen","pick_profile"); st.rerun()


def screen_session():
    # ── guard: if state missing go to welcome ─────────────────────────────────
    if not ss("selected_profile") or not ss("session_lang") or not ss("agent_name"):
        sset("screen","welcome"); st.rerun(); return

    pid  = ss("selected_profile", 1)
    p    = PROFILES[pid]
    lang = ss("session_lang", "en")
    is_rtl = lang in ("ar","mixed")
    ll   = {"en":"EN 🇬🇧","ar":"AR 🇸🇦","mixed":"Mixed 🔀"}.get(lang,"")

    # ── messages — always from session_state directly ─────────────────────────
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    msgs = st.session_state["messages"]

    # ── timer ─────────────────────────────────────────────────────────────────
    if "session_start" not in st.session_state:
        st.session_state["session_start"] = time.time()
    elapsed   = time.time() - st.session_state["session_start"]
    remaining = max(0.0, SESSION_SECS - elapsed)
    pct       = remaining / SESSION_SECS * 100
    bar_color = "#E07000" if remaining < 60 else "#C9A84C"
    t_color   = "#E07000" if remaining < 60 else "#888"
    sp_turns  = sum(1 for m in msgs if m["role"]=="user")

    # ── generate opening once ─────────────────────────────────────────────────
    if not st.session_state.get("opening_done"):
        st.session_state["opening_done"] = True
        with st.spinner(""):
            opening = customer_reply(p, [], lang)
        msgs.append({"role":"assistant","content":opening})
        st.session_state["messages"] = msgs
        st.session_state["pending_audio"] = tts_b64(opening, lang, pid)
        st.rerun(); return

    # ── auto-end when timer expires ───────────────────────────────────────────
    if remaining <= 0 and sp_turns >= 1:
        sset("screen","scoring"); st.rerun(); return

    # ── thin progress bar ─────────────────────────────────────────────────────
    st.markdown(
        f'<div style="height:3px;background:#E5E5E5;border-radius:2px;margin-bottom:.6rem">'
        f'<div style="height:3px;width:{pct:.1f}%;background:{bar_color};'
        f'border-radius:2px;transition:width .5s"></div></div>',
        unsafe_allow_html=True)

    # ── header ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:.3rem 0 .9rem">'
        f'<span style="font-size:.79rem;color:#888">{p["emoji"]} {p["name"]} · {ll}</span>'
        f'<span style="font-size:.79rem;color:{t_color};font-weight:500">'
        f'⏱ {fmt_time(remaining)}</span></div>',
        unsafe_allow_html=True)

    # ── customer bubble ───────────────────────────────────────────────────────
    last_msg = next(
        (m["content"] for m in reversed(msgs) if m["role"]=="assistant"), "…")
    cust_lbl  = "العميل" if is_rtl else "Customer"
    bdr       = "border-right:3px solid #C9A84C;border-left:none" if is_rtl else "border-left:3px solid #C9A84C"
    txt_dir   = "direction:rtl;text-align:right;" if is_rtl else ""

    st.markdown(
        f'<p style="font-size:.66rem;font-weight:600;color:#B0B0B0;'
        f'text-transform:uppercase;letter-spacing:.1em;margin:0 0 .45rem">{cust_lbl}</p>'
        f'<div style="background:#fff;border-radius:20px;padding:1.4rem 1.5rem;'
        f'font-size:1.05rem;line-height:1.7;color:#1A1A1A;'
        f'box-shadow:0 1px 10px rgba(0,0,0,.08);{bdr};{txt_dir}'
        f'word-wrap:break-word;overflow-wrap:break-word;margin-bottom:1rem">'
        f'{last_msg}</div>',
        unsafe_allow_html=True)

    # ── autoplay customer audio ────────────────────────────────────────────────
    if st.session_state.get("pending_audio"):
        b64a = st.session_state["pending_audio"]
        st.markdown(
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/mp3;base64,{b64a}" type="audio/mp3"></audio>',
            unsafe_allow_html=True)
        st.session_state["pending_audio"] = None

    # ── status / hint ─────────────────────────────────────────────────────────
    processing = st.session_state.get("processing", False)
    if processing:
        hint_txt = "جاري المعالجة…" if is_rtl else "Processing your response…"
        hint_col = "#C9A84C"
    elif sp_turns == 0:
        hint_txt = "اضغط للرد" if is_rtl else "Tap the button to respond"
        hint_col = "#B0B0B0"
    else:
        hint_txt = "اضغط للرد" if is_rtl else "Tap to respond"
        hint_col = "#B0B0B0"

    st.markdown(
        f'<p style="text-align:center;font-size:.75rem;color:{hint_col};'
        f'letter-spacing:.04em;text-transform:uppercase;margin:0 0 .4rem">'
        f'{hint_txt}</p>',
        unsafe_allow_html=True)

    # ── recorder component ────────────────────────────────────────────────────
    # Key changes each turn so the component resets cleanly after each recording.
    # This gives a fresh button with no leftover audio controls.
    turn_key = f"rec_{sp_turns}_{int(remaining)//10}"
    audio_b64 = components.html(RECORDER_HTML, height=130, key=turn_key)

    # ── done button ───────────────────────────────────────────────────────────
    st.markdown(
        '<p style="text-align:center;margin-top:.3rem;font-size:.82rem;color:#B0B0B0">'
        'or</p>',
        unsafe_allow_html=True)
    if st.button("Done — get my feedback", key="done_btn", use_container_width=True):
        if sp_turns >= 1:
            sset("screen","scoring"); st.rerun(); return
        else:
            st.toast("Have at least one exchange first 💪")
        return

    # ── process incoming audio ────────────────────────────────────────────────
    if audio_b64 and isinstance(audio_b64, str) and len(audio_b64) > 100:
        # Deduplicate with hash
        ahash = hashlib.md5(audio_b64.encode()).hexdigest()
        if ahash != st.session_state.get("last_audio_hash",""):
            st.session_state["last_audio_hash"] = ahash
            st.session_state["processing"] = True

            with st.spinner(""):
                try:
                    raw_bytes = base64.b64decode(audio_b64)
                    spoken    = stt(raw_bytes, lang)
                except Exception as e:
                    st.error(f"Transcription failed — please try again. ({e})")
                    st.session_state["processing"] = False
                    st.rerun(); return

                if spoken.strip():
                    msgs.append({"role":"user",      "content":spoken})
                    reply = customer_reply(p, msgs, lang)
                    msgs.append({"role":"assistant", "content":reply})
                    st.session_state["messages"]     = msgs
                    st.session_state["pending_audio"] = tts_b64(reply, lang, pid)

            st.session_state["processing"] = False
            st.rerun()


def screen_scoring():
    topbar()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## Analysing your session…")
    st.markdown(
        "<p style='color:#888;font-size:.88rem'>"
        "Your coach is reviewing the conversation.</p>",
        unsafe_allow_html=True)
    msgs = ss("messages", [])
    lang = ss("session_lang","en")
    pid  = ss("selected_profile",1)
    with st.spinner(""):
        try:
            scores = score_transcript(msgs, lang)
        except Exception as e:
            st.error(f"Scoring error: {e}")
            if st.button("Retry"): st.rerun()
            return
    perf = int((scores["sale_score"]+scores["service_score"])*5)
    pts  = 10 + perf
    save_session(ss("agent_name",""), pid, lang,
                 scores["sale_score"], scores["service_score"],
                 pts, msgs, json.dumps(scores))
    sset("last_scores", scores)
    sset("last_points", pts)
    sset("total_points", ss("total_points",0)+pts)
    sset("screen","debrief")
    st.rerun()


def screen_debrief():
    scores = ss("last_scores",{})
    pts    = ss("last_points",10)
    name   = ss("agent_name","")
    lang   = ss("session_lang","en")
    pid    = ss("selected_profile",1)
    p      = PROFILES[pid]
    sale   = scores.get("sale_score",0)
    svc    = scores.get("service_score",0)
    enc    = scores.get("encouragement","")

    topbar(f"⭐ {ss('total_points',0)} pts total")

    st.markdown(f"""<br>
<div class="card-dark" style="text-align:center">
  <div style="font-size:2.2rem;margin-bottom:.4rem">🎉</div>
  <div style="font-size:1.35rem;font-weight:700;color:#C9A84C;margin-bottom:.2rem">
    Well done, {name}!</div>
  <div style="color:#888;font-size:.84rem">{p['emoji']} {p['name']} · session complete</div>
</div>""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="score-pair">
  <div class="score-card">
    <div class="num">{sale}<span style="font-size:1rem;color:#C0C0C0">/10</span></div>
    <div class="lbl">Sale</div>
    <div class="just">{scores.get("sale_justification","")}</div>
  </div>
  <div class="score-card">
    <div class="num">{svc}<span style="font-size:1rem;color:#C0C0C0">/10</span></div>
    <div class="lbl">Service</div>
    <div class="just">{scores.get("service_justification","")}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown(
        f'<div style="background:#1A1A1A;color:#fff;border-radius:12px;'
        f'padding:.85rem 1rem;text-align:center;font-weight:600;font-size:.97rem;'
        f'margin-bottom:.9rem">⭐ +{pts} points earned</div>',
        unsafe_allow_html=True)

    if enc:
        st.markdown(
            f'<div class="card" style="border-left:3px solid #C9A84C;'
            f'font-size:.9rem;line-height:1.6">{enc}</div>',
            unsafe_allow_html=True)

    strongs = scores.get("strong_points",[])
    if strongs:
        st.markdown(
            '<p style="font-size:.72rem;font-weight:600;color:#B0B0B0;'
            'text-transform:uppercase;letter-spacing:.09em;margin:.6rem 0 .35rem">'
            'What you did well</p>', unsafe_allow_html=True)
        chips = "".join(f'<span class="chip">{s}</span>' for s in strongs)
        st.markdown(f'<div style="margin-bottom:.8rem">{chips}</div>',
                    unsafe_allow_html=True)

    grows = scores.get("growth_areas",[])
    if grows:
        st.markdown(
            '<p style="font-size:.72rem;font-weight:600;color:#B0B0B0;'
            'text-transform:uppercase;letter-spacing:.09em;margin:.6rem 0 .35rem">'
            'One thing to try next time</p>', unsafe_allow_html=True)
        for g in grows:
            st.markdown(
                f'<div class="grow-item">{g.get("observation","")}'
                f'<div class="try">Try: &ldquo;{g.get("tip","")}&rdquo;</div></div>',
                unsafe_allow_html=True)

    nxt = scores.get("next_challenge","")
    if nxt:
        st.markdown(
            f'<div style="background:#FBF6E9;border-radius:12px;padding:.85rem 1rem;'
            f'margin-top:.5rem;font-size:.87rem;color:#8B6914">'
            f'🎯 <b>Next challenge:</b> {nxt}</div>',
            unsafe_allow_html=True)

    # audio summary
    summary = (f"Well done {name}. Sale score {sale}, service score {svc}. "
               f"You earned {pts} points. {enc}")
    with st.spinner(""):
        b64 = tts_b64(summary, "en")
    if b64:
        st.markdown('<hr class="div">', unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:.75rem;color:#B0B0B0;margin-bottom:.3rem">'
            '🔊 Hear your feedback</p>', unsafe_allow_html=True)
        st.markdown(
            f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Practice Again →", use_container_width=True):
        for k in ["messages","session_start","opening_done","pending_audio",
                  "last_audio_hash","processing","last_scores","last_points",
                  "session_lang","selected_profile"]:
            if k in st.session_state: del st.session_state[k]
        sset("screen","pick_profile"); st.rerun()

    st.markdown('<p style="text-align:center;margin-top:.6rem">', unsafe_allow_html=True)
    if st.button("Switch agent", use_container_width=False):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.markdown('</p>', unsafe_allow_html=True)


# ── router ──────────────────────────────────────────────────────────────────────
def main():
    screen = ss("screen","welcome")
    {
        "welcome":       screen_welcome,
        "pick_profile":  screen_pick_profile,
        "pick_language": screen_pick_language,
        "instructions":  screen_instructions,
        "session":       screen_session,
        "scoring":       screen_scoring,
        "debrief":       screen_debrief,
    }.get(screen, screen_welcome)()

if __name__ == "__main__":
    main()
