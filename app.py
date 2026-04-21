"""
Mansam Parfumery — Gamified AI Sales Coaching Agent
====================================================
Streamlit MVP · Phase 1 (English, 3 profiles, Sale+Service scoring)
LLM: Google Gemini 2.0 Flash (free tier — 1,500 req/day)

Get your free key at: https://aistudio.google.com
Set it in .env or Streamlit secrets:
  GEMINI_API_KEY=AIza...
"""

import os
import json
import datetime
import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mansam | Sales Coach",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Jost:wght@300;400;500&display=swap');

:root {
    --gold:    #C9A84C;
    --gold-lt: #E8D5A3;
    --dark:    #1A1208;
    --mid:     #2E2415;
    --cream:   #FAF6EE;
    --muted:   #8C7A5A;
}

html, body, [class*="css"] {
    font-family: 'Jost', sans-serif;
    background-color: var(--cream);
    color: var(--dark);
}

h1, h2, h3 { font-family: 'Cormorant Garamond', serif; color: var(--dark); }

.stButton > button {
    background: var(--gold);
    color: var(--dark);
    border: none;
    border-radius: 2px;
    font-family: 'Jost', sans-serif;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.55rem 1.4rem;
    transition: background 0.2s;
}
.stButton > button:hover { background: var(--gold-lt); }

.stTextInput input, .stSelectbox select, .stTextArea textarea {
    border: 1px solid var(--gold-lt);
    border-radius: 2px;
    background: #fff;
}

.metric-card {
    background: var(--mid);
    color: var(--gold-lt);
    border-radius: 4px;
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
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
}

.badge {
    display: inline-block;
    background: var(--gold);
    color: var(--dark);
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    margin: 2px;
}

.chat-user {
    background: #fff;
    border-left: 3px solid var(--gold);
    padding: 0.7rem 1rem;
    border-radius: 0 4px 4px 0;
    margin-bottom: 0.5rem;
}
.chat-ai {
    background: var(--mid);
    color: var(--cream);
    border-left: 3px solid var(--muted);
    padding: 0.7rem 1rem;
    border-radius: 0 4px 4px 0;
    margin-bottom: 0.5rem;
}
.debrief-box {
    background: #fff;
    border: 1px solid var(--gold-lt);
    border-radius: 4px;
    padding: 1.5rem;
    margin-top: 1rem;
    white-space: pre-wrap;
    font-family: 'Jost', sans-serif;
    font-size: 0.92rem;
    line-height: 1.7;
}

