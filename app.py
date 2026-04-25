"""
Mansam Parfumery — Voice Sales Coach
=====================================
Minimal, Claude-inspired UI.
One message at a time. Big mic button. Nothing else.

Groq secret:  GROQ_API_KEY = "gsk_..."
"""

import os, io, json, base64, time
import streamlit as st
from groq import Groq
from gtts import gTTS
from loguru import logger
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ── page config ────────────────────────────────────────────────────────────────
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

/* ── reset to clean white ── */
html, body, [class*="css"], .stApp {
    background: #F5F5F5 !important;
    color: #1A1A1A !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.block-container {
    max-width: 480px !important;
    padding: 0 1.2rem 2rem !important;
    margin: 0 auto !important;
}
#MainMenu, footer, header,
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"] { display: none !important; }

/* ── top bar ── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0 .5rem;
    border-bottom: 1px solid #E5E5E5;
    margin-bottom: 1.5rem;
}
.topbar .brand {
    font-size: .9rem;
    font-weight: 500;
    color: #1A1A1A;
    letter-spacing: .01em;
}
.topbar .pts {
    font-size: .82rem;
    color: #888;
}

/* ── single large name input ── */
.stTextInput input {
    background: #fff !important;
    color: #1A1A1A !important;
    border: 1.5px solid #E0E0E0 !important;
    border-radius: 14px !important;
    font-size: 16px !important;
    padding: .9rem 1rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.06) !important;
}
.stTextInput input:focus {
    border-color: #C9A84C !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,.15) !important;
}
.stTextInput input::placeholder { color: #B0B0B0 !important; }

/* ── primary button ── */
.stButton > button {
    background: #1A1A1A !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: .95rem !important;
    min-height: 52px !important;
    width: 100% !important;
    letter-spacing: .01em !important;
    transition: background .15s !important;
}
.stButton > button:hover { background: #333 !important; }

/* ── profile pill buttons ── */
.profile-btn {
    background: #fff;
    border: 1.5px solid #E0E0E0;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    margin-bottom: .7rem;
    cursor: pointer;
    transition: border-color .15s, box-shadow .15s;
    display: flex;
    align-items: center;
    gap: .9rem;
}
.profile-btn:hover { border-color: #C9A84C; box-shadow: 0 0 0 3px rgba(201,168,76,.12); }
.profile-btn .emo { font-size: 1.6rem; }
.profile-btn .info .name { font-weight: 600; font-size: .95rem; color: #1A1A1A; }
.profile-btn .info .sub  { font-size: .78rem; color: #888; margin-top: 1px; }

/* ── language buttons ── */
.lang-row { display: flex; gap: .6rem; margin-bottom: 1.2rem; flex-wrap: wrap; }
.lang-btn {
    flex: 1; min-width: 100px;
    background: #fff; border: 1.5px solid #E0E0E0;
    border-radius: 12px; padding: .7rem .5rem;
    text-align: center; cursor: pointer;
    font-size: .88rem; font-weight: 500; color: #1A1A1A;
    transition: border-color .15s;
}
.lang-btn.selected { border-color: #C9A84C; background: #FBF6E9; color: #8B6914; }

/* ── the main conversation bubble ── */
.msg-bubble {
    background: #fff;
    border-radius: 20px;
    padding: 1.4rem 1.5rem;
    font-size: 1.05rem;
    line-height: 1.65;
    color: #1A1A1A;
    box-shadow: 0 1px 6px rgba(0,0,0,.07);
    min-height: 90px;
    margin-bottom: 1rem;
    position: relative;
}
.msg-bubble .speaker {
    font-size: .72rem;
    font-weight: 600;
    color: #B0B0B0;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: .5rem;
}
.msg-bubble.customer { border-left: 3px solid #C9A84C; }
.msg-bubble.you-said  { background: #FAFAFA; border-left: 3px solid #E0E0E0; font-size: .9rem; color: #555; }

/* ── status text ── */
.status-txt {
    text-align: center;
    font-size: .82rem;
    color: #B0B0B0;
    letter-spacing: .04em;
    text-transform: uppercase;
    margin: .5rem 0 1.2rem;
    min-height: 1.2rem;
}

/* ── timer bar ── */
.timer-bar-wrap {
    background: #E5E5E5;
    border-radius: 4px;
    height: 4px;
    margin-bottom: 1.5rem;
    overflow: hidden;
}
.timer-bar-fill {
    height: 4px;
    border-radius: 4px;
    background: #C9A84C;
    transition: width .5s linear, background .3s;
}

/* ── mic button — THE STAR ── */
.mic-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: .5rem;
}
.mic-btn {
    width: 72px; height: 72px;
    border-radius: 50%;
    background: #E8521A;    /* Claude orange */
    border: none;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(232,82,26,.35);
    transition: transform .12s, box-shadow .12s;
}
.mic-btn:hover  { transform: scale(1.06); box-shadow: 0 6px 20px rgba(232,82,26,.45); }
.mic-btn:active { transform: scale(.96); }
.mic-btn.recording {
    background: #C0320A;
    box-shadow: 0 4px 24px rgba(192,50,10,.6);
    animation: pulse 1.2s infinite;
}
@keyframes pulse {
    0%,100% { box-shadow: 0 4px 16px rgba(192,50,10,.5); }
    50%      { box-shadow: 0 4px 32px rgba(192,50,10,.85); }
}
.mic-btn svg { pointer-events: none; }
.mic-hint {
    font-size: .78rem; color: #B0B0B0;
    margin-top: .65rem; letter-spacing: .03em;
}

/* ── debrief / summary ── */
.score-row {
    display: flex; gap: .8rem; margin-bottom: 1rem;
}
.score-card {
    flex: 1; background: #fff; border-radius: 14px;
    padding: 1.1rem .8rem; text-align: center;
    box-shadow: 0 1px 6px rgba(0,0,0,.06);
}
.score-card .num {
    font-size: 2rem; font-weight: 700; color: #1A1A1A;
    line-height: 1;
}
.score-card .lbl {
    font-size: .72rem; color: #B0B0B0;
    text-transform: uppercase; letter-spacing: .08em;
    margin-top: .3rem;
}
.enc-box {
    background: #fff; border-radius: 14px;
    padding: 1.1rem 1.2rem; margin-bottom: .8rem;
    font-size: .92rem; line-height: 1.6; color: #1A1A1A;
    box-shadow: 0 1px 6px rgba(0,0,0,.06);
}
.chip {
    display: inline-block; background: #FBF6E9;
    color: #8B6914; border-radius: 20px;
    padding: 4px 12px; font-size: .78rem; font-weight: 500;
    margin: 3px 2px;
}
.grow-row {
    background: #fff; border-radius: 14px;
    padding: 1rem 1.1rem; margin-bottom: .6rem;
    font-size: .88rem; line-height: 1.55; color: #1A1A1A;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
    border-left: 3px solid #E0E0E0;
}
.grow-row .try-line {
    margin-top: .35rem; font-style: italic;
    color: #C9A84C; font-size: .85rem;
}
.pts-pill {
    background: #1A1A1A; color: #fff;
    border-radius: 12px; padding: .9rem 1rem;
    text-align: center; font-weight: 600;
    font-size: 1rem; margin-bottom: 1rem;
}

/* ── divider ── */
.div { border: none; border-top: 1px solid #E5E5E5; margin: 1.2rem 0; }

/* ── small back link ── */
.back-link {
    font-size: .82rem; color: #B0B0B0;
    cursor: pointer; text-decoration: underline;
    background: none; border: none; padding: 0;
}
audio { width: 100%; height: 36px; border-radius: 8px; margin: .4rem 0; accent-color: #C9A84C; }
</style>
""", unsafe_allow_html=True)

# ── constants ──────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
SESSION_SECS = 4 * 60   # 4 minutes

PROFILES = {
    1: {
        "emoji": "👀", "name": "First-Time Browser", "name_ar": "زائر لأول مرة",
        "brief": "Curious, no perfume knowledge. Needs gentle guidance.",
        "opening_en": "Hi… I'm just looking. I don't really know much about perfumes.",
        "opening_ar": "السلام عليكم… أنا بس أتفرج. ما عندي معرفة كثير بالعطور.",
        "personality": "Shy, easily overwhelmed. Warms up with warmth and simplicity.",
        "objections_en": ["I don't know what I like.", "Too many choices.", "Is it expensive?"],
        "objections_ar": ["ما أعرف وش أحب.", "في خيارات كثير.", "غالي؟"],
        "buy_signal": "Asks 'do you think this suits me?' or lingers on a scent.",
        "difficulty": 1,
    },
    2: {
        "emoji": "🎁", "name": "Gift Shopper", "name_ar": "مشتري هدية",
        "brief": "Buying for someone else. Indecisive, anxious to choose right.",
        "opening_en": "I need a gift for my sister. No idea what she'd like.",
        "opening_ar": "أبغى هدية لأختي. ما عندي فكرة وش تحب.",
        "personality": "Grateful for confident guidance. Anxious about getting it wrong.",
        "objections_en": ["She might not like oud.", "What if she has it?", "Too expensive?"],
        "objections_ar": ["ممكن ما تحب العود.", "إذا عندها؟", "غالي للهدية؟"],
        "buy_signal": "Says 'that sounds perfect for her' or asks about gift wrapping.",
        "difficulty": 1,
    },
    3: {
        "emoji": "🏺", "name": "Oud Loyalist", "name_ar": "عاشق العود",
        "brief": "Expert buyer. Tests your knowledge. Respects authenticity.",
        "opening_en": "I've worn Saudi oud for twenty years. Show me what you have.",
        "opening_ar": "أنا ألبس عود سعودي من عشرين سنة. وريني عندكم إيش.",
        "personality": "Confident, discerning. Dismisses generic pitches. Rewards real expertise.",
        "objections_en": ["What makes yours different?", "Smells synthetic.", "I don't trust modern perfumery."],
        "objections_ar": ["وش اللي يميزكم؟", "تبيّن مركّب.", "ما أثق بعطور العصر."],
        "buy_signal": "Pauses, inhales deeply, asks about oud origin.",
        "difficulty": 2,
    },
}

KNOWLEDGE_BASE = """
MANSAM PARFUMERY
Brand: Luxury Arabian perfumery. Heritage of the Arabian Peninsula. Authentic luxury, never imitation.

SERVICE:
- Greet warmly within 30 seconds
- Ask "For yourself or a gift?" before recommending
- Offer scent strip before price
- Never rush — silence while smelling is sacred
- Close: "I think this one found you."

PRODUCTS:
1. Al Majd (العظمة) — Oud & Rose | Extrait | 30ml SAR650 / 50ml SAR950
   Story: Named for glory. Worn at weddings and royal gatherings for generations.
2. Sahara Musk — White Musk & Sandalwood | EDP | 50ml SAR380 / 100ml SAR520
   Story: Whisper of the desert at dawn. Perfect for daily wear and gifts.
3. Darb Al Hind (درب الهند) — Spiced Oud | EDP Intense | 50ml SAR820
   Story: The ancient incense trade route. Bold, complex, unforgettable.

OBJECTIONS:
- Price: Extrait = 12-14h wear. More economical per use than it looks.
- Oud hesitation: Start with Sahara Musk — soft, no smoke, just warmth.
- Already has perfume: Great collections need variety. This is for occasions to remember.

RULE: Open with place or story — never with price.
"""

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
            name TEXT PRIMARY KEY, total_points INTEGER DEFAULT 0, sessions INTEGER DEFAULT 0)"""))
        c.commit()

init_db()

def upsert_agent(name):
    with engine.connect() as c:
        c.execute(text("INSERT INTO agents(name) VALUES(:n) ON CONFLICT(name) DO NOTHING"), {"n": name})
        c.commit()

def save_session(agent, pid, lang, sale, svc, pts, transcript, debrief):
    with engine.connect() as c:
        c.execute(text("""INSERT INTO sessions
            (agent,profile_id,language,sale_score,svc_score,points,transcript,debrief)
            VALUES(:a,:p,:l,:s,:sv,:pt,:t,:db)"""),
            dict(a=agent, p=pid, l=lang, s=sale, sv=svc, pt=pts,
                 t=json.dumps(transcript), db=debrief))
        c.execute(text("UPDATE agents SET total_points=total_points+:pt, sessions=sessions+1 WHERE name=:n"),
                  {"pt": pts, "n": agent})
        c.commit()

# ── Groq ───────────────────────────────────────────────────────────────────────
def groq_client():
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try: key = st.secrets["GROQ_API_KEY"]
        except: pass
    if not key:
        st.error("⚠️ Add GROQ_API_KEY to Streamlit secrets.")
        st.stop()
    return Groq(api_key=key)

def tts_b64(text: str, lang: str) -> str | None:
    l = "ar" if lang in ("ar", "mixed") else "en"
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=l, slow=False).write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        logger.warning(f"TTS: {e}"); return None

def stt(audio_b64: str, lang: str) -> str:
    raw = base64.b64decode(audio_b64)
    hint = {"en": "en", "ar": "ar", "mixed": None}.get(lang)
    f = io.BytesIO(raw); f.name = "r.webm"
    kw = dict(file=f, model="whisper-large-v3", response_format="text", temperature=0.0)
    if hint: kw["language"] = hint
    r = groq_client().audio.transcriptions.create(**kw)
    return (r if isinstance(r, str) else r.text).strip()

def customer_reply(profile, messages, lang) -> str:
    if lang == "ar":
        lang_rule = (f"تكلّم فقط بالعربية السعودية العامية. "
                     f"جملة الافتتاح: {profile['opening_ar']} "
                     f"اعتراضاتك: {' | '.join(profile['objections_ar'])}")
    elif lang == "mixed":
        lang_rule = f"Mix Saudi Arabic and English. Start: {profile['opening_ar']}"
    else:
        lang_rule = (f"Speak natural English. Opening: {profile['opening_en']} "
                     f"Objections: {' | '.join(profile['objections_en'])}")

    sys = f"""You are a customer at Mansam Parfumery in Saudi Arabia.
PROFILE: {profile['name']} — {profile['personality']}
BUY SIGNAL: {profile['buy_signal']}
LANGUAGE: {lang_rule}
{KNOWLEDGE_BASE}
RULES:
- Stay in character. Never reveal you are an AI.
- MAX 2 short sentences per reply. This is voice — be natural and brief.
- React warmly to good technique; push back on generic or rushed pitches.
"""
    msgs = [{"role": "system", "content": sys}]
    if not messages:
        msgs.append({"role": "user", "content": "[Session starts. Say your opening line — one sentence only.]"})
    else:
        msgs.extend(messages)
    r = groq_client().chat.completions.create(
        model=GROQ_MODEL, messages=msgs, max_tokens=90, temperature=0.9)
    return r.choices[0].message.content.strip()

def score_transcript(transcript, lang) -> dict:
    lang_note = {"ar": "Arabic session — include Arabic fluency in Service.",
                 "mixed": "Code-switching — reward natural blending.",
                 "en": "English session."}.get(lang, "")
    sys = f"""Warm, encouraging sales coach for Mansam Parfumery. {lang_note}
{KNOWLEDGE_BASE}
SALE (1-10): needs discovery, product knowledge, storytelling, objections, close.
SERVICE (1-10): warmth, patience, listening, cultural appropriateness.
Return ONLY valid JSON:
{{"sale_score":<1-10>,"sale_justification":"<one warm sentence>",
  "service_score":<1-10>,"service_justification":"<one warm sentence>",
  "strong_points":["<specific moment>","<specific moment>","<specific moment>"],
  "growth_areas":[{{"observation":"<what happened>","tip":"<exact phrase to try next time>"}},
                  {{"observation":"<what happened>","tip":"<exact phrase to try next time>"}}],
  "next_challenge":"<which profile + what to focus on>",
  "encouragement":"<2 sentences of genuine warm encouragement>"}}"""
    tx = "\n".join(f"{'SALESPERSON' if m['role']=='user' else 'CUSTOMER'}: {m['content']}" for m in transcript)
    r = groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role":"system","content":sys},{"role":"user","content":f"Score:\n\n{tx}"}],
        max_tokens=700, temperature=0.15)
    raw = r.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```"); raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"): raw = raw[4:].strip()
    return json.loads(raw)

# ── state ───────────────────────────────────────────────────────────────────────
def ss(k, d=None): return st.session_state.get(k, d)
def sset(k, v): st.session_state[k] = v

# ── top bar ─────────────────────────────────────────────────────────────────────
def topbar(right_text=""):
    pts_str = f"⭐ {ss('total_points',0)} pts" if ss("agent_name") else ""
    right = right_text or pts_str
    st.markdown(f"""
    <div class="topbar">
        <span class="brand">🕌 Mansam Sales Coach</span>
        <span class="pts">{right}</span>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — WELCOME
# ══════════════════════════════════════════════════════════════════════════════
def screen_welcome():
    topbar()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## What's your name?")
    st.markdown("<p style='color:#888;font-size:.9rem;margin-top:-.4rem;margin-bottom:1.2rem'>"
                "We'll track your progress and personalise your coaching.</p>",
                unsafe_allow_html=True)

    name = st.text_input("name", placeholder="Enter your name…",
                         label_visibility="collapsed", key="name_input")

    if st.button("Continue →"):
        if name.strip():
            sset("agent_name", name.strip())
            upsert_agent(name.strip())
            sset("screen", "pick_profile")
            st.rerun()
        else:
            st.warning("Please enter your name.")

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — PICK PROFILE
# ══════════════════════════════════════════════════════════════════════════════
def screen_pick_profile():
    topbar()
    st.markdown(f"<br><p style='color:#888;font-size:.85rem'>Hi {ss('agent_name','')} 👋</p>",
                unsafe_allow_html=True)
    st.markdown("## Choose your customer")
    st.markdown("<p style='color:#888;font-size:.88rem;margin-top:-.3rem;margin-bottom:1.2rem'>"
                "You'll practice a real sales conversation with this AI customer.</p>",
                unsafe_allow_html=True)

    for pid, p in PROFILES.items():
        diff_dots = "●" * p["difficulty"] + "○" * (3 - p["difficulty"])
        st.markdown(f"""
        <div class="profile-btn">
            <span class="emo">{p['emoji']}</span>
            <div class="info">
                <div class="name">{p['name']}</div>
                <div class="sub">{p['brief']} &nbsp;·&nbsp; {diff_dots}</div>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Start with {p['name']}", key=f"p{pid}", use_container_width=True):
            sset("selected_profile", pid)
            sset("screen", "pick_language")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — PICK LANGUAGE
# ══════════════════════════════════════════════════════════════════════════════
def screen_pick_language():
    topbar()
    pid = ss("selected_profile", 1)
    p   = PROFILES[pid]
    st.markdown(f"<br><p style='color:#888;font-size:.85rem'>{p['emoji']} {p['name']}</p>",
                unsafe_allow_html=True)
    st.markdown("## Session language")
    st.markdown("<p style='color:#888;font-size:.88rem;margin-top:-.3rem;margin-bottom:1.4rem'>"
                "Speak however feels natural on your shop floor.</p>",
                unsafe_allow_html=True)

    langs = [("English","en","🇬🇧"), ("Arabic","ar","🇸🇦"), ("Mixed","mixed","🔀")]
    for label, code, flag in langs:
        if st.button(f"{flag}  {label}", key=f"l{code}", use_container_width=True):
            sset("session_lang", code)
            sset("screen", "instructions")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back", use_container_width=False):
        sset("screen", "pick_profile"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — INSTRUCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def screen_instructions():
    topbar()
    pid  = ss("selected_profile", 1)
    p    = PROFILES[pid]
    lang = ss("session_lang", "en")
    ll   = {"en": "English", "ar": "Arabic", "mixed": "Arabic + English"}.get(lang)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## How it works")
    st.markdown(f"""
    <div style="background:#fff;border-radius:14px;padding:1.2rem 1.3rem;
                margin-bottom:1.2rem;box-shadow:0 1px 6px rgba(0,0,0,.06)">
        <p style="margin:0 0 .6rem;font-size:.85rem;color:#B0B0B0;font-weight:600;
                  text-transform:uppercase;letter-spacing:.07em">Your session</p>
        <p style="margin:0;font-size:.95rem;color:#1A1A1A;line-height:1.7">
            🎭 &nbsp;Customer: <b>{p['name']}</b><br>
            🗣️ &nbsp;Language: <b>{ll}</b><br>
            ⏱️ &nbsp;4 minutes
        </p>
    </div>
    <div style="font-size:.9rem;color:#555;line-height:1.8">
        <p>① The customer speaks first — listen.</p>
        <p>② Tap the <span style="background:#E8521A;color:#fff;border-radius:50%;
           padding:1px 7px;font-size:.8rem">●</span> button and speak your response.</p>
        <p>③ Release — the customer replies automatically.</p>
        <p>④ Keep going naturally for 4 minutes.</p>
        <p>⑤ You'll see your coaching summary at the end.</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Start Session →", use_container_width=True):
        sset("messages", [])
        sset("session_start", time.time())
        sset("current_customer_text", "")
        sset("session_status", "starting")
        sset("screen", "session")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — LIVE SESSION  (hands-free voice component)
# ══════════════════════════════════════════════════════════════════════════════

# The JS component:
# - Shows only ONE bubble at a time (current customer message)
# - Big orange record button at the bottom
# - Hold-to-record OR tap-to-start / tap-to-stop (2 modes, auto-detected)
# - Thin gold progress bar at top
# - Sends audio b64 to Streamlit → STT → LLM → TTS → plays → next turn
# - No transcript clutter — just the current exchange

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — LIVE SESSION
# Architecture: Python drives everything. JS is display-only.
#
# Flow:
#   1. Python generates opening line + TTS on first load → stores in session_state
#   2. Page renders: shows customer bubble + plays audio via st.audio autoplay
#   3. st.audio_input mic button — user taps, speaks, taps stop
#   4. Streamlit reruns with audio data → STT → LLM → TTS → store → rerun → repeat
#   5. Timer tracked via session_state; session ends when time runs out
#   6. "End early" button navigates to scoring
#
# This approach has zero JS complexity and works 100% reliably on mobile.
# ══════════════════════════════════════════════════════════════════════════════

def fmt_time(secs):
    m, s = divmod(max(0, int(secs)), 60)
    return f"{m}:{s:02d}"


def screen_session():
    pid       = ss("selected_profile", 1)
    p         = PROFILES[pid]
    lang      = ss("session_lang", "en")
    msgs      = ss("messages", [])
    is_rtl    = lang in ("ar", "mixed")
    cust_lbl  = "العميل" if is_rtl else "Customer"
    ll        = {"en":"EN 🇬🇧","ar":"AR 🇸🇦","mixed":"Mixed 🔀"}.get(lang,"")

    # initialise timer
    if not ss("session_start"):
        sset("session_start", time.time())
    elapsed   = time.time() - ss("session_start")
    remaining = max(0.0, SESSION_SECS - elapsed)
    pct       = remaining / SESSION_SECS * 100
    bar_color = "#E07000" if remaining < 60 else "#C9A84C"
    time_color= "#E07000" if remaining < 60 else "#888"

    # auto-end
    if remaining <= 0 and len(msgs) >= 2:
        sset("screen", "scoring"); st.rerun()

    # ── generate opening once ─────────────────────────────────────────────────
    if not msgs:
        with st.spinner(""):
            opening = customer_reply(p, [], lang)
        msgs.append({"role": "assistant", "content": opening})
        sset("messages", msgs)
        b64 = tts_b64(opening, lang)
        sset("pending_audio", b64)
        st.rerun()

    last_customer = next(
        (m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "…"
    )
    turn_count = len([m for m in msgs if m["role"] == "user"])

    # ── page CSS (scoped, no leaking) ─────────────────────────────────────────
    st.markdown("""
<style>
/* hide ALL streamlit default chrome on session screen */
#MainMenu, footer, header,
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
div[data-testid="stHeader"] { display:none !important; }

/* remove top padding so bar sits flush */
.block-container { padding-top: 0 !important; padding-bottom: 120px !important; }

/* Style the native Streamlit mic button to look like Claude FAB */
div[data-testid="stAudioInput"] {
    position: fixed !important;
    bottom: 28px !important;
    right: 22px !important;
    z-index: 9999 !important;
    width: 72px !important;
    height: 72px !important;
}
div[data-testid="stAudioInput"] > div {
    width: 72px !important;
    height: 72px !important;
    border-radius: 50% !important;
    background: #E8521A !important;
    box-shadow: 0 4px 20px rgba(232,82,26,.45) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border: none !important;
}
/* hide label text, keep only icon */
div[data-testid="stAudioInput"] label,
div[data-testid="stAudioInput"] p,
div[data-testid="stAudioInput"] small { display: none !important; }
div[data-testid="stAudioInput"] button {
    width: 72px !important; height: 72px !important;
    border-radius: 50% !important;
    background: #E8521A !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(232,82,26,.45) !important;
}
div[data-testid="stAudioInput"] button svg {
    width: 28px !important; height: 28px !important;
    color: #fff !important; stroke: #fff !important;
}
</style>
""", unsafe_allow_html=True)

    # ── thin progress bar ─────────────────────────────────────────────────────
    st.markdown(f"""
<div style="height:3px;background:#E5E5E5;width:100%;margin-bottom:0">
  <div style="height:3px;width:{pct:.1f}%;background:{bar_color};transition:width .5s"></div>
</div>""", unsafe_allow_html=True)

    # ── small header row ──────────────────────────────────────────────────────
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:.55rem 1rem .4rem;border-bottom:1px solid #EBEBEB;
            margin-bottom:0">
  <span style="font-size:.8rem;color:#888">{p['emoji']} {p['name']} · {ll}</span>
  <span style="font-size:.8rem;color:{time_color};font-weight:500">⏱ {fmt_time(remaining)}</span>
</div>""", unsafe_allow_html=True)

    # ── customer bubble — full width, auto-height, no clipping ───────────────
    dir_style = "direction:rtl;text-align:right" if is_rtl else ""
    border    = "border-right:3px solid #C9A84C;border-left:none" if is_rtl else "border-left:3px solid #C9A84C"

    # Build style strings safely without injecting into f-string style attrs
    bubble_extra = "direction:rtl;text-align:right;" if is_rtl else ""
    bubble_border = (
        "border-right:3px solid #C9A84C;border-left:none;"
        if is_rtl else
        "border-left:3px solid #C9A84C;"
    )
    bubble_html = (
        '<div style="padding:1.2rem 1rem 0">'
        f'<p style="font-size:.68rem;font-weight:600;color:#B0B0B0;'
        f'text-transform:uppercase;letter-spacing:.1em;margin:0 0 .55rem">'
        f'{cust_lbl}</p>'
        f'<div style="background:#fff;border-radius:20px;padding:1.4rem 1.5rem;'
        f'font-size:1.05rem;line-height:1.7;color:#1A1A1A;'
        f'box-shadow:0 1px 10px rgba(0,0,0,.08);'
        f'{bubble_border}{bubble_extra}'
        f'word-wrap:break-word;overflow-wrap:break-word">'
        f'{last_customer}'
        f'</div></div>'
    )
    st.markdown(bubble_html, unsafe_allow_html=True)

    # ── autoplay audio ────────────────────────────────────────────────────────
    if ss("pending_audio"):
        b64 = ss("pending_audio")
        st.markdown(
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>',
            unsafe_allow_html=True)
        sset("pending_audio", None)

    # ── status hint ───────────────────────────────────────────────────────────
    if turn_count == 0:
        hint = "اضغط 🎙 للرد" if is_rtl else "Tap 🎙 to respond"
    else:
        hint = "اضغط للرد مرة أخرى" if is_rtl else "Tap mic to respond"

    st.markdown(f"""
<div style="text-align:center;padding:1rem 0 .5rem;
            font-size:.76rem;color:#C0C0C0;letter-spacing:.04em;
            text-transform:uppercase">{hint}</div>""", unsafe_allow_html=True)

    # ── end-early button ──────────────────────────────────────────────────────
    end_early = st.button("✓ Done — get my feedback", key="end_early_btn",
                          use_container_width=True)
    if end_early:
        if len(msgs) >= 3:
            sset("screen", "scoring"); st.rerun()
        else:
            st.toast("Have at least one exchange first 💪")

    # ── NATIVE mic input (hidden visually, triggered programmatically) ────────
    # Key increments each turn so widget resets after each recording
    audio_val = st.audio_input(
        "🎙",
        key=f"mic_{len(msgs)}",
        label_visibility="collapsed",
    )

    # ── process new recording ─────────────────────────────────────────────────
    if audio_val is not None:
        raw = audio_val.read()
        if raw and raw != ss("last_processed_bytes", b""):
            sset("last_processed_bytes", raw)
            with st.spinner(""):
                try:
                    spoken = stt(base64.b64encode(raw).decode(), lang)
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                    spoken = ""
                if spoken.strip():
                    msgs.append({"role": "user",      "content": spoken})
                    reply = customer_reply(p, msgs, lang)
                    msgs.append({"role": "assistant", "content": reply})
                    sset("messages", msgs)
                    sset("pending_audio", tts_b64(reply, lang))
                    sset("last_processed_bytes", b"")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 6 — SCORING
# ══════════════════════════════════════════════════════════════════════════════
def screen_scoring():
    topbar()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## Analysing your session…")
    st.markdown("<p style='color:#888;font-size:.9rem'>Your coach is reviewing the conversation.</p>",
                unsafe_allow_html=True)

    msgs = ss("messages", [])
    lang = ss("session_lang", "en")
    pid  = ss("selected_profile", 1)

    with st.spinner(""):
        try:
            scores = score_transcript(msgs, lang)
        except Exception as e:
            st.error(f"Scoring error: {e}")
            if st.button("Retry"): st.rerun()
            return

    perf = int((scores["sale_score"] + scores["service_score"]) * 5)
    pts  = 10 + perf
    save_session(ss("agent_name",""), pid, lang,
                 scores["sale_score"], scores["service_score"],
                 pts, msgs, json.dumps(scores))
    sset("last_scores", scores)
    sset("last_points", pts)
    sset("total_points", ss("total_points", 0) + pts)
    sset("screen", "debrief")
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 7 — DEBRIEF  (same screen, scroll down)
# ══════════════════════════════════════════════════════════════════════════════
def screen_debrief():
    topbar(f"⭐ {ss('total_points',0)} pts total")
    scores = ss("last_scores", {})
    pts    = ss("last_points", 10)
    name   = ss("agent_name", "")
    lang   = ss("session_lang", "en")
    pid    = ss("selected_profile", 1)
    p      = PROFILES[pid]
    sale   = scores.get("sale_score", 0)
    svc    = scores.get("service_score", 0)
    enc    = scores.get("encouragement", "")

    # ── greeting ──────────────────────────────────────────────────────────────
    st.markdown(f"<br>", unsafe_allow_html=True)
    st.markdown(f"## {name}, here's your coaching")
    st.markdown(f"<p style='color:#888;font-size:.88rem;margin-top:-.3rem'>"
                f"{p['emoji']} {p['name']} session complete.</p>",
                unsafe_allow_html=True)

    # ── scores ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="score-row">
        <div class="score-card">
            <div class="num">{sale}<span style="font-size:1rem;color:#B0B0B0">/10</span></div>
            <div class="lbl">Sale</div>
            <div style="font-size:.75rem;color:#888;margin-top:.4rem">{scores.get("sale_justification","")}</div>
        </div>
        <div class="score-card">
            <div class="num">{svc}<span style="font-size:1rem;color:#B0B0B0">/10</span></div>
            <div class="lbl">Service</div>
            <div style="font-size:.75rem;color:#888;margin-top:.4rem">{scores.get("service_justification","")}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── points ────────────────────────────────────────────────────────────────
    st.markdown(f'<div class="pts-pill">⭐ +{pts} points earned</div>', unsafe_allow_html=True)

    # ── coach message ─────────────────────────────────────────────────────────
    if enc:
        st.markdown(f'<div class="enc-box">{enc}</div>', unsafe_allow_html=True)

    # ── strong points as chips ────────────────────────────────────────────────
    strongs = scores.get("strong_points", [])
    if strongs:
        st.markdown('<p style="font-size:.78rem;font-weight:600;color:#B0B0B0;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.3rem">What you did well</p>', unsafe_allow_html=True)
        chips = "".join(f'<span class="chip">{s}</span>' for s in strongs)
        st.markdown(f"<div style='margin-bottom:.9rem'>{chips}</div>", unsafe_allow_html=True)

    # ── growth areas ──────────────────────────────────────────────────────────
    grows = scores.get("growth_areas", [])
    if grows:
        st.markdown('<p style="font-size:.78rem;font-weight:600;color:#B0B0B0;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.3rem">One thing to try next time</p>', unsafe_allow_html=True)
        for g in grows:
            st.markdown(f"""
            <div class="grow-row">
                {g.get("observation","")}
                <div class="try-line">Try: "{g.get("tip","")}"</div>
            </div>""", unsafe_allow_html=True)

    # ── next challenge ────────────────────────────────────────────────────────
    nxt = scores.get("next_challenge", "")
    if nxt:
        st.markdown(f"""
        <div style="background:#FBF6E9;border-radius:12px;padding:.9rem 1rem;
                    margin-top:.5rem;font-size:.88rem;color:#8B6914">
            🎯 <b>Next challenge:</b> {nxt}
        </div>""", unsafe_allow_html=True)

    # ── audio summary ─────────────────────────────────────────────────────────
    summary = (f"Great work {name}. Sale score {sale}, service score {svc}. "
               f"You earned {pts} points. {enc}")
    with st.spinner(""):
        b64 = tts_b64(summary, "en")
    if b64:
        st.markdown("<hr class='div'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:.78rem;color:#B0B0B0;margin-bottom:.3rem'>🔊 Hear your feedback</p>",
                    unsafe_allow_html=True)
        st.markdown(f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>',
                    unsafe_allow_html=True)

    # ── actions ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Practice Again →", use_container_width=True):
        for k in ["messages","session_start","last_scores","last_points",
                  "session_lang","selected_profile"]:
            sset(k, None)
        sset("screen", "pick_profile")
        st.rerun()

    st.markdown("<div style='text-align:center;margin-top:.8rem'>", unsafe_allow_html=True)
    if st.button("Switch agent", use_container_width=False):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ── router ──────────────────────────────────────────────────────────────────
def main():
    {
        "welcome":       screen_welcome,
        "pick_profile":  screen_pick_profile,
        "pick_language": screen_pick_language,
        "instructions":  screen_instructions,
        "session":       screen_session,
        "scoring":       screen_scoring,
        "debrief":       screen_debrief,
    }.get(ss("screen", "welcome"), screen_welcome)()

if __name__ == "__main__":
    main()
