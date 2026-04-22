"""
Mansam Parfumery — Voice-First AI Sales Coaching Agent
=======================================================
Completely rebuilt for smooth, continuous, voice-only experience.

Flow:
  WELCOME → pick profile + language → INSTRUCTIONS → LIVE SESSION (voice loop)
  → DEBRIEF (positive, encouraging)

LLM : Groq Llama 3.3 70B   (free)
STT : Groq Whisper large-v3 (free, same key)
TTS : gTTS                  (free, no key)

Secret needed:  GROQ_API_KEY = "gsk_..."
"""

import os, io, json, base64, datetime, time
import streamlit as st
from groq import Groq
from gtts import gTTS
from loguru import logger
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ─── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mansam Sales Coach",
    page_icon="🕌",
    layout="centered",          # centred = better mobile
    initial_sidebar_state="collapsed",
)

# ─── styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=Jost:wght@300;400;500;600&display=swap');

/* force light */
html,body,[class*="css"],.stApp{
    background:#FAF6EE !important;
    color:#1A1208 !important;
    font-family:'Jost',sans-serif !important;
}
h1,h2,h3{font-family:'Cormorant Garamond',serif !important; color:#1A1208 !important;}

/* hide streamlit chrome */
#MainMenu,footer,header,div[data-testid="stToolbar"]{display:none !important;}
div[data-testid="stDecoration"]{display:none !important;}
.block-container{padding-top:1.5rem !important; padding-bottom:2rem !important;}

/* ── inputs always light ── */
input,textarea{
    background:#fff !important; color:#1A1208 !important;
    border:1.5px solid #E8D5A3 !important; border-radius:6px !important;
    font-size:16px !important;   /* prevent iOS zoom */
}
input::placeholder{color:#A89070 !important;}

/* ── big gold button ── */
.stButton>button,.stFormSubmitButton>button{
    background:#C9A84C !important; color:#1A1208 !important;
    border:none !important; border-radius:8px !important;
    font-family:'Jost',sans-serif !important; font-weight:600 !important;
    font-size:1.05rem !important; letter-spacing:.05em !important;
    min-height:52px !important; width:100% !important;
    transition:background .18s !important;
}
.stButton>button:hover{background:#E8D5A3 !important;}

/* ── card ── */
.card{
    background:#fff; border:1.5px solid #E8D5A3; border-radius:12px;
    padding:1.4rem 1.6rem; margin-bottom:1rem;
    box-shadow:0 2px 8px rgba(0,0,0,.06);
}
.card-dark{
    background:#2E2415; border-radius:12px;
    padding:1.4rem 1.6rem; margin-bottom:1rem;
    color:#FAF6EE;
}

/* ── profile card ── */
.profile-card{
    background:#fff; border:2px solid #E8D5A3; border-radius:12px;
    padding:1.2rem; text-align:center; cursor:pointer;
    transition:border-color .18s, box-shadow .18s;
}
.profile-card:hover,.profile-card.selected{
    border-color:#C9A84C;
    box-shadow:0 0 0 3px rgba(201,168,76,.25);
}

/* ── timer ring ── */
.timer-wrap{
    display:flex; flex-direction:column; align-items:center;
    margin:1rem 0;
}
.timer-circle{
    width:120px; height:120px; border-radius:50%;
    border:6px solid #E8D5A3; display:flex;
    align-items:center; justify-content:center;
    font-size:2rem; font-weight:700; color:#1A1208;
    font-family:'Cormorant Garamond',serif;
    background:#fff; box-shadow:0 2px 12px rgba(0,0,0,.1);
    position:relative;
}
.timer-circle.active{ border-color:#C9A84C; }
.timer-circle.warning{ border-color:#E07000; color:#E07000; }
.timer-circle.done{ border-color:#8C7A5A; color:#8C7A5A; }
.timer-label{font-size:.78rem;color:#8C7A5A;margin-top:.4rem;letter-spacing:.08em;text-transform:uppercase;}

/* ── status pill ── */
.status-pill{
    display:inline-block; border-radius:20px; padding:5px 18px;
    font-size:.8rem; font-weight:600; letter-spacing:.06em;
    text-transform:uppercase; margin-bottom:.6rem;
}
.pill-listening{background:#D4EDDA;color:#155724;}
.pill-speaking{background:#FFF3CD;color:#856404;}
.pill-thinking{background:#D1ECF1;color:#0C5460;}
.pill-idle{background:#F5EDD6;color:#8C7A5A;}

/* ── chat bubble ── */
.bubble-customer{
    background:#2E2415; color:#FAF6EE;
    border-radius:16px 16px 16px 4px;
    padding:.8rem 1.1rem; margin:.4rem 0;
    max-width:88%; font-size:.95rem; line-height:1.55;
}
.bubble-you{
    background:#C9A84C; color:#1A1208;
    border-radius:16px 16px 4px 16px;
    padding:.8rem 1.1rem; margin:.4rem 0 .4rem auto;
    max-width:88%; font-size:.95rem; line-height:1.55;
    text-align:right;
}
.bubble-ar{direction:rtl; text-align:right;}

/* ── score card ── */
.score-ring{
    width:80px; height:80px; border-radius:50%;
    background:#2E2415; display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    margin:0 auto .4rem;
}
.score-ring .num{font-size:1.6rem;font-weight:700;color:#C9A84C;font-family:'Cormorant Garamond',serif;}
.score-ring .den{font-size:.7rem;color:#8C7A5A;}

/* ── debrief ── */
.debrief-section{margin:1rem 0;}
.debrief-section h4{color:#2E2415;font-size:1rem;font-weight:600;margin-bottom:.4rem;}
.debrief-item{
    background:#F5EDD6; border-left:3px solid #C9A84C;
    border-radius:0 6px 6px 0; padding:.6rem .9rem;
    margin:.3rem 0; font-size:.9rem; line-height:1.5;
}
.grow-item{
    background:#fff; border-left:3px solid #8C7A5A;
    border-radius:0 6px 6px 0; padding:.6rem .9rem;
    margin:.3rem 0; font-size:.9rem; line-height:1.5;
}
.points-badge{
    background:#C9A84C; color:#1A1208; border-radius:8px;
    padding:.8rem 1.2rem; text-align:center;
    font-size:1.1rem; font-weight:700; margin:.5rem 0;
}

/* ── top bar ── */
.top-bar{
    display:flex; align-items:center; justify-content:space-between;
    background:#2E2415; border-radius:10px;
    padding:.7rem 1.2rem; margin-bottom:1.2rem;
}
.top-bar .brand{color:#C9A84C;font-weight:700;font-size:1rem;letter-spacing:.06em;}
.top-bar .pts{color:#E8D5A3;font-size:.82rem;}

/* ── audio compact ── */
audio{height:36px;width:100%;border-radius:6px;margin:.3rem 0;accent-color:#C9A84C;}

/* ── divider ── */
.gold-line{border:none;border-top:1.5px solid #E8D5A3;margin:1rem 0;}

/* ── instruction steps ── */
.step{display:flex;gap:.8rem;align-items:flex-start;margin:.6rem 0;}
.step-num{
    min-width:28px;height:28px;border-radius:50%;
    background:#C9A84C;color:#1A1208;
    display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:.85rem;flex-shrink:0;
}
.step-text{font-size:.9rem;line-height:1.5;padding-top:.1rem;}
</style>
""", unsafe_allow_html=True)

# ─── constants ─────────────────────────────────────────────────────────────────
GROQ_MODEL    = "llama-3.3-70b-versatile"
SESSION_SECS  = 4 * 60          # 4-minute session
WARNING_SECS  = 60              # last 60s warning

LANG_OPTIONS = {
    "English 🇬🇧":        {"code": "en", "gtts": "en"},
    "العربية 🇸🇦":         {"code": "ar", "gtts": "ar"},
    "Mixed (عربي+EN) 🔀": {"code": "mixed", "gtts": "ar"},
}

PROFILES = {
    1: {
        "emoji": "👀",
        "name": "First-Time Browser",
        "name_ar": "زائر لأول مرة",
        "brief": "Curious, low knowledge, needs guidance.",
        "brief_ar": "فضولي، يحتاج توجيه.",
        "opening_en": "Hi… I'm just looking. I don't really know much about perfumes honestly.",
        "opening_ar": "السلام عليكم… أنا بس أتفرج. ما عندي معرفة كثير بالعطور.",
        "personality": "Shy, easily overwhelmed. Warms up when treated gently.",
        "objections_en": ["I don't know what I like.", "Too many choices.", "Is it too expensive?"],
        "objections_ar": ["ما أعرف وش أحب.", "في خيارات كثير.", "غالي ما هو؟"],
        "buy_signal": "Asks 'do you think this suits me?' or lingers on a scent.",
        "difficulty": 1,
    },
    2: {
        "emoji": "🎁",
        "name": "Gift Shopper",
        "name_ar": "مشتري هدية",
        "brief": "Buying for someone else, indecisive.",
        "brief_ar": "يشتري هدية لشخص آخر، متردد.",
        "opening_en": "I need a gift for my sister. No idea what she'd like.",
        "opening_ar": "أبغى هدية لأختي. ما عندي فكرة وش تحب.",
        "personality": "Anxious about choosing wrong. Grateful for confident suggestions.",
        "objections_en": ["She might not like oud.", "What if she has it?", "Too expensive for a gift?"],
        "objections_ar": ["ممكن ما تحب العود.", "إذا عندها؟", "غالي للهدية؟"],
        "buy_signal": "Says 'that sounds perfect for her' or asks about wrapping.",
        "difficulty": 1,
    },
    3: {
        "emoji": "🏺",
        "name": "Classic Oud Loyalist",
        "name_ar": "عاشق العود",
        "brief": "Expert buyer, tests your knowledge.",
        "brief_ar": "مشتري خبير، يختبر معرفتك.",
        "opening_en": "I've worn Saudi oud for twenty years. Show me what you have.",
        "opening_ar": "أنا ألبس عود سعودي من عشرين سنة. وريني عندكم إيش.",
        "personality": "Confident, discerning. Respects expertise, dismisses generic pitches.",
        "objections_en": ["What makes yours different?", "Smells synthetic.", "I don't trust modern perfumery."],
        "objections_ar": ["وش اللي يميزكم؟", "تبيّن مركّب.", "ما أثق بعطور العصر."],
        "buy_signal": "Pauses, inhales slowly, asks about oud origin.",
        "difficulty": 2,
    },
}

KNOWLEDGE_BASE = """
MANSAM PARFUMERY — COACHING KNOWLEDGE BASE

BRAND: Luxury Arabian perfumery rooted in the heritage of the Arabian Peninsula.
Promise: authentic luxury, never imitation.

SERVICE STANDARDS:
- Greet warmly within 30 seconds
- Ask one question before recommending: "For yourself or a gift?"
- Offer scent strip before mentioning price
- Never rush — silence while smelling is sacred
- Close with suggestion: "I think this one found you."
- Always offer gift wrapping

PRODUCTS:
1. Al Majd (العظمة) — Oud & Rose | Extrait | 30ml SAR650 / 50ml SAR950
   Story: Named for glory — worn at weddings and royal gatherings for generations.

2. Sahara Musk — White Musk & Sandalwood | EDP | 50ml SAR380 / 100ml SAR520
   Story: Gentlest whisper of the desert at dawn. Perfect for daily wear and gifts.

3. Darb Al Hind (درب الهند) — Spiced Oud | EDP Intense | 50ml SAR820
   Story: Named for the ancient incense trade route. Bold, complex, unforgettable.

OBJECTION RESPONSES:
- Too expensive: Extrait = 12–14hr wear. More economical per use than it looks.
- Not sure about oud: Start with Sahara Musk — soft, no smoke, just warmth.
- Already have perfume: Great collections need variety. This is for occasions to remember.

STORYTELLING RULE: Open with place or moment — never with price.
"""

# ─── database ──────────────────────────────────────────────────────────────────
engine = create_engine("sqlite:///mansam.db", connect_args={"check_same_thread": False})

def init_db():
    with engine.connect() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT, profile_id INTEGER, language TEXT,
            sale_score REAL, svc_score REAL, points INTEGER DEFAULT 0,
            duration_secs INTEGER, transcript TEXT, debrief TEXT,
            created_at TEXT DEFAULT (datetime('now')))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS agents(
            name TEXT PRIMARY KEY, total_points INTEGER DEFAULT 0,
            sessions INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')))"""))
        c.commit()

init_db()

def upsert_agent(name):
    with engine.connect() as c:
        c.execute(text("INSERT INTO agents(name) VALUES(:n) ON CONFLICT(name) DO NOTHING"), {"n": name})
        c.commit()

def save_session(agent, pid, lang, sale, svc, pts, dur, transcript, debrief):
    with engine.connect() as c:
        c.execute(text("""INSERT INTO sessions
            (agent,profile_id,language,sale_score,svc_score,points,duration_secs,transcript,debrief)
            VALUES(:a,:p,:l,:s,:sv,:pt,:d,:t,:db)"""),
            dict(a=agent,p=pid,l=lang,s=sale,sv=svc,pt=pts,d=dur,
                 t=json.dumps(transcript),db=debrief))
        c.execute(text("UPDATE agents SET total_points=total_points+:pt, sessions=sessions+1 WHERE name=:n"),
                  {"pt": pts, "n": agent})
        c.commit()

# ─── Groq client ───────────────────────────────────────────────────────────────
def client() -> Groq:
    key = os.getenv("GROQ_API_KEY","")
    if not key:
        try: key = st.secrets["GROQ_API_KEY"]
        except: key = ""
    if not key:
        st.error("⚠️ GROQ_API_KEY missing. Add it in Streamlit → Manage app → Secrets.")
        st.stop()
    return Groq(api_key=key)

# ─── TTS ───────────────────────────────────────────────────────────────────────
def speak(text: str, lang: str) -> str | None:
    """Returns base64 mp3 or None on failure."""
    tts_lang = "ar" if lang in ("ar","mixed") else "en"
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=tts_lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        logger.warning(f"TTS: {e}")
        return None

def audio_html(b64: str, autoplay=True) -> str:
    ap = "autoplay" if autoplay else ""
    return f'<audio controls {ap} style="width:100%;height:36px"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# ─── STT ───────────────────────────────────────────────────────────────────────
def transcribe(audio_bytes: bytes, lang: str) -> str:
    c = client()
    hint = {"en":"en","ar":"ar","mixed":None}.get(lang)
    f = io.BytesIO(audio_bytes); f.name = "r.wav"
    kw = dict(file=f, model="whisper-large-v3", response_format="text", temperature=0.0)
    if hint: kw["language"] = hint
    r = c.audio.transcriptions.create(**kw)
    return (r if isinstance(r,str) else r.text).strip()

# ─── LLM: customer persona ─────────────────────────────────────────────────────
def persona_prompt(profile: dict, lang: str) -> str:
    if lang == "ar":
        lang_rule = (
            "تكلّم فقط بالعربية السعودية العامية (نجدية/حجازية). "
            f"جملة الافتتاح: {profile['opening_ar']} "
            f"اعتراضاتك المحتملة: {' | '.join(profile['objections_ar'])}"
        )
    elif lang == "mixed":
        lang_rule = (
            "Use a natural mix of Saudi Arabic and English — switch freely as a real KSA customer would. "
            f"Start with: {profile['opening_ar']}"
        )
    else:
        lang_rule = (
            f"Speak natural English. Opening line: {profile['opening_en']} "
            f"Possible objections: {' | '.join(profile['objections_en'])}"
        )

    return f"""You are a customer at Mansam Parfumery, a luxury Arabian perfume store in Saudi Arabia.

PROFILE: {profile['name']} ({profile['name_ar']})
PERSONALITY: {profile['personality']}
BUY SIGNAL: {profile['buy_signal']}

LANGUAGE: {lang_rule}

BRAND KNOWLEDGE:
{KNOWLEDGE_BASE}

RULES:
- Stay in character. Never reveal you are an AI.
- Keep each reply SHORT — 1 to 3 sentences maximum. You are a customer, not a narrator.
- React naturally: warm up when the salesperson is good; push back when they rush or miss signals.
- When your buy signal condition is met, show genuine interest in purchasing.
- This is a voice conversation — speak naturally, not in lists or bullet points.
"""

def customer_reply(profile, messages, lang) -> str:
    msgs = [{"role":"system","content":persona_prompt(profile,lang)}]
    if not messages:
        trigger = "[Session starts. Deliver your opening line naturally — one sentence.]"
        msgs.append({"role":"user","content":trigger})
    else:
        msgs.extend(messages)
    r = client().chat.completions.create(
        model=GROQ_MODEL, messages=msgs, max_tokens=120, temperature=0.9)
    return r.choices[0].message.content.strip()

# ─── LLM: scorer ───────────────────────────────────────────────────────────────
def score_prompt(lang: str) -> str:
    lang_note = {
        "ar": "Session was in Arabic — include language fluency & cultural register in Service score.",
        "mixed": "Session used code-switching — reward natural blending in Service score.",
        "en": "Session was in English.",
    }.get(lang,"")
    return f"""You are a warm, encouraging sales coach for Mansam Parfumery. {lang_note}

{KNOWLEDGE_BASE}

SALE SCORE (1-10): Did the salesperson close? (discovery, storytelling, objections, close)
SERVICE SCORE (1-10): Did the customer feel cared for? (warmth, patience, listening, cultural fit)

Reply ONLY with valid JSON — no markdown, no extra text:
{{
  "sale_score": <1-10>,
  "sale_justification": "<one warm sentence>",
  "service_score": <1-10>,
  "service_justification": "<one warm sentence>",
  "strong_points": ["<specific moment 1>","<specific moment 2>","<specific moment 3>"],
  "growth_areas": [
    {{"observation":"<what happened>","tip":"<one concrete phrase to try next time>"}},
    {{"observation":"<what happened>","tip":"<one concrete phrase to try next time>"}}
  ],
  "next_challenge": "<which profile + what to focus on next time>",
  "encouragement": "<2 sentences of genuine, specific encouragement>"
}}"""

def score_session_transcript(transcript, lang) -> dict:
    tx = "\n".join(
        f"{'SALESPERSON' if m['role']=='user' else 'CUSTOMER'}: {m['content']}"
        for m in transcript)
    r = client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role":"system","content":score_prompt(lang)},
            {"role":"user","content":f"Score this session:\n\n{tx}"},
        ],
        max_tokens=800, temperature=0.15)
    raw = r.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```"); raw = parts[1] if len(parts)>1 else raw
        if raw.startswith("json"): raw = raw[4:].strip()
    return json.loads(raw)

# ─── session state helpers ─────────────────────────────────────────────────────
def ss(k, d=None): return st.session_state.get(k,d)
def sset(k,v): st.session_state[k]=v

# ─── top bar ───────────────────────────────────────────────────────────────────
def top_bar():
    name = ss("agent_name","") or ""
    pts  = ss("total_points", 0)
    right = f"⭐ {pts} pts" if name else ""
    st.markdown(f"""
    <div class="top-bar">
        <span class="brand">🕌 MANSAM SALES COACH</span>
        <span class="pts">{right}</span>
    </div>""", unsafe_allow_html=True)

# ─── timer helpers ─────────────────────────────────────────────────────────────
def fmt_time(secs: int) -> str:
    m,s = divmod(max(0,secs),60)
    return f"{m}:{s:02d}"

def timer_html(remaining: int, total: int) -> str:
    pct   = remaining / total
    cls   = "done" if remaining <= 0 else ("warning" if remaining <= WARNING_SECS else "active")
    color = "#E07000" if cls=="warning" else ("#8C7A5A" if cls=="done" else "#C9A84C")
    # SVG arc progress ring
    r = 50; cx = cy = 60; stroke = 8
    circumference = 2 * 3.14159 * r
    dash = circumference * pct
    return f"""
    <div class="timer-wrap">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="#FAF6EE"
                stroke="#E8D5A3" stroke-width="{stroke}"/>
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
                stroke="{color}" stroke-width="{stroke}"
                stroke-dasharray="{dash:.1f} {circumference:.1f}"
                stroke-linecap="round"
                transform="rotate(-90 {cx} {cy})"/>
        <text x="{cx}" y="{cy+6}" text-anchor="middle"
              font-size="22" font-weight="700" fill="#1A1208"
              font-family="Cormorant Garamond,serif">{fmt_time(remaining)}</text>
      </svg>
      <div class="timer-label">{'⏰ WRAPPING UP' if remaining<=WARNING_SECS and remaining>0 else ('SESSION OVER' if remaining<=0 else 'REMAINING')}</div>
    </div>"""

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — WELCOME
# ══════════════════════════════════════════════════════════════════════════════
def screen_welcome():
    top_bar()
    st.markdown("""
    <div class="card-dark" style="text-align:center;padding:2rem 1.5rem;">
        <div style="font-size:2.5rem;margin-bottom:.5rem">🕌</div>
        <div style="font-family:'Cormorant Garamond',serif;font-size:1.8rem;
                    font-weight:700;color:#C9A84C;margin-bottom:.4rem">
            Mansam Sales Coach
        </div>
        <div style="color:#E8D5A3;font-size:.95rem;line-height:1.6">
            Practice selling to an AI customer.<br>
            Get coached. Earn points. Grow every session.
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("### 👤 What's your name?")
    name = st.text_input("Your name", placeholder="Enter your name to begin…",
                         label_visibility="collapsed", key="name_input")
    if st.button("Get Started →"):
        if name.strip():
            sset("agent_name", name.strip())
            upsert_agent(name.strip())
            sset("screen","pick_profile")
            st.rerun()
        else:
            st.warning("Please enter your name first.")

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — PICK PROFILE
# ══════════════════════════════════════════════════════════════════════════════
def screen_pick_profile():
    top_bar()
    name = ss("agent_name","")
    st.markdown(f"### 👋 Hello, {name}!")
    st.markdown("**Choose your customer for this session:**")
    st.markdown('<hr class="gold-line">', unsafe_allow_html=True)

    for pid, p in PROFILES.items():
        diff = "★"*p["difficulty"] + "☆"*(3-p["difficulty"])
        selected = ss("selected_profile") == pid
        border = "border-color:#C9A84C" if selected else ""
        st.markdown(f"""
        <div class="profile-card" style="{border}">
            <div style="font-size:2.2rem">{p['emoji']}</div>
            <div style="font-weight:700;font-size:1.05rem;margin:.3rem 0">{p['name']}</div>
            <div style="font-size:.82rem;color:#8C7A5A;margin-bottom:.4rem">{p['name_ar']}</div>
            <div style="font-size:.88rem;color:#2E2415;margin-bottom:.5rem">{p['brief']}</div>
            <div style="font-size:.78rem;color:#8C7A5A">Difficulty: {diff}</div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Choose {p['name']}", key=f"pick_{pid}", use_container_width=True):
            sset("selected_profile", pid)
            sset("screen","pick_language")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — PICK LANGUAGE
# ══════════════════════════════════════════════════════════════════════════════
def screen_pick_language():
    top_bar()
    pid  = ss("selected_profile", 1)
    p    = PROFILES[pid]
    st.markdown(f"### {p['emoji']} {p['name']}")
    st.caption(p["brief"])
    st.markdown('<hr class="gold-line">', unsafe_allow_html=True)
    st.markdown("**Choose the session language:**")

    for label, cfg in LANG_OPTIONS.items():
        if st.button(label, key=f"lang_{cfg['code']}", use_container_width=True):
            sset("session_lang", cfg["code"])
            sset("session_gtts", cfg["gtts"])
            sset("screen","instructions")
            st.rerun()

    if st.button("← Back", use_container_width=False):
        sset("screen","pick_profile"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — INSTRUCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def screen_instructions():
    top_bar()
    pid  = ss("selected_profile", 1)
    p    = PROFILES[pid]
    lang = ss("session_lang","en")
    lang_label = {"en":"English","ar":"Arabic","mixed":"Arabic + English"}.get(lang,"")

    st.markdown(f"### Ready to practise, {ss('agent_name','')}?")
    st.markdown(f"""
    <div class="card-dark">
        <div style="color:#C9A84C;font-weight:700;font-size:1rem;margin-bottom:.6rem">
            Your session
        </div>
        <div style="color:#E8D5A3;font-size:.92rem;line-height:1.7">
            🎭 Customer: <b style="color:#C9A84C">{p['name']}</b><br>
            🗣️ Language: <b style="color:#C9A84C">{lang_label}</b><br>
            ⏱️ Duration: <b style="color:#C9A84C">4 minutes</b>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("**How it works:**")
    steps = [
        ("The customer will speak first", "You'll hear their opening line as audio."),
        ("Record your response", "Press the 🎙️ mic button and speak naturally — just like on the floor."),
        ("Keep it conversational", "Short, natural replies work best. No need to be perfect."),
        ("Session runs for 4 minutes", "A countdown shows your remaining time."),
        ("Coaching at the end", "You'll get a full debrief with scores and personalised tips."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(f"""
        <div class="step">
            <div class="step-num">{i}</div>
            <div class="step-text"><b>{title}</b><br>
            <span style="color:#8C7A5A">{desc}</span></div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="gold-line">', unsafe_allow_html=True)

    if lang == "ar":
        tip_text = "💡 تحدّث بشكل طبيعي كأنك في المتجر فعلاً."
    elif lang == "mixed":
        tip_text = "💡 Mix freely — real customers switch languages mid-sentence."
    else:
        tip_text = "💡 Speak naturally, as if you're on the shop floor right now."

    st.info(tip_text)

    if st.button("🎙️ Start Session →", use_container_width=True):
        # Initialise session state
        sset("messages", [])
        sset("session_start", time.time())
        sset("screen", "session")
        sset("waiting_for_audio", False)
        sset("customer_audio_b64", None)
        sset("last_audio_bytes", b"")
        st.rerun()

    if st.button("← Change customer", use_container_width=False):
        sset("screen","pick_profile"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — LIVE SESSION
# ══════════════════════════════════════════════════════════════════════════════
def screen_session():
    top_bar()
    pid      = ss("selected_profile", 1)
    p        = PROFILES[pid]
    lang     = ss("session_lang","en")
    gtts_l   = ss("session_gtts","en")
    msgs     = ss("messages", [])
    started  = ss("session_start", time.time())
    elapsed  = int(time.time() - started)
    remaining = max(0, SESSION_SECS - elapsed)

    # ── header row ────────────────────────────────────────────────────────────
    col_info, col_timer = st.columns([3, 2])
    with col_info:
        st.markdown(f"**{p['emoji']} {p['name']}**")
        st.caption({"en":"English 🇬🇧","ar":"Arabic 🇸🇦","mixed":"Mixed 🔀"}.get(lang,""))
    with col_timer:
        st.markdown(timer_html(remaining, SESSION_SECS), unsafe_allow_html=True)

    st.markdown('<hr class="gold-line">', unsafe_allow_html=True)

    # ── session over — go to debrief ─────────────────────────────────────────
    if remaining == 0 and len(msgs) >= 2:
        sset("session_duration", elapsed)
        sset("screen","scoring")
        st.rerun()

    # ── get customer opening if no messages yet ───────────────────────────────
    if not msgs:
        with st.spinner("Customer entering the store…" if lang=="en" else "العميل يدخل…"):
            opening = customer_reply(p, [], lang)
        msgs.append({"role":"assistant","content":opening})
        sset("messages", msgs)
        b64 = speak(opening, lang)
        sset("customer_audio_b64", b64)
        sset("waiting_for_audio", True)
        st.rerun()

    # ── render conversation ───────────────────────────────────────────────────
    st.markdown("**Conversation**")
    chat_area = st.container()
    with chat_area:
        for i, m in enumerate(msgs):
            is_last = (i == len(msgs)-1)
            ar_cls  = " bubble-ar" if lang in ("ar","mixed") else ""
            if m["role"] == "assistant":
                label = "👤 العميل" if lang in ("ar","mixed") else "👤 Customer"
                st.markdown(
                    f'<div class="bubble-customer{ar_cls}">'
                    f'<small style="opacity:.6;font-size:.72rem">{label}</small><br>{m["content"]}</div>',
                    unsafe_allow_html=True)
                # Play audio for the latest customer message
                if is_last and ss("customer_audio_b64"):
                    st.markdown(audio_html(ss("customer_audio_b64")), unsafe_allow_html=True)
                    sset("customer_audio_b64", None)
            else:
                label = "🧑 أنت" if lang in ("ar","mixed") else "🧑 You"
                st.markdown(
                    f'<div class="bubble-you{ar_cls}">'
                    f'<small style="opacity:.6;font-size:.72rem">{label}</small><br>{m["content"]}</div>',
                    unsafe_allow_html=True)

    st.markdown('<hr class="gold-line">', unsafe_allow_html=True)

    # ── mic input ─────────────────────────────────────────────────────────────
    if remaining > 0:
        mic_label = (
            "🎙️ اضغط للتسجيل — تكلّم بشكل طبيعي ثم اضغط مرة ثانية للإيقاف"
            if lang in ("ar","mixed")
            else "🎙️ Tap to record → speak → tap again to stop"
        )
        st.markdown(f"<div style='text-align:center;color:#8C7A5A;font-size:.85rem;margin-bottom:.4rem'>{mic_label}</div>",
                    unsafe_allow_html=True)

        audio_val = st.audio_input("Record your response", label_visibility="collapsed",
                                   key=f"mic_{len(msgs)}")

        if audio_val is not None:
            raw = audio_val.read()
            if raw and raw != ss("last_audio_bytes", b""):
                sset("last_audio_bytes", raw)
                with st.spinner("Whisper is transcribing…" if lang=="en" else "ويسبر يحوّل صوتك…"):
                    try:
                        text_out = transcribe(raw, lang)
                    except Exception as e:
                        st.error(f"Transcription error: {e}")
                        st.stop()

                if text_out.strip():
                    msgs.append({"role":"user","content":text_out})
                    # Get customer reply
                    with st.spinner("Customer responding…" if lang=="en" else "العميل يرد…"):
                        reply = customer_reply(p, msgs, lang)
                    msgs.append({"role":"assistant","content":reply})
                    sset("messages", msgs)
                    b64 = speak(reply, lang)
                    sset("customer_audio_b64", b64)
                    st.rerun()

        # End early button — smaller, secondary style
        st.markdown("<div style='margin-top:.8rem'>", unsafe_allow_html=True)
        if st.button("✅ End session early & get feedback", use_container_width=True):
            if len(msgs) >= 3:
                sset("session_duration", elapsed)
                sset("screen","scoring")
                st.rerun()
            else:
                st.warning("Have at least 2 exchanges first — keep going!" if lang=="en"
                           else "أجرِ تبادلين على الأقل أولاً!")
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("⏱️ Time's up! Calculating your results…")
        time.sleep(1)
        sset("session_duration", elapsed)
        sset("screen","scoring")
        st.rerun()

    # ── auto-rerun to keep timer ticking ──────────────────────────────────────
    if remaining > 0:
        time.sleep(1)
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 6 — SCORING (brief loading screen)
# ══════════════════════════════════════════════════════════════════════════════
def screen_scoring():
    top_bar()
    st.markdown("""
    <div style="text-align:center;padding:3rem 1rem">
        <div style="font-size:3rem;margin-bottom:1rem">⚡</div>
        <div style="font-family:'Cormorant Garamond',serif;font-size:1.6rem;
                    font-weight:700;color:#2E2415;margin-bottom:.6rem">
            Analysing your session…
        </div>
        <div style="color:#8C7A5A;font-size:.9rem">
            Your personal coach is reviewing the conversation
        </div>
    </div>""", unsafe_allow_html=True)

    msgs = ss("messages",[])
    lang = ss("session_lang","en")
    pid  = ss("selected_profile",1)

    with st.spinner(""):
        try:
            scores = score_session_transcript(msgs, lang)
        except Exception as e:
            st.error(f"Scoring error: {e}")
            if st.button("Retry"):
                st.rerun()
            return

    # calc points
    perf = int((scores["sale_score"] + scores["service_score"]) * 5)
    pts  = 10 + perf   # 10 participation + performance
    dur  = ss("session_duration", SESSION_SECS)

    debrief_json = json.dumps(scores)
    save_session(
        ss("agent_name",""), pid, lang,
        scores["sale_score"], scores["service_score"],
        pts, dur, msgs, debrief_json
    )
    sset("last_scores", scores)
    sset("last_points", pts)
    sset("total_points", ss("total_points",0) + pts)
    sset("screen","debrief")
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 7 — DEBRIEF
# ══════════════════════════════════════════════════════════════════════════════
def screen_debrief():
    top_bar()
    scores = ss("last_scores", {})
    pts    = ss("last_points", 10)
    name   = ss("agent_name","")
    lang   = ss("session_lang","en")
    pid    = ss("selected_profile",1)
    p      = PROFILES[pid]

    sale   = scores.get("sale_score", 0)
    svc    = scores.get("service_score", 0)

    # ── hero congrats ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="card-dark" style="text-align:center">
        <div style="font-size:2.5rem;margin-bottom:.4rem">🎉</div>
        <div style="font-family:'Cormorant Garamond',serif;font-size:1.5rem;
                    font-weight:700;color:#C9A84C;margin-bottom:.3rem">
            Well done, {name}!
        </div>
        <div style="color:#E8D5A3;font-size:.9rem">Session complete</div>
    </div>""", unsafe_allow_html=True)

    # ── scores ───────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card" style="text-align:center">
            <div class="score-ring">
                <div class="num">{sale}</div>
                <div class="den">/ 10</div>
            </div>
            <div style="font-weight:700;font-size:.9rem;margin-bottom:.2rem">SALE</div>
            <div style="font-size:.8rem;color:#8C7A5A">{scores.get("sale_justification","")}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card" style="text-align:center">
            <div class="score-ring">
                <div class="num">{svc}</div>
                <div class="den">/ 10</div>
            </div>
            <div style="font-weight:700;font-size:.9rem;margin-bottom:.2rem">SERVICE</div>
            <div style="font-size:.8rem;color:#8C7A5A">{scores.get("service_justification","")}</div>
        </div>""", unsafe_allow_html=True)

    # ── points ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="points-badge">
        ⭐ +{pts} points earned this session
    </div>""", unsafe_allow_html=True)

    # ── encouragement ─────────────────────────────────────────────────────────
    enc = scores.get("encouragement","")
    if enc:
        st.markdown(f"""
        <div class="card" style="border-left:4px solid #C9A84C">
            <div style="font-size:.85rem;color:#8C7A5A;font-weight:600;
                        text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem">
                💬 Coach says
            </div>
            <div style="font-size:.95rem;line-height:1.6;color:#1A1208">{enc}</div>
        </div>""", unsafe_allow_html=True)

    # ── what you did well ─────────────────────────────────────────────────────
    strongs = scores.get("strong_points",[])
    if strongs:
        st.markdown('<div class="debrief-section">', unsafe_allow_html=True)
        st.markdown("#### ✦ What you did well")
        for s in strongs:
            st.markdown(f'<div class="debrief-item">{s}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── growth areas ──────────────────────────────────────────────────────────
    grows = scores.get("growth_areas",[])
    if grows:
        st.markdown('<div class="debrief-section">', unsafe_allow_html=True)
        st.markdown("#### ◈ One thing to try next time")
        for g in grows:
            obs = g.get("observation","")
            tip_txt = g.get("tip","")
            st.markdown(f"""
            <div class="grow-item">
                <div style="font-size:.88rem;color:#2E2415">{obs}</div>
                <div style="margin-top:.3rem;font-style:italic;color:#C9A84C;font-size:.88rem">
                    Try: "{tip_txt}"
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── next challenge ────────────────────────────────────────────────────────
    nxt = scores.get("next_challenge","")
    if nxt:
        st.markdown(f"""
        <div class="card" style="background:#F5EDD6">
            <div style="font-size:.82rem;color:#8C7A5A;font-weight:600;
                        text-transform:uppercase;letter-spacing:.06em;margin-bottom:.3rem">
                🎯 Your next challenge
            </div>
            <div style="font-size:.92rem;color:#2E2415">{nxt}</div>
        </div>""", unsafe_allow_html=True)

    # ── debrief audio (summary read aloud) ────────────────────────────────────
    summary_tts = (
        f"Well done {name}! Your Sale score is {sale} out of 10, "
        f"and your Service score is {svc} out of 10. "
        f"You earned {pts} points. {enc}"
    )
    with st.spinner("Generating audio summary…"):
        b64 = speak(summary_tts, "en")   # debrief always in English
    if b64:
        st.markdown("**🔊 Listen to your feedback:**")
        st.markdown(audio_html(b64, autoplay=False), unsafe_allow_html=True)

    st.markdown('<hr class="gold-line">', unsafe_allow_html=True)

    # ── actions ───────────────────────────────────────────────────────────────
    if st.button("🔄 Practice Again", use_container_width=True):
        for k in ["messages","session_start","session_duration",
                  "last_scores","last_points","customer_audio_b64",
                  "last_audio_bytes","waiting_for_audio",
                  "session_lang","session_gtts","selected_profile"]:
            sset(k, None)
        sset("screen","pick_profile")
        st.rerun()

    if st.button("👋 Change Agent Name", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
def main():
    screen = ss("screen","welcome")
    {
        "welcome":      screen_welcome,
        "pick_profile": screen_pick_profile,
        "pick_language":screen_pick_language,
        "instructions": screen_instructions,
        "session":      screen_session,
        "scoring":      screen_scoring,
        "debrief":      screen_debrief,
    }.get(screen, screen_welcome)()

if __name__ == "__main__":
    main()