div[data-testid="stSidebar"] { background: var(--dark); }
div[data-testid="stSidebar"] * { color: var(--gold-lt) !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"

TIER_CONFIG = {
    1: {"name": "Beginner",     "sessions_needed": 10, "avg_score_needed": 6},
    2: {"name": "Intermediate", "sessions_needed": 15, "avg_score_needed": 7},
    3: {"name": "Expert",       "sessions_needed": 999, "avg_score_needed": 9},
}

POINTS_PARTICIPATION = 10
POINTS_GROWTH        = 20

# ── Customer profiles ─────────────────────────────────────────────────────────
PROFILES = {
    1: {
        "id": 1,
        "name": "First-Time Browser",
        "tier": 1,
        "emoji": "👀",
        "brief": "Curious, low product knowledge, needs guidance and reassurance.",
        "opening_line": "Hi… I'm just looking. I don't really know much about perfumes honestly.",
        "personality": "Shy, easily overwhelmed, responds well to warmth and simplicity.",
        "triggers": ["feeling special", "easy recommendation", "not being judged"],
        "objections": [
            "I don't know what I like yet.",
            "There are so many options, I'm overwhelmed.",
            "I usually just buy whatever smells nice.",
        ],
        "buy_signal": "Asks 'do you think this one would suit me?' or lingers on a scent.",
        "difficulty": 1,
    },
    2: {
        "id": 2,
        "name": "Gift Shopper",
        "tier": 1,
        "emoji": "🎁",
        "brief": "Buying for someone else, unsure of preferences, needs help narrowing.",
        "opening_line": "I need to buy a gift for my sister — I have no idea what she'd like.",
        "personality": "Indecisive, slightly anxious about getting it wrong, grateful for confident guidance.",
        "triggers": ["reassurance the gift is right", "beautiful packaging", "value for money"],
        "objections": [
            "I'm not sure she'd like oud.",
            "What if she already has this one?",
            "Is this too expensive for a casual gift?",
        ],
        "buy_signal": "Says 'that sounds like something she'd actually love' or asks about gift wrapping.",
        "difficulty": 1,
    },
    3: {
        "id": 3,
        "name": "Classic Oud Loyalist",
        "tier": 1,
        "emoji": "🏺",
        "brief": "Knows exactly what they want — values heritage and authenticity.",
        "opening_line": "I've been wearing Saudi oud for twenty years. Show me what you have.",
        "personality": "Confident, discerning, slightly impatient with basic pitches. Respects expertise.",
        "triggers": ["craftsmanship", "heritage", "exclusivity", "authenticity of ingredients"],
        "objections": [
            "I've tried everything — what makes yours different?",
            "This smells like a blend, not pure oud.",
            "I don't trust modern perfumery to handle oud properly.",
        ],
        "buy_signal": "Pauses and inhales deeply, asks about origin of the oud wood.",
        "difficulty": 2,
    },
}

# ── Knowledge base (expand with real Mansam catalogue before go-live) ─────────
KNOWLEDGE_BASE = """
MANSAM PARFUMERY — KNOWLEDGE BASE (PHASE 1 SAMPLE)

BRAND POSITIONING
Mansam is a luxury Arabian perfumery house rooted in the heritage of the Arabian Peninsula.
Every fragrance is crafted to carry a story — of desert landscapes, ancient trade routes,
and the intimate rituals of Saudi hospitality. The brand promise: authentic luxury, never imitation.

CUSTOMER SERVICE STANDARDS
- Greet every customer warmly within 30 seconds of entry.
- Ask one honest question before recommending: "Are you looking for something for yourself or as a gift?"
- Offer a scent strip or skin test before pitching price.
- Never rush. Silence while a customer smells is sacred — do not fill it with chatter.
- Close with a suggestion, not a push: "I think this one found you."
- Always offer to wrap and include a handwritten note for gifts.

PRODUCT CATALOGUE (SAMPLE)
1. Al Majd (العظمة) — Oud & Rose
   Family: Oriental Woody | Notes: Agarwood / Taif Rose / Amber
   Concentration: Extrait | Sizes: 30ml SAR 650 / 50ml SAR 950
   Story: Named for glory — worn at weddings and royal gatherings for generations.

2. Sahara Musk — White Musk & Sandalwood
   Family: Soft Oriental | Notes: White Musk / Sandalwood / Vanilla
   Concentration: EDP | Sizes: 50ml SAR 380 / 100ml SAR 520
   Story: The gentlest whisper of the desert at dawn. Perfect for daily wear and gifts.

3. Darb Al Hind (درب الهند) — Spiced Oud
   Family: Spicy Oriental | Notes: Indian Oud / Saffron / Cardamom / Patchouli
   Concentration: EDP Intense | Sizes: 50ml SAR 820
   Story: Named for the ancient incense trade route. Bold, complex, unforgettable.

OBJECTION HANDLING
- "Too expensive": "This is an extrait — twice the concentration of a standard EDP.
  You wear it 12–14 hours per application. Per wear, it is more economical than it looks."
- "Not sure about oud": "Let me start with Sahara Musk — soft, no smoke, just warmth.
  Then we can travel further if you'd like."
- "Already have perfume": "A great collection needs variety. This one is for occasions
  when you want to be remembered."

STORYTELLING APPROACH
Open with place, not product — describe the landscape or moment the fragrance was inspired by,
then let the customer smell before naming the price.
"""

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "mansam_coach.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson  TEXT    NOT NULL,
                profile_id   INTEGER NOT NULL,
                sale_score   REAL,
                svc_score    REAL,
                points       INTEGER DEFAULT 0,
                transcript   TEXT,
                debrief      TEXT,
                created_at   TEXT DEFAULT (datetime('now'))
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
            VALUES (:u, :d)
            ON CONFLICT(username) DO NOTHING
        """), {"u": username, "d": display_name})
        conn.commit()

def save_session(salesperson, profile_id, sale, svc, points, transcript, debrief):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO sessions
              (salesperson, profile_id, sale_score, svc_score, points, transcript, debrief)
            VALUES (:sp, :pid, :sale, :svc, :pts, :tx, :db)
        """), dict(sp=salesperson, pid=profile_id, sale=sale, svc=svc,
                   pts=points, tx=json.dumps(transcript), db=debrief))
        conn.execute(text("""
            UPDATE salespeople SET total_points = total_points + :pts WHERE username = :u
        """), {"pts": points, "u": salesperson})
        conn.commit()

