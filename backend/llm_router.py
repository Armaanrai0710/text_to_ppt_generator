import json
import os
import requests
from typing import Dict, List, Optional

# NOTE:
# - We DO NOT store or log API keys here or anywhere else.
# - Keys are passed per-request from the caller and used only in-memory.

def build_structuring_prompt(text: str, guidance: Optional[str]) -> str:
    goal = guidance or "Turn this into a clear, concise presentation with a logical flow."
    return f"""
    You are a slide architect. Read the input and produce a JSON object describing a slide deck.
    The deck should reflect this guidance: {goal}

    Output JSON schema:
    {{
      "title": "Optional overall deck title string",
      "slides": [
        {{
          "title": "Slide title",
          "bullets": ["bullet 1", "bullet 2", "..."],
          "notes": "Optional speaker notes string"
        }}
      ]
    }}

    Keep bullets short. Prefer 4-6 bullets per slide. Create as many slides as needed,
    but keep a reasonable length. If headings in the text imply sections, map them to slides.
    Input starts below:
    ---
    {text}
    ---
    """

def _call_openai(api_key: str, text: str, guidance: Optional[str], model: str = "gpt-4o-mini") -> Dict:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = build_structuring_prompt(text, guidance)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that outputs STRICT JSON. Do not add commentary."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    # Attempt to parse JSON from content
    try:
        return json.loads(content)
    except Exception:
        # Fallback: try to extract JSON block
        import re
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            return json.loads(m.group(0))
        raise

def _call_anthropic(api_key: str, text: str, guidance: Optional[str], model: str = "claude-3-5-sonnet-latest") -> Dict:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    prompt = build_structuring_prompt(text, guidance)
    payload = {
        "model": model,
        "max_tokens": 4000,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    # Anthropics returns a list of content blocks
    content_blocks = resp.json().get("content", [])
    text_out = ""
    for block in content_blocks:
        if block.get("type") == "text":
            text_out += block.get("text", "")
    return json.loads(text_out)

def _call_gemini(api_key: str, text: str, guidance: Optional[str], model: str = "gemini-1.5-pro"):
    # Generative Language API (REST)
    # https://ai.google.dev/gemini-api/docs/api-overview
    import requests
    prompt = build_structuring_prompt(text, guidance)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    candidates = resp.json().get("candidates", [])
    text_out = ""
    if candidates and "content" in candidates[0]:
        parts = candidates[0]["content"].get("parts", [])
        for p in parts:
            text_out += p.get("text", "")
    return json.loads(text_out)

def _heuristic_split(text: str, guidance: Optional[str]) -> Dict:
    """
    Fallback when no API key/provider is given or API calls fail.
    Simple heuristic:
    - Split by Markdown headings if present, otherwise by double newlines.
    - Cap bullets per slide and chunk lines.
    """
    import re
    lines = text.strip().splitlines()
    # Detect markdown H1/H2 as slide boundaries
    slides = []
    current_title = None
    current_lines = []

    def flush_slide():
        nonlocal slides, current_title, current_lines
        if current_title or current_lines:
            bullets = [ln.strip("-* ").strip() for ln in current_lines if ln.strip()]
            # Limit per slide
            if len(bullets) > 8:
                bullets = bullets[:8]
            slides.append({
                "title": current_title or "Slide",
                "bullets": bullets[:8],
                "notes": ""
            })
        current_title, current_lines = None, []

    for ln in lines:
        if re.match(r"^\s*#{1,2}\s+.+", ln):
            flush_slide()
            current_title = re.sub(r"^\s*#{1,2}\s+", "", ln).strip()
        elif ln.strip():
            current_lines.append(ln.strip())

    flush_slide()
    if not slides:
        # chunk by paragraphs
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, p in enumerate(paras):
            bullets = [s.strip() for s in re.split(r"[•\-\u2022]|\n", p) if s.strip()]
            slides.append({"title": f"Section {i+1}", "bullets": bullets[:6], "notes": ""})
    deck = {"title": "", "slides": slides[:20]}
    return deck

def structure_slides(provider: str, api_key: Optional[str], text: str, guidance: Optional[str]) -> Dict:
    """
    Returns {"title": str, "slides": [{"title":..., "bullets":[...], "notes": "..."}]}
    """
    provider = (provider or "").lower().strip()
    if api_key and provider in {"openai", "anthropic", "gemini"}:
        try:
            if provider == "openai":
                return _call_openai(api_key, text, guidance)
            if provider == "anthropic":
                return _call_anthropic(api_key, text, guidance)
            if provider == "gemini":
                return _call_gemini(api_key, text, guidance)
        except Exception:
            # Fall back silently to heuristic
            pass
    # Fallback
    return _heuristic_split(text, guidance)
