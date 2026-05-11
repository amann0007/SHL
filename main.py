"""
SHL Assessment Recommendation Agent - FastAPI Service
POST /chat  - stateless conversational agent
GET  /health - readiness check
"""

import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from catalog import get_catalog, build_catalog_text, KEY_MAP

app = FastAPI(title="SHL Assessment Recommendation Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CATALOG = get_catalog()
CATALOG_TEXT = build_catalog_text()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[Recommendation]
    end_of_conversation: bool


SYSTEM_PROMPT = f"""You are an SHL Assessment Recommendation Agent. Your ONLY job is to help hiring managers and recruiters select the right SHL Individual Test Solutions from the official SHL catalog.

## STRICT RULES
1. You ONLY discuss SHL assessments. Refuse all off-topic questions with: "I can only help with SHL assessment selection."
2. NEVER recommend anything not in the catalog below.
3. NEVER hallucinate URLs — only use URLs from the catalog.
4. Do NOT recommend on turn 1 if the query is vague. Ask clarifying questions first.
5. You MUST clarify at minimum: role/job function, and seniority/level before recommending.
6. When you have enough context, recommend 1–10 assessments.
7. If the user refines constraints, UPDATE the shortlist accordingly.
8. When asked to compare assessments, use ONLY catalog data.
9. Honor the 8-turn conversation cap — commit to a shortlist by turn 6 at the latest.

## OUTPUT FORMAT (JSON only — no markdown fences)
You MUST respond with valid JSON in this exact schema:
{{
  "reply": "<your conversational reply to the user>",
  "recommendations": [
    {{"name": "<exact catalog name>", "url": "<exact catalog URL>", "test_type": "<single letter code>"}}
  ],
  "end_of_conversation": false
}}

- `recommendations` is [] when still gathering context or refusing.
- `recommendations` has 1–10 items when you commit to a shortlist.
- `end_of_conversation` is true ONLY when the user is satisfied and the task is complete.
- test_type codes: A=Ability & Aptitude, B=Biodata & Situational Judgment, C=Competencies, D=Development & 360, E=Assessment Exercises, K=Knowledge & Skills, P=Personality & Behavior, S=Simulations

## CATALOG (name | types | job levels | duration | url)
{CATALOG_TEXT}
"""

CATALOG_URL_SET = {item["url"] for item in CATALOG}
CATALOG_NAME_MAP = {item["name"].lower(): item for item in CATALOG}

ROLE_RULES = [
    {
        "keywords": ["data scientist", "data science", "machine learning", "ml engineer", "analytics", "analyst"],
        "message": "For a data science hire, I’d focus on data, statistics, programming, and reasoning assessments.",
        "names": [
            "Data Science (New)",
            "Automata Data Science (New)",
            "Basic Statistics (New)",
            "R Programming (New)",
            "Python (New)",
            "SHL Verify Interactive - Numerical Reasoning",
        ],
    },
    {
        "keywords": ["software engineer", "software developer", "developer", "engineer", "programming", "coding", "full stack", "backend", "frontend", "web developer"],
        "message": "For a software engineer hire, I’d focus on coding, programming concepts, and language-specific assessments.",
        "names": [
            "Automata (New)",
            "Programming Concepts",
            "Python (New)",
            "Java 8 (New)",
            "JavaScript (New)",
            "ReactJS (New)",
            "Node.js (New)",
            "SQL (New)",
        ],
    },
    {
        "keywords": ["manager", "leadership", "director", "executive", "lead", "supervisor"],
        "message": "For a manager or leadership role, I’d focus on judgment, leadership style, and personality-based assessments.",
        "names": [
            "Management Scenarios",
            "Executive Scenarios",
            "OPQ Leadership Report",
            "Enterprise Leadership Report 2.0",
            "OPQ Universal Competency Report 2.0",
            "Motivation Questionnaire MQM5",
        ],
    },
    {
        "keywords": ["sales", "account executive", "business development", "customer success", "account manager"],
        "message": "For a sales role, I’d focus on communication, motivation, and sales-fit assessments.",
        "names": [
            "Business Communication (adaptive)",
            "Interpersonal Communications",
            "Motivation Questionnaire MQM5",
            "OPQ MQ Sales Report",
            "Sales Transformation 2.0 - Individual Contributor",
        ],
    },
    {
        "keywords": ["graduate", "entry level", "entry-level", "fresher", "junior"],
        "message": "For an entry-level or graduate role, I’d focus on reasoning, communication, and basic work-style assessments.",
        "names": [
            "Graduate Scenarios",
            "Business Communication (adaptive)",
            "Dependability and Safety Instrument (DSI)",
            "SHL Verify Interactive - Numerical Reasoning",
        ],
    },
]

LEVEL_RULES = {
    "entry-level": ["entry-level", "entry level", "graduate", "junior", "fresher", "new grad", "new graduate"],
    "mid-professional": ["mid-level", "mid level", "mid", "experienced", "intermediate"],
    "manager": ["manager", "lead", "supervisor"],
    "director": ["director", "executive", "vp", "vice president"],
}

LEVEL_JOB_LEVEL_MAP = {
    "entry-level": ["entry-level", "graduate", "general population"],
    "mid-professional": ["mid-professional", "professional individual contributor"],
    "manager": ["manager", "front line manager", "supervisor"],
    "director": ["director", "executive"],
}


def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content.lower()
    return ""


def _detect_level(text: str) -> str | None:
    for level, keywords in LEVEL_RULES.items():
        if any(keyword in text for keyword in keywords):
            return level
    return None


def _detect_role_rule(text: str) -> dict | None:
    for rule in ROLE_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            return rule
    return None


def _catalog_item(name: str) -> dict | None:
    return CATALOG_NAME_MAP.get(name.lower())


def _item_matches_level(item: dict, level: str | None) -> bool:
    if not level:
        return True

    aliases = LEVEL_JOB_LEVEL_MAP.get(level, [])
    item_levels = [job_level.lower() for job_level in item.get("job_levels", [])]
    return any(alias in item_level for alias in aliases for item_level in item_levels)


def _make_recommendations(names: list[str], limit: int = 10) -> list[Recommendation]:
    recs = []
    seen = set()
    for name in names:
        item = _catalog_item(name)
        if not item or item["name"] in seen:
            continue
        seen.add(item["name"])
        recs.append(
            Recommendation(
                name=item["name"],
                url=item["url"],
                test_type=item["test_type"],
            )
        )
        if len(recs) >= limit:
            break
    return recs


def _score_catalog_item(item: dict, text: str, level: str | None) -> int:
    haystack = " ".join([
        item["name"],
        item["description"],
        " ".join(item.get("keys", [])),
        " ".join(item.get("job_levels", [])),
    ]).lower()

    score = 0
    for token in re.findall(r"[a-z0-9+.#-]+", text):
        if token and token in haystack:
            score += 1

    if level:
        normalized_levels = [job_level.lower() for job_level in item.get("job_levels", [])]
        if any(level in job_level for job_level in normalized_levels):
            score += 3

    if item.get("test_type") == "A" and any(word in text for word in ["reasoning", "numerical", "logic", "aptitude"]):
        score += 2

    return score


def _local_recommendations(text: str, level: str | None) -> list[Recommendation]:
    role_rule = _detect_role_rule(text)
    if role_rule:
        recs = _make_recommendations(role_rule["names"])
        if level:
            filtered = [rec for rec in recs if _item_matches_level(_catalog_item(rec.name) or {}, level)]
            return filtered or recs
        return recs

    scored = []
    for item in CATALOG:
        score = _score_catalog_item(item, text, level)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    recommendations = []
    for _, item in scored[:10]:
        recommendations.append(
            Recommendation(
                name=item["name"],
                url=item["url"],
                test_type=item["test_type"],
            )
        )
    return recommendations


def _build_reply(text: str, recommendations: list[Recommendation], level: str | None) -> str:
    if recommendations:
        if level:
            return "Here are the best SHL assessments for your role and level."
        return "Here are the closest SHL assessments based on your request."

    if not text:
        return "Tell me the role/job function and seniority/level, and I’ll recommend the best SHL assessments."

    if not level:
        return "I understand the role, but I still need the seniority/level to narrow this down."

    return "I need a little more detail about the role/job function to recommend the right SHL assessments."


def call_agent(messages: list[Message]) -> ChatResponse:
    text = _latest_user_text(messages)
    level = _detect_level(text)
    recommendations = _local_recommendations(text, level)
    reply = _build_reply(text, recommendations, level)
    return ChatResponse(reply=reply, recommendations=recommendations, end_of_conversation=False)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    user_turns = sum(1 for m in request.messages if m.role == "user")
    if user_turns > 8:
        return ChatResponse(
            reply="We've reached the maximum conversation length. Based on our discussion, please review the assessments shared above.",
            recommendations=[],
            end_of_conversation=True
        )

    return call_agent(request.messages)
