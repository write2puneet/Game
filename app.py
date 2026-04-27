"""
Mansam Parfumery — Voice Sales Coach  v3
=========================================
Full 20-SKU knowledge base · 3 rich customer personas
Clean centred mic button · Positive coaching debrief

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

# ── global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html,body,[class*="css"],.stApp{
    background:#F5F5F5 !important;
    color:#1A1A1A !important;
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif !important;
}
.block-container{
    max-width:480px !important;
    padding:0 1.1rem 6rem !important;
    margin:0 auto !important;
}
#MainMenu,footer,header,
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"]{display:none !important;}

/* inputs */
.stTextInput input{
    background:#fff !important; color:#1A1A1A !important;
    border:1.5px solid #E0E0E0 !important; border-radius:14px !important;
    font-size:16px !important; padding:.85rem 1rem !important;
    box-shadow:0 1px 4px rgba(0,0,0,.06) !important;
}
.stTextInput input:focus{border-color:#C9A84C !important;
    box-shadow:0 0 0 3px rgba(201,168,76,.15) !important;}
.stTextInput input::placeholder{color:#B0B0B0 !important;}

/* primary buttons */
.stButton>button{
    background:#1A1A1A !important; color:#fff !important;
    border:none !important; border-radius:14px !important;
    font-family:'Inter',sans-serif !important; font-weight:500 !important;
    font-size:.95rem !important; min-height:52px !important;
    width:100% !important; letter-spacing:.01em !important;
}
.stButton>button:hover{background:#333 !important;}

/* ── MIC BUTTON — large orange circle, centred ── */
div[data-testid="stAudioInput"]{
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    width:100% !important;
    margin:.8rem 0 .4rem !important;
    padding:0 !important;
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
}
div[data-testid="stAudioInput"]>div{
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:0 !important;
    width:auto !important;
}
div[data-testid="stAudioInput"] label,
div[data-testid="stAudioInput"] small,
div[data-testid="stAudioInput"] p{display:none !important;}
div[data-testid="stAudioInput"] button{
    width:86px !important; height:86px !important;
    border-radius:50% !important;
    background:#E8521A !important;
    border:none !important; cursor:pointer !important;
    box-shadow:0 6px 28px rgba(232,82,26,.45) !important;
    display:flex !important; align-items:center !important;
    justify-content:center !important;
    transition:transform .12s,box-shadow .12s !important;
    -webkit-tap-highlight-color:transparent !important;
    touch-action:manipulation !important;
}
div[data-testid="stAudioInput"] button:hover{
    transform:scale(1.07) !important;
    box-shadow:0 8px 32px rgba(232,82,26,.55) !important;
}
div[data-testid="stAudioInput"] button:active{transform:scale(.93) !important;}
div[data-testid="stAudioInput"] button svg{
    width:34px !important; height:34px !important;
    color:#fff !important; stroke:#fff !important; fill:none !important;
}
/* pulse while recording */
div[data-testid="stAudioInput"] button[aria-label*="Stop"]{
    background:#B02A08 !important;
    box-shadow:0 6px 32px rgba(176,42,8,.7) !important;
    animation:mpulse 1.1s infinite !important;
}
@keyframes mpulse{
    0%,100%{box-shadow:0 4px 20px rgba(176,42,8,.5);}
    50%{box-shadow:0 4px 44px rgba(176,42,8,.9);}
}

/* cards */
.card{background:#fff;border-radius:14px;padding:1.2rem 1.3rem;
      margin-bottom:.8rem;box-shadow:0 1px 6px rgba(0,0,0,.06);}
.card-dark{background:#1A1A1A;border-radius:14px;padding:1.3rem 1.4rem;margin-bottom:.8rem;}

/* chips */
.chip{display:inline-block;background:#FBF6E9;color:#8B6914;
      border-radius:20px;padding:4px 11px;font-size:.76rem;font-weight:500;margin:2px 2px;}

/* topbar */
.topbar{display:flex;align-items:center;justify-content:space-between;
        padding:.9rem 0 .5rem;border-bottom:1px solid #EBEBEB;margin-bottom:1.2rem;}
.topbar .brand{font-size:.88rem;font-weight:600;color:#1A1A1A;}
.topbar .pts{font-size:.8rem;color:#888;}

/* progress bar */
.prog-wrap{height:3px;background:#E5E5E5;border-radius:2px;margin-bottom:.9rem;}
.prog-fill{height:3px;border-radius:2px;transition:width .5s linear,background .3s;}

/* score card */
.score-pair{display:flex;gap:.8rem;margin-bottom:.9rem;}
.score-card{flex:1;background:#fff;border-radius:14px;padding:1rem .8rem;
            text-align:center;box-shadow:0 1px 6px rgba(0,0,0,.06);}
.score-card .num{font-size:2rem;font-weight:700;color:#1A1A1A;line-height:1;}
.score-card .lbl{font-size:.7rem;color:#B0B0B0;text-transform:uppercase;
                 letter-spacing:.08em;margin-top:.3rem;}
.score-card .just{font-size:.73rem;color:#888;margin-top:.35rem;line-height:1.4;}

/* grow item */
.grow-item{background:#fff;border-left:3px solid #E0E0E0;border-radius:0 10px 10px 0;
           padding:.8rem 1rem;margin:.35rem 0;font-size:.87rem;line-height:1.55;}
.grow-item .try{margin-top:.3rem;font-style:italic;color:#C9A84C;font-size:.84rem;}

/* divider */
.div{border:none;border-top:1px solid #EBEBEB;margin:1rem 0;}

audio{width:100%;height:36px;border-radius:8px;margin:.3rem 0;accent-color:#C9A84C;}
</style>
""", unsafe_allow_html=True)

