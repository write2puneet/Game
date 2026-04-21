"""
Mansam Parfumery — Gamified AI Sales Coaching Agent
====================================================
Streamlit MVP · Phase 1
LLM  : Groq — Llama 3.3 70B (free · 30 RPM · 1,000 req/day)
Audio: gTTS  — Google Text-to-Speech (free, no API key)
Lang : English + Arabic (selectable per session)

Streamlit secrets required:
  GROQ_API_KEY = "gsk_..."
"""

import os
import io
import json
import base64
import datetime
import streamlit as st
from groq import Groq
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from gtts import gTTS
from loguru import logger
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  — must be first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mansam | Sales Coach",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# FORCE LIGHT THEME + FULL STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Force light theme regardless of system/browser preference ── */
:root, [data-theme="dark"], [data-theme="light"] {
    color-scheme: light !important;
}
html, body {
    background-color: #FAF6EE !important;
    color: #1A1208 !important;
}

/* ── Brand tokens ── */
:root {
    --gold:       #C9A84C;
    --gold-lt:    #E8D5A3;
    --gold-pale:  #F5EDD6;
    --dark:       #1A1208;
    --mid:        #2E2415;
    --cream:      #FAF6EE;
    --muted:      #8C7A5A;
    --white:      #FFFFFF;
    --border:     #DDD3B8;
}

@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Jost:wght@300;400;500&display=swap');

html, body, [class*="css"], .stApp, section[data-testid="stAppViewContainer"] {
    font-family: 'Jost', sans-serif !important;
    background-color: var(--cream) !important;
    color: var(--dark) !important;
}

h1, h2, h3 {
    font-family: 'Cormorant Garamond', serif !important;
    color: var(--dark) !important;
}

/* ── Force all text inputs to be light ── */
input, textarea, select,
.stTextInput input,
.stTextArea textarea,
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background-color: #FFFFFF !important;
    color: #1A1208 !important;
    border: 1.5px solid var(--gold-lt) !important;
    border-radius: 4px !important;
    caret-color: var(--dark) !important;
}
input::placeholder, textarea::placeholder {
    color: #A89070 !important;
    opacity: 1 !important;
}

/* ── Buttons ── */
.stButton > button,
.stFormSubmitButton > button {
    background: var(--gold) !important;
    color: var(--dark) !important;
    border: none !important;
    border-radius: 3px !important;
    font-family: 'Jost', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    transition: background 0.18s !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: var(--gold-lt) !important;
}

/* ── Sidebar ── */
div[data-testid="stSidebar"],
div[data-testid="stSidebar"] > div {
    background-color: var(--mid) !important;
}
div[data-testid="stSidebar"] label,
div[data-testid="stSidebar"] p,
div[data-testid="stSidebar"] span,
div[data-testid="stSidebar"] div,
div[data-testid="stSidebar"] .stCaption {
    color: var(--gold-lt) !important;
}
div[data-testid="stSidebar"] input {
    background: #3D3020 !important;
    color: #FAF6EE !important;
    border-color: var(--muted) !important;
}
div[data-testid="stSidebar"] input::placeholder {
    color: var(--muted) !important;
}
div[data-testid="stSidebar"] .stRadio label span {
    color: var(--gold-lt) !important;
}

/* ── Metric cards ── */
.metric-card {
    background: var(--mid);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    text-align: center;
    margin-bottom: 0.5rem;
}
.metric-card .val {
    font-size: 2rem;
    font-family: 'Cormorant Garamond', serif;
    font-weight: 700;
    color: var(--gold);
}
.metric-card .lbl {
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
}

/* ── Badges ── */
.badge {
    display: inline-block;
    background: var(--gold);
    color: var(--dark);
    border-radius: 20px;
    padding: 3px 14px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin: 2px;
}
.badge-outline {
    display: inline-block;
    border: 1.5px solid var(--gold);
    color: var(--gold);
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.73rem;
    font-weight: 500;
    margin: 2px;
}