def load_sessions(salesperson: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            "SELECT * FROM sessions WHERE salesperson = :sp ORDER BY created_at DESC",
            conn, params={"sp": salesperson}
        )

def load_all_sessions() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM sessions ORDER BY created_at DESC", conn)

def load_salespeople() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM salespeople", conn)

# ── Gemini client ─────────────────────────────────────────────────────────────
def get_gemini_model(system_instruction: str):
    """Return a configured Gemini GenerativeModel with the given system instruction."""
    # Try .env first, then Streamlit secrets
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = ""

    if not api_key:
        st.error(
            "⚠️ GEMINI_API_KEY not found.\n\n"
            "On Streamlit Cloud: go to **Manage app → Settings → Secrets** and add:\n"
            "```\nGEMINI_API_KEY = \"AIza...your-key\"\n```\n"
            "Get a free key at https://aistudio.google.com"
        )
        st.stop()

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_instruction,
    )

# ── Prompt builders ───────────────────────────────────────────────────────────
def persona_system(profile: dict) -> str:
    return f"""You are playing a customer at Mansam Parfumery, a luxury Arabian perfume brand in Saudi Arabia.

CUSTOMER PROFILE: {profile['name']}
PERSONALITY: {profile['personality']}
MOTIVATION: {profile['brief']}
OPENING LINE (use this when the session starts): {profile['opening_line']}
EMOTIONAL TRIGGERS: {', '.join(profile['triggers'])}
TYPICAL OBJECTIONS:
{chr(10).join('- ' + o for o in profile['objections'])}
BUY SIGNAL: {profile['buy_signal']}

BRAND KNOWLEDGE (what the customer may ask about):
{KNOWLEDGE_BASE}

RULES:
- Stay in character at all times. Never break the fourth wall or mention you are an AI.
- Be realistic — push back naturally, ask questions, express hesitation.
- React warmly to good selling technique; go cooler to poor technique.
- Keep responses to 2–4 sentences — you are a customer, not an essay writer.
- Speak naturally in English (Phase 1).
- When the buy signal condition is met, express genuine interest in purchasing.
"""