# ── constants ──────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
SESSION_SECS = 4 * 60

# ── full knowledge base ────────────────────────────────────────────────────────
MANSAM_KB = """
MANSAM — Luxury Arabian Fragrance House. Four collections: Oud, Nayat, Qanun, Buzuq & Riqq.
Brand voice: quiet nobility, heritage, craftsmanship, calm authority. Not loud. Not cheap-chic.
Sales philosophy: storytelling > pushing. Discover the customer first, then match emotion to bottle.
Price register: luxury. Never apologise for price. Anchor on heritage, rarity, and emotional outcome.

FULL SKU LIBRARY (20 EDPs):

OUD COLLECTION
• Hams Min Al Sahraa — Men/family gifting. Rose/Floral/Musk-Oud. "Quiet nobility, inner depth."
• Naseem Al Ward — Unisex top-seller, work/social. Bergamot/Rose-Jasmine/Soft woods. "Graceful optimism, charm."
• Qublat Ward — Travel gifting, elegant unisex. Bergamot/Rose/Oud. "Romantic authority, refined elegance."
• Shatha Biladi — Winter, Saudi identity. Citrus/Floral/Oud. "Pride of origin, rooted identity."

NAYAT COLLECTION
• Aala Taj Warda — Summer evenings. Saffron-Cinnamon/Rose/Warm spicy. "Passion, rise, grandeur."
• Aala Sathi Al Qamar — Men gifting. White flowers-Lily/Musk-Sandalwood. "Joy, glow."
• Fakhamat Al Warda — Women. Rose/Fresh florals/Soft woods. "Royal elegance, visible status."
• Hadeeth Al Rooh — Women. Warm spices/Oriental woods/Amber. "Inner depth, soulfulness."
• Hamsa — Women. Fruity/Patchouli/Sandalwood. "Warmth, social ease."
• Sarhan — Men top-seller, work. Saffron/Leather-Oud/Deep woods. "Vision, pioneering spirit."
• Tahta Al Noujoum — Women top-seller, evenings. Neroli/Orange blossom/Musk-rum. "Dreamy playful charm."
• Min Ana — Travel gifting. Oriental woods/Warm spices. "Self-discovery, individuality."
• Horr Fi Al Riyah — Women. Soft almond/Lily/Sandalwood-Amber. "Freedom, independence."

QANUN COLLECTION
• Safaa Al Nada — Men/family gifting. Bergamot/Rose-LilyOfValley/Sandalwood. "Purity, calm clarity."
• Mamlakati — Winter. Musk/Strong woods/Vanilla. "Ownership, command."
• Al Hawa Ghallab — Women top-seller. Juniper-Saffron/Floral/Lasting woody. "Magnetism, desire."
• Al Shaghaf Al Ahmar — Expressive. Luxurious spices/Rose/Woody. "Passion, intensity."

BUZUQ & RIQQ COLLECTION
• Khatiiiir — Men hero product. Saffron/Leather-Rose/Oud-Frankincense. "Power, danger, bold charisma."
• Amtar — Women summer top-seller. Fruity/Patchouli/Sandalwood. "Fresh optimism, renewal."
• Thawrat Al Ahasseess — Men top-seller. Saffron/Rose/Oud-Incense. "Emotional intensity, rebellion."

EMOTIONAL MAP — use when customer describes a feeling:
NOBILITY     → Shatha Biladi, Hams Min Al Sahraa, Al Shaghaf Al Ahmar
HAPPINESS    → Tahta Al Noujoum, Naseem Al Ward
PLEASURE     → Aala Taj Warda, Hadeeth Al Rooh, Fakhamat Al Warda
GENEROSITY   → Amtar, Horr Fi Al Riyah, Hamsa
PASSION      → Thawrat Al Ahasseess, Khatiiiir, Qublat Ward
DESIRE       → Safaa Al Nada, Al Hawa Ghallab, Mamlakati
PRIDE        → Sarhan, Min Ana

GOLD SERVICE BEHAVIOURS (Service score rubric):
- Warm greeting, no rushing
- Discover first: "Is this for yourself or a gift?" / "What mood are you chasing?"
- Speak of notes as story, not chemistry
- Patience with silence — let the customer smell and reflect
- Close gently: "Shall I wrap this one for you, or would you like to try one more?"
"""