/* ── Chat bubbles ── */
.chat-user {
    background: var(--white);
    border-left: 3px solid var(--gold);
    padding: 0.75rem 1rem;
    border-radius: 0 6px 6px 0;
    margin-bottom: 0.5rem;
    color: var(--dark);
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.chat-ai {
    background: var(--mid);
    color: var(--cream);
    border-left: 3px solid var(--muted);
    padding: 0.75rem 1rem;
    border-radius: 0 6px 6px 0;
    margin-bottom: 0.5rem;
}
.chat-ai-ar {
    background: var(--mid);
    color: var(--cream);
    border-right: 3px solid var(--muted);
    border-left: none;
    padding: 0.75rem 1rem;
    border-radius: 6px 0 0 6px;
    margin-bottom: 0.5rem;
    direction: rtl;
    text-align: right;
}
.chat-user-ar {
    background: var(--white);
    border-right: 3px solid var(--gold);
    border-left: none;
    padding: 0.75rem 1rem;
    border-radius: 6px 0 0 6px;
    margin-bottom: 0.5rem;
    color: var(--dark);
    direction: rtl;
    text-align: right;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* ── Debrief box ── */
.debrief-box {
    background: var(--white);
    border: 1px solid var(--gold-lt);
    border-radius: 6px;
    padding: 1.6rem;
    margin-top: 1rem;
    white-space: pre-wrap;
    font-family: 'Jost', sans-serif;
    font-size: 0.9rem;
    line-height: 1.75;
    color: var(--dark);
}

/* ── Profile cards ── */
.profile-card {
    background: var(--white);
    border: 1.5px solid var(--gold-pale);
    border-radius: 8px;
    padding: 1.2rem;
    margin-bottom: 0.5rem;
    transition: border-color 0.2s;
}
.profile-card:hover { border-color: var(--gold); }

/* ── Language toggle pill ── */
.lang-pill {
    display: inline-block;
    background: var(--gold-pale);
    color: var(--dark);
    border-radius: 20px;
    padding: 4px 16px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 3px;
    cursor: default;
}
.lang-pill-active {
    background: var(--gold);
}

/* ── Tooltip helper text ── */
.tip {
    font-size: 0.78rem;
    color: var(--muted);
    font-style: italic;
    margin-top: 2px;
}

/* ── Audio player compact ── */
audio {
    height: 32px;
    width: 100%;
    margin-top: 4px;
    border-radius: 4px;
    accent-color: var(--gold);
}

/* ── Streamlit overrides ── */
.stAlert { border-radius: 4px !important; }
div[data-testid="stToolbar"] { display: none; }
.stDataFrame { border: 1px solid var(--gold-pale) !important; border-radius: 4px; }

/* ── RTL form support ── */
.rtl-input input {
    direction: rtl !important;
    text-align: right !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
GROQ_MODEL      = "llama-3.3-70b-versatile"
POINTS_PARTICIP = 10
POINTS_GROWTH   = 20

TIER_CONFIG = {
    1: {"name": "Beginner",     "sessions_needed": 10, "avg_score_needed": 6},
    2: {"name": "Intermediate", "sessions_needed": 15, "avg_score_needed": 7},
    3: {"name": "Expert",       "sessions_needed": 999, "avg_score_needed": 9},
}

LANG_OPTIONS = {
    "English 🇬🇧":        {"code": "en", "gtts": "en", "label": "English"},
    "العربية 🇸🇦":         {"code": "ar", "gtts": "ar", "label": "Arabic"},
    "Mixed (عربي + EN)": {"code": "mixed", "gtts": "ar", "label": "Mixed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER PROFILES  (English + Arabic variants)
# ─────────────────────────────────────────────────────────────────────────────
PROFILES = {
    1: {
        "id": 1, "name": "First-Time Browser", "name_ar": "الزائر لأول مرة",
        "tier": 1, "emoji": "👀",
        "brief": "Curious, low product knowledge, needs guidance and reassurance.",
        "brief_ar": "فضولي، معرفة محدودة بالعطور، يحتاج إلى توجيه وطمأنة.",
        "opening_en": "Hi… I'm just looking. I don't really know much about perfumes honestly.",
        "opening_ar": "السلام عليكم… أنا بس أتفرج. ما عندي معرفة كبيرة بالعطور بصراحة.",
        "personality": "Shy, easily overwhelmed, responds well to warmth and simplicity.",
        "personality_ar": "خجول، يرتبك بسهولة، يستجيب جيداً للدفء والبساطة.",
        "triggers": ["feeling special", "easy recommendation", "not being judged"],
        "objections_en": ["I don't know what I like yet.", "Too many options, I'm overwhelmed.", "I usually just buy whatever smells nice."],
        "objections_ar": ["ما أعرف وش أحب.", "في خيارات كثير، تعبت.", "عادةً أشتري أي شي يرائحته حلوة."],
        "buy_signal": "Asks 'do you think this one would suit me?' or lingers on a scent.",
        "difficulty": 1,
    },
    2: {
        "id": 2, "name": "Gift Shopper", "name_ar": "مشتري هدية",
        "tier": 1, "emoji": "🎁",
        "brief": "Buying for someone else, unsure of preferences, needs help narrowing.",
        "brief_ar": "يشتري هدية لشخص آخر، غير متأكد من التفضيلات، يحتاج مساعدة.",
        "opening_en": "I need to buy a gift for my sister — I have no idea what she'd like.",
        "opening_ar": "أبغى أشتري هدية لأختي — ما عندي فكرة وش تحب.",
        "personality": "Indecisive, slightly anxious about getting it wrong, grateful for guidance.",
        "personality_ar": "متردد، قلق من اختيار غلط، ممتنن للمساعدة.",
        "triggers": ["reassurance", "beautiful packaging", "value for money"],
        "objections_en": ["I'm not sure she'd like oud.", "What if she already has this?", "Is this too expensive for a gift?"],
        "objections_ar": ["مو متأكد إنها تحب العود.", "إذا عندها هذا؟", "هذا غالي للهدية؟"],
        "buy_signal": "Says 'that sounds like something she'd love' or asks about gift wrapping.",
        "difficulty": 1,
    },
    3: {
        "id": 3, "name": "Classic Oud Loyalist", "name_ar": "عاشق العود الكلاسيكي",
        "tier": 1, "emoji": "🏺",
        "brief": "Knows exactly what they want — values heritage and authenticity.",
        "brief_ar": "يعرف بالضبط ما يريد — يقدّر التراث والأصالة.",
        "opening_en": "I've been wearing Saudi oud for twenty years. Show me what you have.",
        "opening_ar": "أنا ألبس عود سعودي من عشرين سنة. وريني عندكم إيش.",
        "personality": "Confident, discerning, slightly impatient. Respects expertise.",
        "personality_ar": "واثق، نقّاد، نوعاً ما قليل الصبر. يحترم الخبرة.",
        "triggers": ["craftsmanship", "heritage", "exclusivity", "authenticity"],
        "objections_en": ["What makes yours different?", "This smells like a blend, not pure oud.", "I don't trust modern perfumery with oud."],
        "objections_ar": ["وش اللي يميزكم؟", "هذا يبين مزيج، مو عود صافي.", "ما أثق بعطور العصر الحديث في العود."],
        "buy_signal": "Pauses and inhales deeply, asks about the oud wood origin.",
        "difficulty": 2,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = """
MANSAM PARFUMERY — KNOWLEDGE BASE (PHASE 1 SAMPLE)

BRAND POSITIONING
Mansam is a luxury Arabian perfumery house rooted in the heritage of the Arabian Peninsula.
Every fragrance carries a story — of desert landscapes, ancient trade routes, and the intimate
rituals of Saudi hospitality. Brand promise: authentic luxury, never imitation.
(بالعربي: منسم للعطور الفاخرة — التراث العربي الأصيل في كل قطرة)

CUSTOMER SERVICE STANDARDS
- Greet every customer warmly within 30 seconds.
- Ask one question before recommending: "Are you looking for something for yourself or as a gift?"
- Offer a scent strip or skin test before mentioning price.
- Never rush. Silence while a customer smells is sacred.
- Close with suggestion not pressure: "I think this one found you."
- Always offer gift wrapping and a handwritten note.

PRODUCT CATALOGUE
1. Al Majd (العظمة) — Oud & Rose
   Family: Oriental Woody | Notes: Agarwood / Taif Rose / Amber
   Concentration: Extrait | 30ml SAR 650 / 50ml SAR 950
   Story: Named for glory — worn at weddings and royal gatherings for generations.

2. Sahara Musk — White Musk & Sandalwood
   Family: Soft Oriental | Notes: White Musk / Sandalwood / Vanilla
   Concentration: EDP | 50ml SAR 380 / 100ml SAR 520
   Story: The gentlest whisper of the desert at dawn. Perfect for daily wear and gifts.

3. Darb Al Hind (درب الهند) — Spiced Oud
   Family: Spicy Oriental | Notes: Indian Oud / Saffron / Cardamom / Patchouli
   Concentration: EDP Intense | 50ml SAR 820
   Story: Named for the ancient incense trade route. Bold, complex, unforgettable.

OBJECTION HANDLING
- "Too expensive": Extrait concentration = 12-14 hours wear per application. More economical per use than cheaper alternatives.
- "Not sure about oud": Start with Sahara Musk — soft, no smoke, just warmth. Then travel further.
- "Already have perfume": A great collection needs variety. This is for occasions to be remembered.

STORYTELLING RULE
Open with place or moment — never with price. Let the customer smell before they see the number.
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH = "mansam_coach.db"
engine  = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson TEXT    NOT NULL,
                profile_id  INTEGER NOT NULL,
                language    TEXT    DEFAULT 'en',
                sale_score  REAL,
                svc_score   REAL,
                points      INTEGER DEFAULT 0,
                transcript  TEXT,
                debrief     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS salespeople (
                username     TEXT PRIMARY KEY,
                display_name TEXT,
                tier         INTEGER DEFAULT 1,
                total_points INTEGER DEFAULT 0,
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """))
        conn.commit()

init_db()

def upsert_salesperson(username: str, display_name: str):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO salespeople (username, display_name)
            VALUES (:u, :d) ON CONFLICT(username) DO NOTHING
        """), {"u": username, "d": display_name})
        conn.commit()

def save_session(salesperson, profile_id, language, sale, svc, points, transcript, debrief):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO sessions
              (salesperson,profile_id,language,sale_score,svc_score,points,transcript,debrief)
            VALUES (:sp,:pid,:lang,:sale,:svc,:pts,:tx,:db)
        """), dict(sp=salesperson, pid=profile_id, lang=language, sale=sale, svc=svc,
                   pts=points, tx=json.dumps(transcript), db=debrief))
        conn.execute(text("""
            UPDATE salespeople SET total_points = total_points + :pts WHERE username = :u
        """), {"pts": points, "u": salesperson})
        conn.commit()

def load_sessions(salesperson: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            "SELECT * FROM sessions WHERE salesperson=:sp ORDER BY created_at DESC",
            conn, params={"sp": salesperson}
        )

def load_all_sessions() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM sessions ORDER BY created_at DESC", conn)

def load_salespeople() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM salespeople", conn)

# ─────────────────────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────────────────────
def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = ""
    if not api_key:
        st.error(
            "⚠️ **GROQ_API_KEY not found.**\n\n"
            "Get a free key at https://console.groq.com then add to Streamlit secrets:\n"
            "```\nGROQ_API_KEY = \"gsk_...\"\n```"
        )
        st.stop()
    return Groq(api_key=api_key)

# ─────────────────────────────────────────────────────────────────────────────
# AUDIO — gTTS (free, no API key)
# ─────────────────────────────────────────────────────────────────────────────
def text_to_audio_b64(text: str, lang_code: str = "en") -> str | None:
    """Convert text to base64-encoded MP3 using gTTS. Returns None on failure."""
    # For mixed sessions use Arabic TTS since customer speaks Arabic
    tts_lang = "ar" if lang_code in ("ar", "mixed") else "en"
    try:
        buf = io.BytesIO()
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        logger.warning(f"TTS failed: {e}")
        return None

def audio_player(b64: str) -> str:
    """Return HTML audio player for a base64 MP3."""
    return f'<audio controls autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDERS
# ─────────────────────────────────────────────────────────────────────────────
def persona_system(profile: dict, lang_code: str) -> str:
    if lang_code == "ar":
        lang_instruction = (
            "Speak ONLY in Saudi Arabic (Najdi/Hijazi dialect). "
            "Use natural conversational Arabic, not Modern Standard Arabic. "
            f"Your opening line in Arabic: {profile['opening_ar']}\n"
            f"Your objections: {'; '.join(profile['objections_ar'])}"
        )
        personality = profile["personality_ar"]
        brief       = profile["brief_ar"]
    elif lang_code == "mixed":
        lang_instruction = (
            "Speak in a natural mix of Saudi Arabic and English — code-switch freely "
            "as a real KSA customer would in a luxury store. "
            f"Start with: {profile['opening_ar']}"
        )
        personality = profile["personality"]
        brief       = profile["brief"]
    else:
        lang_instruction = (
            "Speak natural English.\n"
            f"Opening line: {profile['opening_en']}\n"
            f"Objections: {'; '.join(profile['objections_en'])}"
        )
        personality = profile["personality"]
        brief       = profile["brief"]

    return f"""You are playing a customer at Mansam Parfumery, a luxury Arabian perfume brand in Saudi Arabia.

PROFILE: {profile['name']} ({profile['name_ar']})
PERSONALITY: {personality}
MOTIVATION: {brief}
EMOTIONAL TRIGGERS: {', '.join(profile['triggers'])}
BUY SIGNAL: {profile['buy_signal']}

LANGUAGE INSTRUCTION: {lang_instruction}

BRAND KNOWLEDGE:
{KNOWLEDGE_BASE}

RULES:
- Stay in character at all times. Never reveal you are an AI.
- React realistically — push back, ask questions, express hesitation.
- Warm up naturally when the salesperson uses good technique.
- Cool down when they rush or ignore your concerns.
- Keep responses to 2–4 sentences — you are a customer, not a narrator.
- When the buy signal is met, show genuine purchasing interest.
"""

def scoring_system(lang_code: str) -> str:
    lang_note = {
        "ar":    "The session was conducted in Arabic. Evaluate Arabic fluency and cultural register under Service.",
        "mixed": "The session used code-switching (Arabic + English). Reward natural language blending under Service.",
        "en":    "The session was conducted in English.",
    }.get(lang_code, "")

    return f"""You are an expert sales coach scoring a Mansam Parfumery role-play session.
{lang_note}

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

SALE SCORE (1–10) — Can the salesperson close?
10  Perfect: discovery, storytelling, all objections handled, natural close + upsell
8–9 Strong, minor gaps
6–7 Adequate — identified need, recommendation made, weak close or missed upsell
4–5 Partial — some knowledge, poor objection handling or no close attempt
2–3 Minimal selling behaviour
1   No selling behaviour

SERVICE SCORE (1–10) — Does the customer feel cared for?
10  Warm, patient, culturally appropriate, active listening, never rushed
8–9 Mostly warm, minor lapses
6–7 Polite but mechanical or slightly rushed
4–5 Transactional, no real connection
2–3 Cold or impatient
1   Rude or dismissive

CRITICAL: Reply ONLY with a valid JSON object. No markdown, no extra text.
{{
  "sale_score": <integer 1-10>,
  "sale_justification": "<one sentence>",
  "service_score": <integer 1-10>,
  "service_justification": "<one sentence>",
  "strong_points": ["<point 1>", "<point 2>", "<point 3>"],
  "improvement_areas": [
    {{"what": "<what happened>", "why": "<why it matters>", "suggestion": "<concrete phrase or technique>"}},
    {{"what": "<what happened>", "why": "<why it matters>", "suggestion": "<concrete phrase or technique>"}}
  ],
  "next_session_recommendation": "<profile name and focus area>"
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# LLM CALLS
# ─────────────────────────────────────────────────────────────────────────────
def chat_as_customer(profile: dict, messages: list, lang_code: str) -> str:
    client = get_client()
    groq_msgs = [{"role": "system", "content": persona_system(profile, lang_code)}]

    if not messages:
        trigger = (
            "[الجلسة تبدأ الآن. أنت في المتجر. قل جملة الافتتاح بشكل طبيعي.]"
            if lang_code in ("ar", "mixed")
            else "[Session starts. You are in the store. Deliver your opening line naturally.]"
        )
        groq_msgs.append({"role": "user", "content": trigger})
    else:
        for m in messages:
            groq_msgs.append({"role": m["role"], "content": m["content"]})

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL, messages=groq_msgs,
            max_tokens=250, temperature=0.85,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq chat error: {e}")
        raise


def score_session(transcript: list, lang_code: str) -> dict:
    client = get_client()
    tx_text = "\n".join(
        f"{'SALESPERSON' if m['role']=='user' else 'CUSTOMER'}: {m['content']}"
        for m in transcript
    )
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": scoring_system(lang_code)},
                {"role": "user",   "content": f"Score this session:\n\n{tx_text}"},
            ],
            max_tokens=900, temperature=0.15,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {raw[:300]}")
    except Exception as e:
        logger.error(f"Groq scoring error: {e}")
        raise

# ─────────────────────────────────────────────────────────────────────────────
# DEBRIEF BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_debrief(scores, sp_name, prev_sale, prev_svc, points_earned, growth_bonus):
    sale, svc = scores["sale_score"], scores["service_score"]
    perf_pts  = int((sale + svc) * 5)
    growth_msg = ""
    if prev_sale > 0 and sale > prev_sale:
        growth_msg += f"Your Sale score of {sale} beats your average of {prev_sale:.1f}. "
    if prev_svc > 0 and svc > prev_svc:
        growth_msg += f"Your Service score of {svc} beats your average of {prev_svc:.1f}. "
    if growth_msg:
        growth_msg = "📈 " + growth_msg.strip()

    strong = "\n".join(f"  ✦ {p}" for p in scores["strong_points"])
    areas  = "\n".join(
        f"  → {a['what']}\n    Why it matters: {a['why']}\n    Try next time: \"{a['suggestion']}\""
        for a in scores["improvement_areas"]
    )
    growth_line = f"  +{POINTS_GROWTH} Growth bonus — improved on last session!\n" if growth_bonus else ""

    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SESSION DEBRIEF — Mansam Parfumery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Well done, {sp_name}. Every session makes you sharper on the floor.

★ WHAT YOU DID WELL
{strong}

◈ AREAS TO GROW
{areas}

◉ YOUR SCORES
  Sale score    : {sale} / 10  — {scores['sale_justification']}
  Service score : {svc}  / 10  — {scores['service_justification']}

{growth_msg}

◎ POINTS EARNED
  +{POINTS_PARTICIP} Participation
  +{perf_pts} Performance  ({sale + svc}/20 combined)
{growth_line}  Total this session: {points_earned} points

◈ NEXT RECOMMENDED SESSION
  {scores['next_session_recommendation']}

Keep going. The best salespeople are not born — they are made, one session at a time.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def ss(key, default=None):
    return st.session_state.get(key, default)

def ss_set(key, val):
    st.session_state[key] = val

# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def metric_card(label, value, col):
    col.markdown(f"""
    <div class="metric-card">
        <div class="val">{value}</div>
        <div class="lbl">{label}</div>
    </div>""", unsafe_allow_html=True)

def tip(text: str):
    """Render a small helper tooltip line."""
    st.markdown(f'<p class="tip">💡 {text}</p>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🕌 Mansam\n### Sales Coach")
        st.divider()

        page = st.radio(
            "Navigate",
            ["🎭 Practice Session", "📈 My Progress", "📊 Manager Dashboard"],
            label_visibility="collapsed",
            help="Switch between practice, your personal stats, and the team dashboard.",
        )
        st.divider()

        st.markdown("**👤 Salesperson**")
        sp_name = st.text_input(
            "Your name",
            value=ss("sp_name", ""),
            placeholder="Enter your name…",
            key="sp_input",
            help="Your name is used to track your points and session history.",
        )
        if sp_name:
            ss_set("sp_name", sp_name)
            upsert_salesperson(sp_name.lower().replace(" ", "_"), sp_name)

        tier = ss("tier", 1)
        st.markdown(
            f'<span class="badge">Tier {tier} · {TIER_CONFIG[tier]["name"]}</span>'
            f'<span class="badge">⭐ {ss("total_points", 0)} pts</span>',
            unsafe_allow_html=True,
        )
        st.divider()

        # Audio toggle
        audio_on = st.toggle(
            "🔊 Voice playback",
            value=ss("audio_on", True),
            help="When ON, the customer's replies are read aloud automatically using text-to-speech.",
        )
        ss_set("audio_on", audio_on)

        st.divider()
        st.caption("Phase 1 MVP · EN + AR · 3 profiles\nGroq · Llama 3.3 70B (free)\nTTS by gTTS (free)")

    # strip emoji prefix for routing
    return page.split(" ", 1)[1] if " " in page else page

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PRACTICE SESSION
# ─────────────────────────────────────────────────────────────────────────────
def page_practice():
    st.markdown("# 🎭 Practice Session")
    sp_name = ss("sp_name", "")
    if not sp_name:
        st.info("👈 Enter your name in the sidebar to begin.")
        tip("Your name is used to save your scores and track progress over time.")
        return

    # ── Profile picker ────────────────────────────────────────────────────────
    if not ss("session_active"):
        st.markdown("### Choose a Customer Profile")
        tip("Each profile simulates a different type of customer you will meet on the floor. Start with Profile 1 if you are new.")
        st.markdown("")

        cols = st.columns(3)
        for i, (pid, p) in enumerate(PROFILES.items()):
            with cols[i]:
                diff_stars = '★' * p['difficulty'] + '☆' * (3 - p['difficulty'])
                st.markdown(f"""
                <div class="profile-card">
                    <div style="font-size:2rem">{p['emoji']}</div>
                    <div style="font-weight:700;font-size:1rem;margin:4px 0">{p['name']}</div>
                    <div style="font-size:0.8rem;color:#8C7A5A;margin-bottom:4px">{p['name_ar']}</div>
                    <div style="font-size:0.85rem;margin-bottom:8px">{p['brief']}</div>
                    <div style="font-size:0.78rem;color:#8C7A5A">Difficulty: {diff_stars}</div>
                </div>""", unsafe_allow_html=True)

                # Language selector per profile
                lang_choice = st.selectbox(
                    "Session language",
                    list(LANG_OPTIONS.keys()),
                    key=f"lang_{pid}",
                    help="English — full English conversation.\nArabic — full Saudi dialect.\nMixed — code-switch between Arabic and English as real customers do.",
                )
                if st.button(f"Start session", key=f"pick_{pid}", use_container_width=True):
                    ss_set("session_active", True)
                    ss_set("active_profile", pid)
                    ss_set("session_lang", LANG_OPTIONS[lang_choice]["code"])
                    ss_set("session_lang_gtts", LANG_OPTIONS[lang_choice]["gtts"])
                    ss_set("messages", [])
                    ss_set("debrief_done", False)
                    ss_set("last_debrief", "")
                    st.rerun()
        return

    profile   = PROFILES[ss("active_profile")]
    lang_code = ss("session_lang", "en")
    lang_gtts = ss("session_lang_gtts", "en")
    is_rtl    = lang_code in ("ar", "mixed")

    lang_label = {"en": "English 🇬🇧", "ar": "Arabic 🇸🇦", "mixed": "Mixed 🇸🇦🇬🇧"}.get(lang_code, "")
    st.markdown(
        f"### {profile['emoji']} {profile['name']}  "
        f'<span class="badge-outline">{lang_label}</span>',
        unsafe_allow_html=True,
    )
    st.caption(profile["brief_ar"] if lang_code == "ar" else profile["brief"])
    tip("Type your response as you would speak to a real customer. There are no wrong answers — every session improves your score.")
    st.divider()

    # ── Debrief view ──────────────────────────────────────────────────────────
    if ss("debrief_done"):
        st.markdown('<div class="debrief-box">' + ss("last_debrief", "") + '</div>',
                    unsafe_allow_html=True)

        # Audio debrief read-out (English TTS)
        if ss("audio_on") and ss("last_debrief"):
            with st.spinner("Generating audio summary…"):
                # Summarise key scores for TTS (avoid reading the whole debrief)
                sale_s = ss("last_scores", {}).get("sale_score", "?")
                svc_s  = ss("last_scores", {}).get("service_score", "?")
                tts_summary = (
                    f"Session complete. {sp_name}, your Sale score is {sale_s} out of 10, "
                    f"and your Service score is {svc_s} out of 10. Well done and keep practising."
                )
                b64 = text_to_audio_b64(tts_summary, "en")
                if b64:
                    st.markdown(audio_player(b64), unsafe_allow_html=True)

        st.markdown("")
        if st.button("🔄 Start New Session"):
            for k in ["session_active","active_profile","messages",
                      "debrief_done","last_debrief","last_scores"]:
                ss_set(k, None)
            st.rerun()
        return

    # ── Live chat ─────────────────────────────────────────────────────────────
    msgs: list = ss("messages", [])

    # Opening line from customer
    if not msgs:
        with st.spinner("Customer entering the store…" if lang_code == "en" else "العميل يدخل المتجر…"):
            try:
                opening = chat_as_customer(profile, [], lang_code)
            except Exception as e:
                st.error(f"Groq API error: {e}")
                st.stop()
        msgs = [{"role": "assistant", "content": opening}]
        ss_set("messages", msgs)
        # Auto-play opening line
        if ss("audio_on"):
            b64 = text_to_audio_b64(opening, lang_gtts)
            ss_set("last_audio", b64)

    # Render chat history
    for idx, m in enumerate(msgs):
        is_last = idx == len(msgs) - 1
        if m["role"] == "user":
            bubble_class = "chat-user-ar" if is_rtl else "chat-user"
            label = "🧑 أنت:" if is_rtl else "🧑 You:"
        else:
            bubble_class = "chat-ai-ar" if is_rtl else "chat-ai"
            label = "👤 العميل:" if is_rtl else "👤 Customer:"

        st.markdown(
            f'<div class="{bubble_class}"><strong>{label}</strong> {m["content"]}</div>',
            unsafe_allow_html=True,
        )
        # Play audio for the latest AI message
        if m["role"] == "assistant" and is_last and ss("audio_on"):
            audio_b64 = ss("last_audio")
            if audio_b64:
                st.markdown(audio_player(audio_b64), unsafe_allow_html=True)

    # ── Input form ────────────────────────────────────────────────────────────
    placeholder = "ماذا تقول للعميل؟" if is_rtl else "What do you say to the customer?"
    send_label  = "إرسال ➤" if is_rtl else "Send ➤"
    end_label   = "إنهاء وتقييم" if is_rtl else "End & Score"

    if is_rtl:
        st.markdown('<div class="rtl-input">', unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_send, col_end = st.columns([5, 1, 1])
        with col_input:
            user_input = st.text_input(
                "response",
                placeholder=placeholder,
                label_visibility="collapsed",
            )
        with col_send:
            send_clicked = st.form_submit_button(send_label, use_container_width=True)
        with col_end:
            end_clicked = st.form_submit_button(end_label, use_container_width=True, type="primary")

    if is_rtl:
        st.markdown('</div>', unsafe_allow_html=True)

    tip(
        "Press 'End & Score' after a natural conversation (aim for 3–6 exchanges). "
        "The AI will score your Sale and Service performance."
        if lang_code == "en"
        else "اضغط 'إنهاء وتقييم' بعد محادثة طبيعية. سيقيّم الذكاء الاصطناعي أدائك."
    )

    # Send message
    if send_clicked and user_input.strip():
        msgs.append({"role": "user", "content": user_input.strip()})
        with st.spinner("Customer responding…" if lang_code == "en" else "العميل يرد…"):
            try:
                reply = chat_as_customer(profile, msgs, lang_code)
            except Exception as e:
                st.error(f"Groq API error: {e}")
                st.stop()
        msgs.append({"role": "assistant", "content": reply})
        ss_set("messages", msgs)
        # Pre-generate audio for next render
        if ss("audio_on"):
            b64 = text_to_audio_b64(reply, lang_gtts)
            ss_set("last_audio", b64)
        else:
            ss_set("last_audio", None)
        st.rerun()

    # End and score
    if end_clicked:
        if len(msgs) < 3:
            st.warning("Have at least 2 exchanges before ending." if lang_code == "en"
                       else "أجرِ محادثتين على الأقل قبل الإنهاء.")
            return

        with st.spinner("Evaluating your session…" if lang_code == "en" else "يتم تقييم جلستك…"):
            try:
                scores = score_session(msgs, lang_code)
            except Exception as e:
                st.error(f"Scoring error: {e}")
                return

            perf_pts  = int((scores["sale_score"] + scores["service_score"]) * 5)
            df_prev   = load_sessions(sp_name)
            prev_sale = float(df_prev["sale_score"].mean()) if not df_prev.empty else 0.0
            prev_svc  = float(df_prev["svc_score"].mean())  if not df_prev.empty else 0.0
            growth    = scores["sale_score"] > prev_sale and prev_sale > 0
            total_pts = POINTS_PARTICIP + perf_pts + (POINTS_GROWTH if growth else 0)

            debrief = build_debrief(scores, sp_name, prev_sale, prev_svc, total_pts, growth)
            save_session(sp_name, profile["id"], lang_code,
                         scores["sale_score"], scores["service_score"],
                         total_pts, msgs, debrief)

            ss_set("total_points", ss("total_points", 0) + total_pts)
            ss_set("last_debrief", debrief)
            ss_set("last_scores", scores)
            ss_set("debrief_done", True)
            ss_set("last_audio", None)
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: MY PROGRESS
# ─────────────────────────────────────────────────────────────────────────────
def page_progress():
    st.markdown("# 📈 My Progress")
    sp_name = ss("sp_name", "")
    if not sp_name:
        st.info("👈 Enter your name in the sidebar.")
        return

    df = load_sessions(sp_name)
    if df.empty:
        st.info("No sessions yet. Complete your first practice session!")
        tip("Each session earns at least 10 participation points. Your scores and history appear here after your first session.")
        return

    c1, c2, c3, c4 = st.columns(4)
    metric_card("Sessions",     len(df),                          c1)
    metric_card("Avg Sale",     f"{df['sale_score'].mean():.1f}", c2)
    metric_card("Avg Service",  f"{df['svc_score'].mean():.1f}",  c3)
    metric_card("Total Points", int(df["points"].sum()),          c4)

    tip("Sale measures closing ability. Service measures how cared-for the customer felt. Both matter equally.")

    st.markdown("### Score Trends")
    df["created_at"] = pd.to_datetime(df["created_at"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["sale_score"],
                             name="Sale",    line=dict(color="#C9A84C", width=2.5),
                             mode="lines+markers"))
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["svc_score"],
                             name="Service", line=dict(color="#8C7A5A", width=2.5),
                             mode="lines+markers"))
    fig.update_layout(
        paper_bgcolor="#FAF6EE", plot_bgcolor="#FAF6EE",
        font=dict(family="Jost", color="#1A1208"),
        yaxis=dict(range=[0, 10], gridcolor="#E8D5A3"),
        xaxis=dict(gridcolor="#E8D5A3"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    if "language" in df.columns:
        st.markdown("### Sessions by Language")
        lang_counts = df["language"].value_counts().reset_index()
        lang_counts.columns = ["Language", "Sessions"]
        lang_counts["Language"] = lang_counts["Language"].map(
            {"en": "English", "ar": "Arabic", "mixed": "Mixed"}
        ).fillna(lang_counts["Language"])
        fig_lang = px.pie(lang_counts, names="Language", values="Sessions",
                          color_discrete_sequence=["#C9A84C","#8C7A5A","#E8D5A3"])
        fig_lang.update_layout(paper_bgcolor="#FAF6EE", font=dict(color="#1A1208"))
        st.plotly_chart(fig_lang, use_container_width=True)

    st.markdown("### Session History")
    display = df[["created_at","profile_id","language","sale_score","svc_score","points"]].copy()
    display.columns = ["Date","Profile","Language","Sale","Service","Points"]
    display["Profile"]  = display["Profile"].map({pid: p["name"] for pid, p in PROFILES.items()})
    display["Language"] = display["Language"].map({"en":"English","ar":"Arabic","mixed":"Mixed"}).fillna("")
    st.dataframe(display, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: MANAGER DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("# 📊 Manager Dashboard")
    st.caption("Enterprise MIS · all salespeople · all sessions")
    tip("This view is for sales managers. It updates live as sessions are completed.")

    all_df = load_all_sessions()
    sp_df  = load_salespeople()

    if all_df.empty:
        st.info("No session data yet.")
        return

    today    = datetime.date.today().isoformat()
    today_df = all_df[all_df["created_at"].str.startswith(today)]

    c1, c2, c3, c4 = st.columns(4)
    metric_card("Sessions Today",    len(today_df),                          c1)
    metric_card("Avg Sale Score",    f"{all_df['sale_score'].mean():.1f}",   c2)
    metric_card("Avg Service Score", f"{all_df['svc_score'].mean():.1f}",    c3)
    metric_card("Salespeople",       len(sp_df),                             c4)

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Team Leaderboard")
        tip("Ranked by total points. Points = participation + performance + growth bonuses.")
        lb = (
            all_df.groupby("salesperson")
            .agg(Sessions=("id","count"),
                 Avg_Sale=("sale_score","mean"),
                 Avg_Service=("svc_score","mean"),
                 Total_Points=("points","sum"))
            .reset_index()
            .sort_values("Total_Points", ascending=False)
        )
        lb["Avg_Sale"]    = lb["Avg_Sale"].round(1)
        lb["Avg_Service"] = lb["Avg_Service"].round(1)
        st.dataframe(lb, use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("### Sale vs Service Distribution")
        tip("A high Sale / low Service pattern = closes deals but feels pushy. Opposite = warm but doesn't convert.")
        fig2 = go.Figure()
        fig2.add_trace(go.Box(y=all_df["sale_score"], name="Sale",
                              marker_color="#C9A84C", line_color="#C9A84C"))
        fig2.add_trace(go.Box(y=all_df["svc_score"],  name="Service",
                              marker_color="#8C7A5A", line_color="#8C7A5A"))
        fig2.update_layout(
            paper_bgcolor="#FAF6EE", plot_bgcolor="#FAF6EE",
            font=dict(family="Jost", color="#1A1208"),
            yaxis=dict(range=[0, 10], gridcolor="#E8D5A3"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Score Trend — All Team")
    all_df["created_at"] = pd.to_datetime(all_df["created_at"])
    trend = (
        all_df.groupby(all_df["created_at"].dt.date)
        .agg(Sale=("sale_score","mean"), Service=("svc_score","mean"))
        .reset_index()
    )
    fig3 = px.line(trend, x="created_at", y=["Sale","Service"],
                   color_discrete_map={"Sale":"#C9A84C","Service":"#8C7A5A"})
    fig3.update_layout(
        paper_bgcolor="#FAF6EE", plot_bgcolor="#FAF6EE",
        font=dict(family="Jost", color="#1A1208"),
        xaxis_title="", yaxis=dict(range=[0,10], gridcolor="#E8D5A3"),
        xaxis=dict(gridcolor="#E8D5A3"),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

    if "language" in all_df.columns:
        st.markdown("### Sessions by Language")
        tip("Tracks how much Arabic practice is happening vs English — useful for Phase 2 readiness assessment.")
        lc = all_df["language"].value_counts().reset_index()
        lc.columns = ["Language","Count"]
        lc["Language"] = lc["Language"].map({"en":"English","ar":"Arabic","mixed":"Mixed"}).fillna(lc["Language"])
        fig4 = px.bar(lc, x="Language", y="Count",
                      color_discrete_sequence=["#C9A84C"])
        fig4.update_layout(paper_bgcolor="#FAF6EE", plot_bgcolor="#FAF6EE",
                           font=dict(color="#1A1208"), margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig4, use_container_width=True)

    with st.expander("📥 Export raw data"):
        tip("Download all session data as CSV for monthly reporting or deeper analysis.")
        csv = all_df.to_csv(index=False)
        st.download_button("Download CSV", csv, "mansam_sessions.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    page = render_sidebar()
    if "Practice" in page:
        page_practice()
    elif "Progress" in page:
        page_progress()
    elif "Dashboard" in page:
        page_dashboard()

if __name__ == "__main__":
    main()