def scoring_system() -> str:
    return f"""You are an expert sales coach evaluating a role-play session transcript from Mansam Parfumery.

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

SCORING RUBRIC — SALE (1–10): Can the salesperson close?
10  Perfect needs discovery, compelling story, all objections handled, natural close, upsell attempted
8–9 Strong with minor gaps
6–7 Adequate — identified needs, made recommendation, weak close or missed upsell
4–5 Partial — some product knowledge but poor objection handling or no close attempt
2–3 Minimal — relied on customer to drive, little technique
1   No selling behaviour observed

SCORING RUBRIC — SERVICE (1–10): Does the customer feel cared for?
10  Warm, patient, culturally appropriate, active listening, never rushed
8–9 Mostly warm with minor lapses
6–7 Generally polite but mechanical or slightly rushed
4–5 Transactional — no genuine connection built
2–3 Cold or impatient at moments
1   Rude, dismissive, or inappropriate

IMPORTANT: Respond ONLY with a valid JSON object. No markdown fences, no extra text.
Use this exact structure:
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

# ── Gemini chat helpers ───────────────────────────────────────────────────────
def _to_gemini_history(messages: list) -> list:
    """
    Convert our internal message list [{"role":"user"|"assistant","content":"..."}]
    to Gemini's format [{"role":"user"|"model","parts":["..."]}].
    Gemini requires conversation to start with a user turn and alternate strictly.
    We filter out any leading assistant messages.
    """
    history = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})
    return history


def chat_as_customer(profile: dict, messages: list) -> str:
    """
    Send the conversation history to Gemini playing the customer persona.
    messages: list of {"role": "user"|"assistant", "content": "..."}
    """
    model = get_gemini_model(persona_system(profile))

    # Separate history from the last user message
    if not messages:
        # First turn — ask persona to deliver opening line
        response = model.generate_content(
            "[Session starts. You are now in the store. Deliver your opening line naturally.]"
        )
        return response.text.strip()

    gemini_history = _to_gemini_history(messages[:-1])
    last_msg = messages[-1]["content"]

    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(last_msg)
    return response.text.strip()


def score_session(transcript: list) -> dict:
    """Score the completed transcript and return a parsed dict."""
    model = get_gemini_model(scoring_system())

    transcript_text = "\n".join(
        f"{'SALESPERSON' if m['role'] == 'user' else 'CUSTOMER'}: {m['content']}"
        for m in transcript
    )
    prompt = f"Please score this sales role-play session:\n\n{transcript_text}"
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown fences if Gemini adds them anyway
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:].strip()

    return json.loads(raw)


# ── Debrief builder ───────────────────────────────────────────────────────────
def build_debrief(scores: dict, sp_name: str,
                  prev_sale_avg: float, prev_svc_avg: float,
                  points_earned: int, growth_bonus: bool) -> str:
    sale = scores["sale_score"]
    svc  = scores["service_score"]

    growth_msg = ""
    if prev_sale_avg > 0 and sale > prev_sale_avg:
        growth_msg += f"Your Sale score of {sale} beats your previous average of {prev_sale_avg:.1f}. "
    if prev_svc_avg > 0 and svc > prev_svc_avg:
        growth_msg += f"Your Service score of {svc} beats your previous average of {prev_svc_avg:.1f}. "
    if growth_msg:
        growth_msg = "📈 " + growth_msg.strip()

    strong = "\n".join(f"  ✦ {p}" for p in scores["strong_points"])
    areas = "\n".join(
        f"  → {a['what']}\n"
        f"    Why it matters: {a['why']}\n"
        f"    Try next time: \"{a['suggestion']}\""
        for a in scores["improvement_areas"]
    )
    perf_pts = int((sale + svc) * 5)
    growth_line = f"  +{POINTS_GROWTH} Growth bonus — improved on last session!\n" if growth_bonus else ""

    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SESSION DEBRIEF — Mansam Parfumery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Well done for completing this session, {sp_name}. Every practice session makes you sharper on the floor — and today you showed real commitment.

★ WHAT YOU DID WELL
{strong}

◈ AREAS TO GROW
{areas}

◉ YOUR SCORES
  Sale score    : {sale} / 10  — {scores['sale_justification']}
  Service score : {svc}  / 10  — {scores['service_justification']}

{growth_msg}

◎ POINTS EARNED THIS SESSION
  +{POINTS_PARTICIPATION} Participation
  +{perf_pts} Performance  ({sale + svc}/20 combined)
{growth_line}  Total this session: {points_earned} points

◈ NEXT RECOMMENDED SESSION
  {scores['next_session_recommendation']}

Keep going. The best salespeople are not born — they are made, one session at a time.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""".strip()


# ── Session state helpers ─────────────────────────────────────────────────────
def ss(key, default=None):
    return st.session_state.get(key, default)

def ss_set(key, val):
    st.session_state[key] = val