# ── customer profiles ──────────────────────────────────────────────────────────
PROFILES = {
    1: {
        "emoji": "🧔",
        "name": "First-Time Browser",
        "name_ar": "زائر لأول مرة",
        "difficulty": 1,
        "brief": "Curious, low knowledge, needs guidance and reassurance.",
        "opening_en": "Hello… I've never bought an oud before. I was just walking past. Everything looks so expensive. Can you tell me what makes this different?",
        "opening_ar": "السلام عليكم… ما اشتريت عود من قبل. كنت أمشي وشفت المحل. كل شي يبدو غالي. وش اللي يخلي هذا مختلف؟",
        "persona": """You are a first-time browser in a luxury Arabian perfume boutique in Riyadh.
You are curious but intimidated by price and the unfamiliar world of oud.
You know almost nothing about perfume notes.
You warm up ONLY when the salesperson slows down, discovers what YOU like, and tells a story.
If they rush to upsell or dump information you become quieter: "I think I need to come back later."
Buy signal: when they confidently recommend ONE specific bottle with a reason tied to your mood.
Typical objections: "It's a lot of money for something I don't know", "Is it too strong?", "I don't know if I'll like it after an hour."
Speak naturally, short sentences.""",
    },
    2: {
        "emoji": "👩",
        "name": "Gift Shopper",
        "name_ar": "مشتري هدية",
        "difficulty": 1,
        "brief": "Buying for sister's birthday. Indecisive. Needs confident direction.",
        "opening_en": "I need a gift for my sister. Her birthday is this weekend. I honestly have no idea what she'd like. Help me — you pick something.",
        "opening_ar": "أبغى هدية لأختي. عيد ميلادها هذا الأسبوع. والله ما عندي فكرة. أنت اختار لي شي.",
        "persona": """You are shopping for your sister's birthday gift — this weekend.
You don't wear perfume yourself. You know your sister is "elegant, a bit quiet, works in an office."
You want the salesperson to TAKE CHARGE but also reassure you.
You get annoyed if they ask too many vague questions without giving direction.
You love it when they say "For a sister who is elegant and composed, most gift-givers choose X because..."
Buy signal: they pick ONE bottle, justify it in two sentences, and mention gifting or wrapping.
Objections: "What if she already has something like this?", "Is this too personal?", "Can it be returned?"
Speak like someone in a hurry but warm.""",
    },
    3: {
        "emoji": "👴",
        "name": "Oud Loyalist",
        "name_ar": "عاشق العود الكلاسيكي",
        "difficulty": 2,
        "brief": "Expert. 30 years of oud. Tests your knowledge. Respects authenticity.",
        "opening_en": "As-salamu alaykum. I've been wearing oud for thirty years. Tell me — what's the oud origin in your Shatha Biladi? Cambodi? Hindi? And is it real oud or a reconstruction?",
        "opening_ar": "السلام عليكم. أنا ألبس عود من ثلاثين سنة. قول لي — العود في شذى بلادي من وين؟ كامبودي؟ هندي؟ وهو عود حقيقي ولا تركيب؟",
        "persona": """You are a Saudi gentleman in your 50s who has worn oud daily for 30 years.
You own bottles from Ajmal, Arabian Oud, Amouage, Abdul Samad Al Qurashi.
You are polite but testing. You will catch any salesperson who bluffs about oud origins or accord construction.
You respect salespeople who demonstrate genuine knowledge OR are humble and say "Let me check with our perfumer" rather than fake an answer.
Buy signal: salesperson shows genuine knowledge OR honest humility + offers expert backup.
Objections: "Your price is higher than Arabian Oud for less pedigree", "How do I know this isn't synthetic?", "Who is your nose?"
Speak calmly, a little formally, with occasional Arabic phrases like "ma sha Allah" or "tayyib".""",
    },
}

