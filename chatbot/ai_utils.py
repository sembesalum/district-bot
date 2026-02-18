import os
from pathlib import Path
from typing import Optional, Tuple

import requests
from django.conf import settings


OPENAI_API_KEY: Optional[str] = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = getattr(settings, "OPENAI_MODEL", None) or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Sentinel: when the model says the document has no answer
NO_ANSWER_MARKER = "NO_ANSWER"


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

    # If no body at all, just return header (nothing useful to rewrite).
    if not body.strip():
        return header

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
        # If the AI call fails, return a single, friendly fallback message
        # instead of dumping the original long technical text.
        if (lang or "sw") == "en":
            fallback_body = (
                "Sorry, detailed information is temporarily unavailable. "
                "Please try again later or contact the district office for more details."
            )
        else:
            fallback_body = (
                "Samahani, taarifa kamili haipatikani kwa sasa. "
                "Tafadhali jaribu tena baadaye au wasiliana na ofisi ya Wilaya ya Chemba "
                "kwa maelezo zaidi."
            )
        if header:
            return f"{header}\n\n{fallback_body}"
        return fallback_body

    if header:
        return f"{header}\n\n{new_body}"
    return new_body


def answer_freeform_question(user_message: str, lang: str = "sw") -> Tuple[Optional[str], bool]:
    """
    Check if the user's free-form question can be answered from taarifa.md.
    Returns (answer_text, answered).
    - If the document has an answer: (answer_text, True). answer_text is in Kiswahili.
    - If no answer or API/taarifa missing: (None, False). Caller should show no-answer prompt.
    """
    user_message = (user_message or "").strip()
    if not user_message:
        return None, False
    if not OPENAI_API_KEY or not TAARIFA_TEXT:
        return None, False

    target_lang = "Kiswahili" if (lang or "sw") == "sw" else "English"
    system_msg = (
        "Wewe ni msaidizi wa Halmashauri ya Wilaya ya Chemba. Unapewa hati ya taarifa ya Wilaya (taarifa.md). "
        "Kazi yako: kama swali la mtumiaji linajibiwa kwa taarifa iliyomo kwenye hati, jibu kwa lugha ya Kiswahili, "
        "kwa ufupi na kwa maneno ya binadamu. Kama hati HAINA taarifa inayojibu swali hilo, jibu kwa neno moja tu: NO_ANSWER. "
        "Usiongeze mambo yasiyomo kwenye hati."
    )
    user_msg = (
        f"Hati ya taarifa (taarifa.md):\n\n{TAARIFA_TEXT}\n\n"
        f"Swali la mtumiaji: {user_message}\n\n"
        f"Jibu kwa {target_lang} ikiwa jibu liko kwenye hati; vinginevyo andika NO_ANSWER tu."
    )
    response = _call_openai_chat(
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
    )
    if not response:
        return None, False
    response_clean = response.strip()
    if response_clean.upper() == NO_ANSWER_MARKER or NO_ANSWER_MARKER in response_clean.upper():
        return None, False
    return response_clean, True