# ── UI Components ─────────────────────────────────────────────────────────────
def metric_card(label, value, col):
    col.markdown(f"""
    <div class="metric-card">
        <div class="val">{value}</div>
        <div class="lbl">{label}</div>
    </div>""", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("## 🕌 Mansam\n### Sales Coach")
        st.divider()

        page = st.radio(
            "Navigate",
            ["Practice Session", "My Progress", "Manager Dashboard"],
            label_visibility="collapsed",
        )
        st.divider()

        st.markdown("**Salesperson**")
        sp_name = st.text_input(
            "Your name", value=ss("sp_name", ""),
            placeholder="Enter your name…", key="sp_input",
        )
        if sp_name:
            ss_set("sp_name", sp_name)
            upsert_salesperson(sp_name.lower().replace(" ", "_"), sp_name)

        tier = ss("tier", 1)
        st.markdown(
            f'<span class="badge">Tier {tier} · {TIER_CONFIG[tier]["name"]}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="badge">⭐ {ss("total_points", 0)} pts</span>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("Phase 1 MVP · English · 3 profiles\nPowered by Gemini 2.0 Flash (free)")
    return page


# ── Page: Practice Session ────────────────────────────────────────────────────
def page_practice():
    st.markdown("# Practice Session")
    sp_name = ss("sp_name", "")
    if not sp_name:
        st.info("👈 Enter your name in the sidebar to begin.")
        return

    # ── Profile selection screen ──
    if not ss("session_active"):
        st.markdown("### Choose Your Customer Profile")
        cols = st.columns(3)
        for i, (pid, p) in enumerate(PROFILES.items()):
            with cols[i]:
                st.markdown(f"**{p['emoji']} {p['name']}**")
                st.caption(p["brief"])
                st.caption(f"Difficulty: {'★' * p['difficulty']}{'☆' * (3 - p['difficulty'])}")
                if st.button(f"Start session", key=f"pick_{pid}"):
                    ss_set("session_active", True)
                    ss_set("active_profile", pid)
                    ss_set("messages", [])
                    ss_set("debrief_done", False)
                    ss_set("last_debrief", "")
                    st.rerun()
        return

    profile = PROFILES[ss("active_profile")]
    st.markdown(f"### {profile['emoji']} Session — {profile['name']}")
    st.caption(profile["brief"])
    st.divider()

    # ── Post-session debrief view ──
    if ss("debrief_done"):
        st.markdown('<div class="debrief-box">' + ss("last_debrief", "") + '</div>',
                    unsafe_allow_html=True)
        st.markdown("")
        if st.button("🔄 Start New Session"):
            for k in ["session_active", "active_profile", "messages",
                      "debrief_done", "last_debrief"]:
                ss_set(k, None)
            st.rerun()
        return

    # ── Live chat ──
    msgs: list = ss("messages", [])

    # Auto-trigger customer opening line
    if not msgs:
        with st.spinner("Customer entering the store…"):
            try:
                opening = chat_as_customer(profile, [])
            except Exception as e:
                st.error(f"Gemini API error: {e}")
                st.stop()
        msgs = [{"role": "assistant", "content": opening}]
        ss_set("messages", msgs)

    # Render conversation
    for m in msgs:
        if m["role"] == "user":
            st.markdown(
                f'<div class="chat-user">🧑 <strong>You:</strong> {m["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="chat-ai">👤 <strong>Customer:</strong> {m["content"]}</div>',
                unsafe_allow_html=True,
            )

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Your response", key="chat_input",
            placeholder="What do you say to the customer?",
            label_visibility="collapsed",
        )
    with col_btn:
        end_clicked = st.button("End & Score", type="primary")

    # Send salesperson message
    if user_input:
        msgs.append({"role": "user", "content": user_input})
        with st.spinner("Customer is responding…"):
            reply = chat_as_customer(profile, msgs)
        msgs.append({"role": "assistant", "content": reply})
        ss_set("messages", msgs)
        st.session_state["chat_input"] = ""
        st.rerun()

    # End session and score
    if end_clicked:
        if len(msgs) < 3:
            st.warning("Have at least 2 exchanges before ending the session.")
            return

        with st.spinner("Evaluating your session — this takes a few seconds…"):
            try:
                scores = score_session(msgs)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error from Gemini scoring: {e}")
                st.error("Scoring returned unexpected output. Please try again.")
                return
            except Exception as e:
                logger.error(f"Scoring failed: {e}")
                st.error(f"Scoring failed: {e}")
                return

            perf_pts = int((scores["sale_score"] + scores["service_score"]) * 5)
            df_prev  = load_sessions(sp_name)
            prev_sale = df_prev["sale_score"].mean() if not df_prev.empty else 0.0
            prev_svc  = df_prev["svc_score"].mean()  if not df_prev.empty else 0.0
            growth_bonus = (scores["sale_score"] > prev_sale) and (prev_sale > 0)
            total_pts = POINTS_PARTICIPATION + perf_pts + (POINTS_GROWTH if growth_bonus else 0)

            debrief = build_debrief(scores, sp_name, prev_sale, prev_svc,
                                    total_pts, growth_bonus)
            save_session(sp_name, profile["id"],
                         scores["sale_score"], scores["service_score"],
                         total_pts, msgs, debrief)

            ss_set("total_points", ss("total_points", 0) + total_pts)
            ss_set("last_debrief", debrief)
            ss_set("debrief_done", True)
            st.rerun()


# ── Page: My Progress ─────────────────────────────────────────────────────────
def page_progress():
    st.markdown("# My Progress")
    sp_name = ss("sp_name", "")
    if not sp_name:
        st.info("👈 Enter your name in the sidebar.")
        return

    df = load_sessions(sp_name)
    if df.empty:
        st.info("No sessions yet. Complete your first practice session!")
        return

    c1, c2, c3, c4 = st.columns(4)
    metric_card("Sessions",     len(df),                          c1)
    metric_card("Avg Sale",     f"{df['sale_score'].mean():.1f}", c2)
    metric_card("Avg Service",  f"{df['svc_score'].mean():.1f}",  c3)
    metric_card("Total Points", int(df["points"].sum()),          c4)

    st.markdown("### Score Trends")
    df["created_at"] = pd.to_datetime(df["created_at"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["sale_score"],
                             name="Sale",    line=dict(color="#C9A84C", width=2)))
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["svc_score"],
                             name="Service", line=dict(color="#8C7A5A", width=2)))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Jost"), yaxis=dict(range=[0, 10]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Session History")
    display = df[["created_at", "profile_id", "sale_score", "svc_score", "points"]].copy()
    display.columns = ["Date", "Profile", "Sale", "Service", "Points"]
    display["Profile"] = display["Profile"].map(
        {pid: p["name"] for pid, p in PROFILES.items()}
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


# ── Page: Manager Dashboard ───────────────────────────────────────────────────
def page_dashboard():
    st.markdown("# Manager Dashboard")
    st.caption("Enterprise MIS · all salespeople · all sessions")

    all_df = load_all_sessions()
    sp_df  = load_salespeople()

    if all_df.empty:
        st.info("No session data yet.")
        return

    today = datetime.date.today().isoformat()
    today_df = all_df[all_df["created_at"].str.startswith(today)]

    c1, c2, c3, c4 = st.columns(4)
    metric_card("Sessions Today",   len(today_df),                         c1)
    metric_card("Avg Sale Score",   f"{all_df['sale_score'].mean():.1f}",  c2)
    metric_card("Avg Service Score",f"{all_df['svc_score'].mean():.1f}",   c3)
    metric_card("Salespeople",      len(sp_df),                            c4)

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Team Leaderboard")
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
        fig2 = go.Figure()
        fig2.add_trace(go.Box(y=all_df["sale_score"], name="Sale",
                              marker_color="#C9A84C", line_color="#C9A84C"))
        fig2.add_trace(go.Box(y=all_df["svc_score"],  name="Service",
                              marker_color="#8C7A5A", line_color="#8C7A5A"))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Jost"), yaxis=dict(range=[0, 10]),
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
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Jost"), xaxis_title="",
        yaxis=dict(range=[0, 10]),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📥 Export raw data"):
        csv = all_df.to_csv(index=False)
        st.download_button("Download CSV", csv, "mansam_sessions.csv", "text/csv")


# ── Main router ───────────────────────────────────────────────────────────────
def main():
    page = render_sidebar()
    if page == "Practice Session":
        page_practice()
    elif page == "My Progress":
        page_progress()
    elif page == "Manager Dashboard":
        page_dashboard()


if __name__ == "__main__":
    main()