LANG_OPTIONS = {
    "English 🇬🇧":        {"code": "en", "gtts": "en"},
    "العربية 🇸🇦":         {"code": "ar", "gtts": "ar"},
    "Mixed 🔀":            {"code": "mixed", "gtts": "ar"},
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
            name TEXT PRIMARY KEY, total_points INTEGER DEFAULT 0,
            sessions INTEGER DEFAULT 0)"""))
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
            text("SELECT total_points, sessions FROM agents WHERE name=:n"),
            {"n": name}).fetchone()
    return dict(row._mapping) if row else {"total_points": 0, "sessions": 0}

# ── Groq ───────────────────────────────────────────────────────────────────────
def groq_client():
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    if not key:
        st.error("⚠️ Add GROQ_API_KEY to Streamlit secrets.")
        st.stop()
    return Groq(api_key=key)

# ── TTS ────────────────────────────────────────────────────────────────────────
def tts_b64(text: str, lang: str):
    l = "ar" if lang in ("ar", "mixed") else "en"
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=l, slow=False).write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        logger.warning(f"TTS: {e}")
        return None

# ── STT ────────────────────────────────────────────────────────────────────────
def stt(audio_b64: str, lang: str) -> str:
    raw  = base64.b64decode(audio_b64)
    hint = {"en": "en", "ar": "ar", "mixed": None}.get(lang)
    f    = io.BytesIO(raw)
    f.name = "r.webm"
    kw = dict(file=f, model="whisper-large-v3",
              response_format="text", temperature=0.0)
    if hint:
        kw["language"] = hint
    r = groq_client().audio.transcriptions.create(**kw)
    return (r if isinstance(r, str) else r.text).strip()

# ── Customer LLM ───────────────────────────────────────────────────────────────
def customer_reply(profile, messages, lang) -> str:
    if lang == "ar":
        lang_rule = (
            "تكلّم فقط بالعربية السعودية العامية. "
            f"جملة الافتتاح: {profile['opening_ar']}"
        )
    elif lang == "mixed":
        lang_rule = f"Mix Saudi Arabic and English freely. Start: {profile['opening_ar']}"
    else:
        lang_rule = f"Speak natural English. Opening: {profile['opening_en']}"

    sys = f"""{profile['persona']}

LANGUAGE: {lang_rule}

KNOWLEDGE BASE:
{MANSAM_KB}

CRITICAL:
- Stay in character. Never reveal you are an AI.
- MAX 2 short sentences per reply — this is a voice conversation.
- React warmly to good technique; push back on generic or rushed pitches.
"""
    msgs = [{"role": "system", "content": sys}]
    if not messages:
        msgs.append({"role": "user",
                     "content": "[Session starts. Say your opening line naturally — one sentence only.]"})
    else:
        msgs.extend(messages)

    r = groq_client().chat.completions.create(
        model=GROQ_MODEL, messages=msgs, max_tokens=90, temperature=0.9)
    return r.choices[0].message.content.strip()

# ── Scorer ─────────────────────────────────────────────────────────────────────
def score_transcript(transcript, lang) -> dict:
    lang_note = {
        "ar":    "Arabic session — include Arabic fluency and cultural register in Service score.",
        "mixed": "Code-switching session — reward natural language blending in Service score.",
        "en":    "English session.",
    }.get(lang, "")

    sys = f"""You are a warm, encouraging sales coach for Mansam Parfumery. {lang_note}

{MANSAM_KB}

SALE SCORE (1-10): needs discovery, product knowledge, storytelling, objections, close.
SERVICE SCORE (1-10): warmth, patience, listening, cultural appropriateness, pacing.

