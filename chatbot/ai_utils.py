import os
from pathlib import Path
from typing import Optional

import requests
from django.conf import settings


OPENAI_API_KEY: Optional[str] = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = getattr(settings, "OPENAI_MODEL", None) or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def _load_taarifa_text() -> str:
    """
    Load taarifa.md from the project root (one level above BASE_DIR).
    If anything fails, return empty string so we can safely fall back.
    """
    try:
        base_dir = Path(settings.BASE_DIR)
        root = base_dir.parent
        path = root / "taarifa.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


TAARIFA_TEXT: str = _load_taarifa_text()


def _call_openai_chat(messages: list[dict]) -> Optional[str]:
    """
    Minimal wrapper around OpenAI Chat Completions API, using requests.
    Returns the assistant message content, or None on failure.
    """
    if not OPENAI_API_KEY:
        return None

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 700,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = (choice.get("message") or {}).get("content")
        if not message:
            return None
        return str(message).strip()
    except Exception:
        return None


def rewrite_info_answer(header: str, body: str, lang: str = "sw") -> str:
    """
    Rewrite taarifa / FAQ style answers so they sound more natural,
    using taarifa.md as the source of truth. If OpenAI or taarifa.md
    is not available, return the original header + body unchanged.

    We preserve the header (e.g. "1️⃣ Utangulizi wa Wilaya...") so that
    any downstream logic that checks the prefix still works.
    """
    header = header or ""
    body = body or ""

    # If no AI key or no taarifa content, just return original.
    if not OPENAI_API_KEY or not TAARIFA_TEXT or not body.strip():
        if header and body:
            return f"{header}\n\n{body}"
        return f"{header}{body}"

    # Decide language hint – for now we always prefer Kiswahili.
    target_lang = "Kiswahili" if (lang or "sw") == "sw" else "English"

    system_msg = (
        "Wewe ni msaidizi wa Halmashauri ya Wilaya ya Chemba.\n"
        "Kazi yako ni kuchukua taarifa rasmi na kuziandika upya kwa namna ya mazungumzo ya binadamu "
        "kupitia WhatsApp.\n"
        "Usibadilishe ukweli wa taarifa, usiongeze mambo ambayo hayapo kwenye taarifa rasmi.\n"
        "Tumia lugha rahisi, fupi, ya heshima, na pangilia aya vizuri."
    )

    user_msg = (
        f"Lugha lengwa: {target_lang}\n\n"
        f"Hii ni sehemu ya kichwa cha ujumbe (usiibadilishe):\n{header}\n\n"
        "Huu hapa ni mwili wa ujumbe wa zamani ambao umeandikwa moja kwa moja kwenye mfumo:\n"
        f"{body}\n\n"
        "Na hii ni taarifa rasmi ya rejea kutoka kwenye hati ya taarifa ya Wilaya (taarifa.md):\n"
        f"{TAARIFA_TEXT}\n\n"
        "Tafadhali andika upya MWILI WA UJUMBE PEKEE (usirudie kichwa) kwa mtindo wa binadamu, "
        "ukitumia lugha hiyo hiyo, na ukihakikisha taarifa zote muhimu bado zipo na zina uhalisia.\n"
        "Tumia aya chache fupi; unaweza kuacha namba / orodha pale inapofaa.\n"
        "Rudisha tu mwili mpya wa ujumbe bila kuongeza maelezo mengine."
    )

    new_body = _call_openai_chat(
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
    )

    if not new_body:
        # Fall back to original text on any failure
        if header and body:
            return f"{header}\n\n{body}"
        return f"{header}{body}"

    if header:
        return f"{header}\n\n{new_body}"
    return new_body

