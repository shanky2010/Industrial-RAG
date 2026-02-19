"""
IndustrialRAG - LLM Formatting Layer
Strict grounding: only outputs what is in the retrieved context.
"""

import os
from typing import Optional

SYSTEM_PROMPT = """You are an industrial maintenance assistant. Your ONLY job is to extract and structure information from the provided CONTEXT.

STRICT RULES:
1. Use ONLY information explicitly present in the CONTEXT.
2. If a section has no relevant info in the context, write: "Not found in manual."
3. Do NOT use general knowledge. Do NOT guess. Do NOT add anything not in the context.
4. If the context is completely unrelated to the query, respond only with: INSUFFICIENT_CONTEXT

Output format (use exactly):
PROBLEM SUMMARY:
[What the context says about this issue]

POSSIBLE CAUSES:
1. [cause from context]

STEP-BY-STEP CORRECTIVE ACTIONS:
1. [step from context]

SAFETY NOTES:
[warnings from context, or "None stated in manual."]"""


def _prompt(context: str, query: str) -> str:
    return (
        "CONTEXT (from uploaded manual/repair logs only):\n"
        "===\n"
        f"{context}\n"
        "===\n\n"
        f"Technician query: {query}\n\n"
        "Using ONLY the context above, provide the structured response."
    )


def _is_bad(text: str) -> bool:
    return not text or "INSUFFICIENT_CONTEXT" in text.upper()


def _ollama(context: str, query: str) -> Optional[str]:
    try:
        import requests
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model":   os.environ.get("OLLAMA_MODEL", "mistral"),
                "prompt":  _prompt(context, query),
                "system":  SYSTEM_PROMPT,
                "stream":  False,
                "options": {"temperature": 0.0, "num_predict": 1024},
            },
            timeout=120,
        )
        if r.status_code == 200:
            return r.json().get("response", "")
    except Exception as e:
        print(f"Ollama error: {e}")
    return None


def _openai(context: str, query: str) -> Optional[str]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": _prompt(context, query)},
            ],
            temperature=0.0,
            max_tokens=1024,
        )
        return r.choices[0].message.content
    except Exception as e:
        print(f"OpenAI error: {e}")
    return None


def _anthropic(context: str, query: str) -> Optional[str]:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _prompt(context, query)}],
        )
        return msg.content[0].text
    except Exception as e:
        print(f"Anthropic error: {e}")
    return None


def _rule_based(context: str, query: str) -> str:
    """
    No-LLM fallback.
    Scans context lines for cause/fix/warning keywords.
    Only outputs text literally present in the context — never generates filler.
    """
    lines = [
        ln.strip() for ln in context.split("\n")
        if ln.strip() and not ln.strip().startswith("[")
    ]

    cause_kw = ["cause", "caused by", "due to", "failure", "fault", "defect",
                "worn", "damaged", "failed", "broken", "loose", "blocked", "missing"]
    fix_kw   = ["replace", "check", "verify", "inspect", "clean", "adjust",
                "tighten", "reset", "test", "turn off", "turn on", "connect",
                "disconnect", "press", "ensure", "remove", "install", "lubricate", "charge"]
    warn_kw  = ["warning", "caution", "danger", "do not", "must not", "hazard",
                "electric", "shock", "fire", "risk", "never"]

    causes, fixes, warnings = [], [], []
    for line in lines:
        low = line.lower()
        if any(k in low for k in warn_kw) and len(warnings) < 3:
            warnings.append(line[:250])
        elif any(k in low for k in cause_kw) and len(causes) < 5:
            causes.append(line[:250])
        elif any(k in low for k in fix_kw) and len(fixes) < 7:
            fixes.append(line[:250])

    has_content = bool(causes or fixes)

    out  = "PROBLEM SUMMARY:\n"
    out += (
        f'Information found in the uploaded manual regarding "{query}".\n'
        if has_content else
        f'No direct match for "{query}" found in retrieved pages.\n'
    )

    out += "\nPOSSIBLE CAUSES:\n"
    if causes:
        for i, c in enumerate(causes, 1):
            out += f"{i}. {c}\n"
    else:
        out += "1. Not found in manual.\n"

    out += "\nSTEP-BY-STEP CORRECTIVE ACTIONS:\n"
    if fixes:
        for i, f in enumerate(fixes, 1):
            out += f"{i}. {f}\n"
    else:
        out += "1. Not found in manual. Refer to the referenced pages directly.\n"

    out += "\nSAFETY NOTES:\n"
    if warnings:
        for w in warnings:
            out += f"- {w}\n"
    else:
        out += "None stated in manual.\n"

    return out


def generate_formatted_response(context: str, query: str, machine: str) -> str:
    """
    Main entry point.
    Priority: Ollama → OpenAI → Anthropic → rule-based fallback.
    All paths are strictly grounded — no hallucination.
    """
    if not context.strip():
        return (
            "PROBLEM SUMMARY:\n"
            f'No relevant content retrieved from the manual for "{query}" on {machine}.\n\n'
            "POSSIBLE CAUSES:\n"
            "1. Not found in manual.\n\n"
            "STEP-BY-STEP CORRECTIVE ACTIONS:\n"
            "1. Verify the correct manual has been uploaded in the Admin panel.\n"
            "2. Ensure the machine name matches exactly what was used during upload.\n"
            "3. Try rephrasing using terms from the manual.\n\n"
            "SAFETY NOTES:\n"
            "Do not attempt repairs without the official manual."
        )

    result = None

    if os.environ.get("USE_OLLAMA", "true").lower() == "true":
        result = _ollama(context, query)
        if _is_bad(result):
            result = None

    if not result and os.environ.get("OPENAI_API_KEY"):
        result = _openai(context, query)
        if _is_bad(result):
            result = None

    if not result and os.environ.get("ANTHROPIC_API_KEY"):
        result = _anthropic(context, query)
        if _is_bad(result):
            result = None

    if not result:
        result = _rule_based(context, query)

    return result