Your tone must be POSITIVE and ENCOURAGING throughout. Always find something genuine to praise.
Frame all growth areas as opportunities, never as failures.

Return ONLY valid JSON — no markdown, no extra text:
{{
  "sale_score": <1-10>,
  "sale_justification": "<one warm encouraging sentence>",
  "service_score": <1-10>,
  "service_justification": "<one warm encouraging sentence>",
  "strong_points": ["<specific praised moment>", "<specific praised moment>", "<specific praised moment>"],
  "growth_areas": [
    {{"observation": "<what happened>", "tip": "<exact phrase or technique to try next time>"}},
    {{"observation": "<what happened>", "tip": "<exact phrase or technique to try next time>"}}
  ],
  "next_challenge": "<which profile + specific focus area for next session>",
  "encouragement": "<2 sentences of genuine specific encouragement — mention what made this session unique>"
}}"""

    tx = "\n".join(
        f"{'SALESPERSON' if m['role']=='user' else 'CUSTOMER'}: {m['content']}"
        for m in transcript)
    r = groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user",   "content": f"Score this session:\n\n{tx}"},
        ],
        max_tokens=700, temperature=0.15)
    raw = r.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)

# ── state helpers ───────────────────────────────────────────────────────────────
def ss(k, d=None):  return st.session_state.get(k, d)
def sset(k, v):     st.session_state[k] = v

def topbar(right=""):
    pts = ss("total_points", 0)
    r   = right or (f"⭐ {pts} pts" if ss("agent_name") else "")
    st.markdown(
        f'<div class="topbar"><span class="brand">🕌 Mansam Sales Coach</span>'
        f'<span class="pts">{r}</span></div>',
        unsafe_allow_html=True)

def fmt_time(secs):
    m, s = divmod(max(0, int(secs)), 60)
    return f"{m}:{s:02d}"

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — WELCOME
# ══════════════════════════════════════════════════════════════════════════════
def screen_welcome():
    topbar()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## What's your name?")
    st.markdown(
        "<p style='color:#888;font-size:.88rem;margin-top:-.3rem;margin-bottom:1.2rem'>"
        "We'll track your progress and personalise your coaching.</p>",
        unsafe_allow_html=True)

    name = st.text_input("name", placeholder="Enter your name…",
                         label_visibility="collapsed", key="name_input")
    if st.button("Continue →"):
        if name.strip():
            clean = name.strip()
            sset("agent_name", clean)
            upsert_agent(clean)
            data = load_agent(clean)
            sset("total_points", data["total_points"])
            sset("screen", "pick_profile")
            st.rerun()
        else:
            st.warning("Please enter your name.")

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — PICK PROFILE
# ══════════════════════════════════════════════════════════════════════════════
def screen_pick_profile():
    topbar()
    name = ss("agent_name", "")
    st.markdown(f"<br><p style='color:#888;font-size:.85rem'>Hi {name} 👋</p>",
                unsafe_allow_html=True)
    st.markdown("## Choose your customer")
    st.markdown(
        "<p style='color:#888;font-size:.87rem;margin-top:-.3rem;margin-bottom:1.2rem'>"
        "You'll have a real sales conversation with this AI customer.</p>",
        unsafe_allow_html=True)

    for pid, p in PROFILES.items():
        dots = "●" * p["difficulty"] + "○" * (3 - p["difficulty"])
        st.markdown(f"""
<div style="background:#fff;border-radius:14px;padding:1.1rem 1.2rem;
            margin-bottom:.5rem;box-shadow:0 1px 6px rgba(0,0,0,.06);
            display:flex;align-items:center;gap:1rem">
  <span style="font-size:2.2rem;line-height:1">{p['emoji']}</span>
  <div>
    <div style="font-weight:600;font-size:.97rem;color:#1A1A1A">{p['name']}</div>
    <div style="font-size:.78rem;color:#8C7A5A;margin:.1rem 0">{p['name_ar']}</div>
    <div style="font-size:.82rem;color:#888">{p['brief']}</div>
    <div style="font-size:.73rem;color:#B0B0B0;margin-top:.25rem">Difficulty: {dots}</div>
  </div>
