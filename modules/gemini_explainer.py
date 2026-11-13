"""Optional Gemini integration. Gemini only *words* answers: every number it may use is computed
deterministically by this app and passed in as a fact sheet. Without an API key the feature is off."""
from __future__ import annotations

import json
import os

import requests
import streamlit as st

SYSTEM = (
    "You are the explainer inside 'Mumbai: The Air We Build'. Answer the user's question using ONLY the FACT SHEET provided. "
    "Rules: (1) Never state a number that is not in the fact sheet. (2) If the fact sheet cannot answer, say so and say what data would be needed. "
    "(3) Never say that an urban feature causes a PM2.5 level; describe associations and say they are not proof of cause. "
    "(4) Keep PM2.5 and PM10 / total PM figures separate and name which one you mean. (5) Label scenario results as hypothetical. "
    "(6) Plain language for a general reader, under 180 words, no headings."
)


def api_key() -> str | None:
    try:
        k = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        k = None
    return k or os.environ.get("GEMINI_API_KEY")


def model() -> str:
    try:
        return st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    except Exception:
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def ask(question: str, facts: dict) -> str:
    key = api_key()
    if not key:
        raise RuntimeError("No GEMINI_API_KEY configured")
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": "FACT SHEET (JSON):\n" + json.dumps(facts, default=str) + "\n\nQUESTION: " + question}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
    }
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model()}:generateContent",
                      headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=40)
    r.raise_for_status()
    j = r.json()
    try:
        return j["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError("Gemini returned no text")