</div>""", unsafe_allow_html=True)
        if st.button(f"Start with {p['name']}", key=f"p{pid}",
                     use_container_width=True):
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
    st.markdown(f"<br><p style='color:#888;font-size:.84rem'>"
                f"{p['emoji']} {p['name']}</p>", unsafe_allow_html=True)
    st.markdown("## Session language")
    st.markdown(
        "<p style='color:#888;font-size:.87rem;margin-top:-.3rem;margin-bottom:1.3rem'>"
        "Speak however feels natural on your shop floor.</p>",
        unsafe_allow_html=True)

    for label, cfg in LANG_OPTIONS.items():
        if st.button(label, key=f"l{cfg['code']}", use_container_width=True):
            sset("session_lang", cfg["code"])
            sset("screen", "instructions")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back", use_container_width=False):
        sset("screen", "pick_profile")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — INSTRUCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def screen_instructions():
    topbar()
    pid  = ss("selected_profile", 1)
    p    = PROFILES[pid]
    lang = ss("session_lang", "en")
    ll   = {"en": "English", "ar": "Arabic", "mixed": "Arabic + English"}.get(lang)

    st.markdown(f"<br>", unsafe_allow_html=True)
    st.markdown(f"## Ready, {ss('agent_name', '')}?")
    st.markdown(f"""
<div class="card-dark">
  <p style="color:#C9A84C;font-weight:600;font-size:.82rem;
            text-transform:uppercase;letter-spacing:.06em;margin:0 0 .7rem">Your session</p>
  <p style="color:#E5E5E5;font-size:.93rem;line-height:1.8;margin:0">
    {p['emoji']} &nbsp;Customer: <b style="color:#fff">{p['name']}</b><br>
    🗣️ &nbsp;Language: <b style="color:#fff">{ll}</b><br>
    ⏱️ &nbsp;Duration: <b style="color:#fff">4 minutes</b>
  </p>
</div>""", unsafe_allow_html=True)

    steps = [
        ("Customer speaks first", "Listen to their opening line."),
        ("Tap the orange button and speak", "Respond naturally — just like on the shop floor."),
        ("Tap again to send", "The customer replies automatically."),
        ("Keep going for 4 minutes", "Natural conversation. No scripts needed."),
        ("Full coaching at the end", "Scores, strengths and personalised tips."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(f"""
<div style="display:flex;gap:.8rem;align-items:flex-start;margin:.5rem 0">
  <div style="min-width:24px;height:24px;border-radius:50%;background:#C9A84C;
              color:#1A1A1A;display:flex;align-items:center;justify-content:center;
              font-weight:700;font-size:.78rem;flex-shrink:0">{i}</div>
  <div style="font-size:.88rem;line-height:1.5;padding-top:.1rem">
    <b>{title}</b><br>
    <span style="color:#888">{desc}</span>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 Microphone permission is required once. Allow it, then just speak.")

    if st.button("Start Session →", use_container_width=True):
        sset("messages", [])
        sset("session_start", time.time())
        sset("pending_audio", None)
        sset("last_processed_bytes", b"")
        sset("screen", "session")
        st.rerun()

    if st.button("← Change customer", use_container_width=False):
        sset("screen", "pick_profile")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — LIVE SESSION
# ══════════════════════════════════════════════════════════════════════════════
def screen_session():
    pid       = ss("selected_profile", 1)
    p         = PROFILES[pid]
    lang      = ss("session_lang", "en")
    msgs      = ss("messages", [])
    is_rtl    = lang in ("ar", "mixed")
    cust_lbl  = "العميل" if is_rtl else "Customer"

    # timer
    if not ss("session_start"):
        sset("session_start", time.time())
    elapsed   = time.time() - ss("session_start")
    remaining = max(0.0, SESSION_SECS - elapsed)
    pct       = remaining / SESSION_SECS * 100
    bar_color = "#E07000" if remaining < 60 else "#C9A84C"
    t_color   = "#E07000" if remaining < 60 else "#888"
    ll        = {"en": "EN 🇬🇧", "ar": "AR 🇸🇦", "mixed": "Mixed 🔀"}.get(lang, "")

    if remaining <= 0 and len(msgs) >= 2:
        sset("screen", "scoring")
        st.rerun()

    # generate opening once
    if not msgs:
        with st.spinner(""):
            opening = customer_reply(p, [], lang)
        msgs.append({"role": "assistant", "content": opening})
        sset("messages", msgs)
        sset("pending_audio", tts_b64(opening, lang))
        st.rerun()

    # ── session-screen CSS (scoped, no leaking) ───────────────────────────────
    st.markdown("""
<style>
.block-container{padding-bottom:2rem !important;}
</style>""", unsafe_allow_html=True)

    # ── thin progress bar ─────────────────────────────────────────────────────
    st.markdown(
        f'<div class="prog-wrap"><div class="prog-fill" '
        f'style="width:{pct:.1f}%;background:{bar_color}"></div></div>',
        unsafe_allow_html=True)

    # ── mini header ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:.4rem 0 .8rem">'
        f'<span style="font-size:.8rem;color:#888">{p["emoji"]} {p["name"]} · {ll}</span>'
        f'<span style="font-size:.8rem;color:{t_color};font-weight:500">⏱ {fmt_time(remaining)}</span>'
        f'</div>',
        unsafe_allow_html=True)

    # ── customer bubble ───────────────────────────────────────────────────────
    last_customer = next(
        (m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "…")

    border_style = (
        "border-right:3px solid #C9A84C;border-left:none"
        if is_rtl else
        "border-left:3px solid #C9A84C"
    )
    dir_style = "direction:rtl;text-align:right" if is_rtl else ""

    st.markdown(
        f'<p style="font-size:.68rem;font-weight:600;color:#B0B0B0;'
        f'text-transform:uppercase;letter-spacing:.1em;margin:0 0 .5rem">'
        f'{cust_lbl}</p>'
        f'<div style="background:#fff;border-radius:20px;padding:1.4rem 1.5rem;'
        f'font-size:1.05rem;line-height:1.7;color:#1A1A1A;'
        f'box-shadow:0 1px 10px rgba(0,0,0,.08);{border_style};{dir_style};'
        f'word-wrap:break-word;overflow-wrap:break-word;margin-bottom:.8rem">'
        f'{last_customer}</div>',
        unsafe_allow_html=True)

    # ── autoplay customer audio once ──────────────────────────────────────────
    if ss("pending_audio"):
        b64 = ss("pending_audio")
        st.markdown(
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>',
            unsafe_allow_html=True)
        sset("pending_audio", None)

    # ── hint text ─────────────────────────────────────────────────────────────
    turn_count = len([m for m in msgs if m["role"] == "user"])
    hint = (
        ("اضغط الزر للرد" if is_rtl else "Tap the button below to respond")
        if turn_count == 0 else
        ("اضغط للرد" if is_rtl else "Tap to respond")
    )
    st.markdown(
        f'<p style="text-align:center;font-size:.76rem;color:#C0C0C0;'
        f'letter-spacing:.04em;text-transform:uppercase;margin:1rem 0 0">'
        f'{hint}</p>',
        unsafe_allow_html=True)

    # ── MIC INPUT — centred via global CSS ────────────────────────────────────
    audio_val = st.audio_input(
        "Record",
        key=f"mic_{len(msgs)}",
        label_visibility="collapsed",
    )

    # ── done button ───────────────────────────────────────────────────────────
    st.markdown(
        '<p style="text-align:center;margin-top:.5rem">',
        unsafe_allow_html=True)
    done = st.button("Done — get my feedback", key="done_btn")
    st.markdown('</p>', unsafe_allow_html=True)
    if done:
        if len(msgs) >= 3:
            sset("screen", "scoring")
            st.rerun()
        else:
            st.toast("Have at least one exchange first 💪")

    # ── process recording ─────────────────────────────────────────────────────
    if audio_val is not None:
        raw = audio_val.read()
        if raw and raw != ss("last_processed_bytes", b""):
            sset("last_processed_bytes", raw)
            with st.spinner(""):
                try:
                    spoken = stt(base64.b64encode(raw).decode(), lang)
                except Exception as e:
                    st.error(f"Could not transcribe: {e}")
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
    st.markdown(
        "<p style='color:#888;font-size:.88rem'>"
        "Your coach is reviewing the conversation.</p>",
        unsafe_allow_html=True)

    msgs = ss("messages", [])
    lang = ss("session_lang", "en")
    pid  = ss("selected_profile", 1)

    with st.spinner(""):
        try:
            scores = score_transcript(msgs, lang)
        except Exception as e:
            st.error(f"Scoring error: {e}")
            if st.button("Retry"):
                st.rerun()
            return

    perf = int((scores["sale_score"] + scores["service_score"]) * 5)
    pts  = 10 + perf
    save_session(ss("agent_name", ""), pid, lang,
                 scores["sale_score"], scores["service_score"],
                 pts, msgs, json.dumps(scores))
    sset("last_scores", scores)
    sset("last_points", pts)
    sset("total_points", ss("total_points", 0) + pts)
    sset("screen", "debrief")
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 7 — DEBRIEF
# ══════════════════════════════════════════════════════════════════════════════
def screen_debrief():
    scores = ss("last_scores", {})
    pts    = ss("last_points", 10)
    name   = ss("agent_name", "")
    lang   = ss("session_lang", "en")
    pid    = ss("selected_profile", 1)
    p      = PROFILES[pid]
    sale   = scores.get("sale_score", 0)
    svc    = scores.get("service_score", 0)
    enc    = scores.get("encouragement", "")

    topbar(f"⭐ {ss('total_points', 0)} pts total")

    # hero
    st.markdown(f"""
<br>
<div class="card-dark" style="text-align:center">
  <div style="font-size:2.2rem;margin-bottom:.4rem">🎉</div>
  <div style="font-size:1.4rem;font-weight:700;color:#C9A84C;
              font-family:'Inter',sans-serif;margin-bottom:.2rem">
    Well done, {name}!
  </div>
  <div style="color:#888;font-size:.85rem">
    {p['emoji']} {p['name']} · session complete
  </div>
</div>""", unsafe_allow_html=True)

    # scores
    sale_j = scores.get("sale_justification", "")
    svc_j  = scores.get("service_justification", "")
    st.markdown(f"""
<div class="score-pair">
  <div class="score-card">
    <div class="num">{sale}<span style="font-size:1rem;color:#C0C0C0">/10</span></div>
    <div class="lbl">Sale</div>
    <div class="just">{sale_j}</div>
  </div>
  <div class="score-card">
    <div class="num">{svc}<span style="font-size:1rem;color:#C0C0C0">/10</span></div>
    <div class="lbl">Service</div>
    <div class="just">{svc_j}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # points
    st.markdown(
        f'<div style="background:#1A1A1A;color:#fff;border-radius:12px;'
        f'padding:.85rem 1rem;text-align:center;font-weight:600;'
        f'font-size:.97rem;margin-bottom:.9rem">⭐ +{pts} points earned</div>',
        unsafe_allow_html=True)

    # encouragement
    if enc:
        st.markdown(
            f'<div class="card" style="border-left:3px solid #C9A84C;font-size:.9rem;'
            f'line-height:1.6">{enc}</div>',
            unsafe_allow_html=True)

    # strong points
    strongs = scores.get("strong_points", [])
    if strongs:
        st.markdown(
            '<p style="font-size:.72rem;font-weight:600;color:#B0B0B0;'
            'text-transform:uppercase;letter-spacing:.09em;margin:.6rem 0 .35rem">'
            'What you did well</p>',
            unsafe_allow_html=True)
        chips = "".join(f'<span class="chip">{s}</span>' for s in strongs)
        st.markdown(f'<div style="margin-bottom:.8rem">{chips}</div>',
                    unsafe_allow_html=True)

    # growth areas
    grows = scores.get("growth_areas", [])
    if grows:
        st.markdown(
            '<p style="font-size:.72rem;font-weight:600;color:#B0B0B0;'
            'text-transform:uppercase;letter-spacing:.09em;margin:.6rem 0 .35rem">'
            'One thing to try next time</p>',
            unsafe_allow_html=True)
        for g in grows:
            obs = g.get("observation", "")
            tip = g.get("tip", "")
            st.markdown(
                f'<div class="grow-item">{obs}'
                f'<div class="try">Try: &ldquo;{tip}&rdquo;</div></div>',
                unsafe_allow_html=True)

    # next challenge
    nxt = scores.get("next_challenge", "")
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
            '🔊 Hear your feedback</p>',
            unsafe_allow_html=True)
        st.markdown(
            f'<audio controls src="data:audio/mp3;base64,{b64}"></audio>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Practice Again →", use_container_width=True):
        for k in ["messages", "session_start", "last_scores",
                  "last_points", "session_lang", "selected_profile",
                  "pending_audio", "last_processed_bytes"]:
            sset(k, None)
        sset("screen", "pick_profile")
        st.rerun()

    st.markdown(
        '<p style="text-align:center;margin-top:.6rem">',
        unsafe_allow_html=True)
    if st.button("Switch agent", use_container_width=False):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown('</p>', unsafe_allow_html=True)

# ── router ──────────────────────────────────────────────────────────────────────
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
