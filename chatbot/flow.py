"""
District Citizen Services – WhatsApp bot conversation flow.
Single database stores session only; all responses are static/simple.
"""
import re
import random
import string
from datetime import datetime

# ---- States ----
WELCOME = "welcome"
MAIN_MENU = "main_menu"
LANGUAGE_CHOICE = "language_choice"
# Check status
CHECK_DEPT = "check_dept"
CHECK_ID_TYPE = "check_id_type"
CHECK_ID_VALUE = "check_id_value"
CHECK_RESULT_OPTIONS = "check_result_options"
# Submit question/complaint
SUBMIT_DEPT = "submit_dept"
SUBMIT_MESSAGE = "submit_message"
SUBMIT_CONFIRMED_OPTIONS = "submit_confirmed_options"
TRACK_TICKET = "track_ticket"
# Department info
DEPT_INFO_CHOICE = "dept_info_choice"
DEPT_INFO_SHOWN = "dept_info_shown"

# ---- Department keys (same for all flows) ----
DEPARTMENTS = [
    ("ardhi", "Ardhi (Land)", "🏡"),
    ("electricity", "Electricity", "⚡"),
    ("health", "Health", "🏥"),
    ("maji", "Maji (Water)", "💧"),
    ("business", "Business & Trade", "📋"),
    ("other", "Other", "📌"),
]

DEPT_KEYS = [d[0] for d in DEPARTMENTS]


def _dept_list(with_other=True):
    items = DEPARTMENTS if with_other else DEPARTMENTS[:-1]
    return "\n".join(f"{i}️⃣ {name} {icon}" for i, (_, name, icon) in enumerate(items, 1))


def _t(lang, en, sw):
    """Return English or Kiswahili text by lang ('en' or 'sw')."""
    return sw if (lang or "en") == "sw" else en


def _invalid_option(lang="en"):
    return _t(
        lang,
        "Sorry, I didn't understand that.\nPlease reply with a valid option number.",
        "Samahani, sikuweza kuelewa.\nTafadhali jibu kwa nambari sahihi.",
    )


def _no_record_found(lang="en"):
    return _t(
        lang,
        "No record found with the provided details.\n\n1️⃣ Try again\n2️⃣ Contact support",
        "Hakuna rekodi iliyopatikana.\n\n1️⃣ Jaribu tena\n2️⃣ Wasiliana na msaada",
    )


# ---- Department info (static) ----
DEPT_INFO = {
    "ardhi": """Ardhi Department Services:
- Land ownership verification
- Plot allocation
- Title deed processing

Office Hours:
Monday to Friday
8:00 AM – 3:30 PM""",
    "electricity": """Electricity Department Services:
- New connection requests
- Meter reading and billing
- Fault reporting

Office Hours:
Monday to Friday
8:00 AM – 3:30 PM""",
    "health": """Health Department Services:
- Health certificates
- Clinic referrals
- Public health information

Office Hours:
Monday to Friday
8:00 AM – 3:30 PM""",
    "maji": """Maji (Water) Department Services:
- Water connection requests
- Billing and payments
- Supply issues

Office Hours:
Monday to Friday
8:00 AM – 3:30 PM""",
    "business": """Business & Trade Department Services:
- Business registration
- Trade licenses
- Market information

Office Hours:
Monday to Friday
8:00 AM – 3:30 PM""",
    "other": """For other services, please visit the district office or contact the main reception.""",
}

# ---- Department info Kiswahili ----
DEPT_INFO_SW = {
    "ardhi": """Huduma za Idara ya Ardhi:
- Uthibitishaji wa umiliki wa ardhi
- Ugawaji wa viwanja
- Usindikaji wa hati miliki

Saa za Ofisi:
Jumatatu hadi Ijumaa
8:00 asubuhi – 3:30 alasiri""",
    "electricity": """Huduma za Umeme:
- Maombi ya muunganisho mpya
- Kusoma mita na bili
- Ripoti ya hitilafu

Saa za Ofisi:
Jumatatu hadi Ijumaa
8:00 asubuhi – 3:30 alasiri""",
    "health": """Huduma za Afya:
- Vibali vya afya
- Rufaa za kliniki
- Taarifa za afya ya umma

Saa za Ofisi:
Jumatatu hadi Ijumaa
8:00 asubuhi – 3:30 alasiri""",
    "maji": """Huduma za Maji:
- Maombi ya muunganisho wa maji
- Bili na malipo
- Masuala ya usambazaji

Saa za Ofisi:
Jumatatu hadi Ijumaa
8:00 asubuhi – 3:30 alasiri""",
    "business": """Huduma za Biashara na Soko:
- Usajili wa biashara
- Leseni za biashara
- Taarifa za soko

Saa za Ofisi:
Jumatatu hadi Ijumaa
8:00 asubuhi – 3:30 alasiri""",
    "other": """Kwa huduma zingine, tafadhali tembelea ofisi ya wilaya au wasiliana na mapokezi.""",
}


def _get_dept_by_number(num_str, with_other=True):
    items = DEPARTMENTS if with_other else DEPARTMENTS[:-1]
    try:
        n = int(num_str.strip())
        if 1 <= n <= len(items):
            return items[n - 1][0]
    except (ValueError, TypeError):
        pass
    return None


def _generate_ticket_id():
    return "DCT-" + "".join(random.choices(string.digits, k=5))


def _validate_ref_number(text):
    """Accept alphanumeric reference, e.g. REF-12345 or similar."""
    return bool(re.match(r"^[A-Za-z0-9\-/]+$", (text or "").strip())) and len((text or "").strip()) >= 3


def _validate_nida(text):
    """NIDA: assume digits, typical length."""
    s = (text or "").strip()
    return s.isdigit() and 8 <= len(s) <= 20


def _validate_phone(text):
    """Phone: digits, optional + at start."""
    s = (text or "").strip().lstrip("+")
    return s.isdigit() and 9 <= len(s) <= 15


def get_main_menu(lang="en"):
    """Main menu text in English or Kiswahili (lang 'en' or 'sw')."""
    if lang == "sw":
        return (
            "Karibu! 👋\n"
            "Huu ni Msaidizi wa Huduma za Raia wa Wilaya.\n\n"
            "Naweza kukusaidia:\n"
            "1️⃣ Angalia hali ya maombi\n"
            "2️⃣ Wasilisha swali au malalamiko\n"
            "3️⃣ Pata taarifa za idara\n"
            "4️⃣ Badilisha lugha\n\n"
            "Tafadhali jibu kwa nambari kuendelea."
        )
    return (
        "Karibu! 👋\n"
        "This is the District Citizen Services Assistant.\n\n"
        "I can help you:\n"
        "1️⃣ Check application status\n"
        "2️⃣ Submit a question or complaint\n"
        "3️⃣ Get department information\n"
        "4️⃣ Change language\n\n"
        "Please reply with a number to continue."
    )


def get_welcome_message(lang="en"):
    """Welcome message (main menu + reset hint). Default English."""
    hint_en = "\n(Reply # to reset / start over)"
    hint_sw = "\n(Jibu # kuanza upya)"
    hint = hint_sw if lang == "sw" else hint_en
    return get_main_menu(lang) + hint


def process_message(session_state, session_context, session_language, user_message):
    """
    Process one user message. No DB for applications/complaints; session only.
    Returns: (next_state, context_update_dict, reply_text)
    """
    state = session_state or WELCOME
    ctx = dict(session_context or {})
    msg = (user_message or "").strip()
    reply = ""
    next_state = state

    # ----- # = reset session (default key) -----
    if msg == "#":
        next_state = MAIN_MENU
        ctx = {}
        reply = get_welcome_message(session_language or "en")
        return next_state, ctx, reply

    # ----- Welcome / first message -> main menu (default English) -----
    if state == WELCOME:
        next_state = MAIN_MENU
        reply = get_welcome_message("en")
        return next_state, ctx, reply

    # ----- Language choice (option 4 from main menu) -----
    if state == LANGUAGE_CHOICE:
        lang_prompt_en = "Please choose language:\n1️⃣ Kiswahili\n2️⃣ English"
        lang_prompt_sw = "Chagua lugha:\n1️⃣ Kiswahili\n2️⃣ English"
        lang_prompt = lang_prompt_sw if session_language == "sw" else lang_prompt_en
        if msg == "1":
            ctx["language"] = "sw"
            next_state = MAIN_MENU
            reply = get_welcome_message("sw")
        elif msg == "2":
            ctx["language"] = "en"
            next_state = MAIN_MENU
            reply = get_welcome_message("en")
        else:
            reply = lang_prompt
        return next_state, ctx, reply

    # ----- Main menu -----
    if state == MAIN_MENU:
        lang = session_language or "en"
        select_dept = _t(lang,
            "Please select the department:\n1️⃣ Ardhi (Land)\n2️⃣ Electricity\n3️⃣ Health\n4️⃣ Maji (Water)\n5️⃣ Business & Trade\n6️⃣ Other",
            "Chagua idara:\n1️⃣ Ardhi (Ardhi)\n2️⃣ Umeme\n3️⃣ Afya\n4️⃣ Maji\n5️⃣ Biashara na Soko\n6️⃣ Nyingine")
        select_dept_issue = _t(lang,
            "Please select the department your issue relates to:\n1️⃣ Ardhi\n2️⃣ Electricity\n3️⃣ Health\n4️⃣ Maji\n5️⃣ Business & Trade",
            "Chagua idara inayohusika na tatizo lako:\n1️⃣ Ardhi\n2️⃣ Umeme\n3️⃣ Afya\n4️⃣ Maji\n5️⃣ Biashara na Soko")
        select_dept_info = _t(lang,
            "Select a department to get information:\n1️⃣ Ardhi\n2️⃣ Electricity\n3️⃣ Health\n4️⃣ Maji\n5️⃣ Business & Trade",
            "Chagua idara kupata taarifa:\n1️⃣ Ardhi\n2️⃣ Umeme\n3️⃣ Afya\n4️⃣ Maji\n5️⃣ Biashara na Soko")
        if msg == "1":
            next_state = CHECK_DEPT
            reply = select_dept
        elif msg == "2":
            next_state = SUBMIT_DEPT
            reply = select_dept_issue
        elif msg == "3":
            next_state = DEPT_INFO_CHOICE
            reply = select_dept_info
        elif msg == "4":
            next_state = LANGUAGE_CHOICE
            reply = _t(lang, "Please choose language:\n1️⃣ Kiswahili\n2️⃣ English", "Chagua lugha:\n1️⃣ Kiswahili\n2️⃣ English")
        else:
            reply = _invalid_option(lang)
        return next_state, ctx, reply

    # ----- Check status: department -> ID type -> ID value -----
    if state == CHECK_DEPT:
        lang = session_language or "en"
        dept = _get_dept_by_number(msg, with_other=True)
        if dept:
            ctx["check_dept"] = dept
            dept_label = next((d[1] for d in DEPARTMENTS if d[0] == dept), dept)
            next_state = CHECK_ID_TYPE
            how_check = _t(lang,
                f"You selected {dept_label} 🏡\n\nHow would you like to check your status?\n1️⃣ Application Reference Number\n2️⃣ National ID (NIDA)\n3️⃣ Phone Number",
                f"Umechagua {dept_label} 🏡\n\nUngependa kuangalia hali yako kwa njia gani?\n1️⃣ Nambari ya Kumbukumbu ya Maombi\n2️⃣ Kitambulisho cha Taifa (NIDA)\n3️⃣ Nambari ya Simu")
            reply = how_check
        else:
            reply = _invalid_option(lang)
        return next_state, ctx, reply

    if state == CHECK_ID_TYPE:
        lang = session_language or "en"
        enter_ref = _t(lang, "Please enter your Application Reference Number:", "Tafadhali ingiza Nambari yako ya Kumbukumbu ya Maombi:")
        enter_nida = _t(lang, "Please enter your National ID (NIDA):", "Tafadhali ingiza Kitambulisho chako cha Taifa (NIDA):")
        enter_phone = _t(lang, "Please enter your Phone Number:", "Tafadhali ingiza Nambari yako ya Simu:")
        if msg in ("1", "2", "3"):
            ctx["check_id_type"] = msg
            next_state = CHECK_ID_VALUE
            if msg == "1":
                reply = enter_ref
            elif msg == "2":
                reply = enter_nida
            else:
                reply = enter_phone
        else:
            reply = _invalid_option(lang)
        return next_state, ctx, reply

    if state == CHECK_ID_VALUE:
        lang = session_language or "en"
        id_type = ctx.get("check_id_type", "1")
        valid = False
        if id_type == "1":
            valid = _validate_ref_number(msg)
        elif id_type == "2":
            valid = _validate_nida(msg)
        else:
            valid = _validate_phone(msg)

        if not valid:
            reply = _invalid_option(lang)
            return next_state, ctx, reply

        # No real DB (session only): static demo success for REF-12345, otherwise "No record found".
        next_state = CHECK_RESULT_OPTIONS
        ctx["last_check_identifier"] = msg
        dept = ctx.get("check_dept", "ardhi")
        dept_label = next((d[1] for d in DEPARTMENTS if d[0] == dept), dept)
        if msg.strip().upper() in ("REF-12345", "DEMO"):
            reply = _t(lang,
                f"{dept_label} – Application Status\n\nApplication Status: IN REVIEW\nStage: Survey Verification\nLast Update: 12 Jan 2026\n\n1️⃣ Check another application\n2️⃣ Contact officer\n3️⃣ Main menu",
                f"{dept_label} – Hali ya Maombi\n\nHali: Inakaguliwa\nHatua: Uthibitishaji wa Uchunguzi\nSasisho la Mwisho: 12 Jan 2026\n\n1️⃣ Angalia maombi mengine\n2️⃣ Wasiliana na afisa\n3️⃣ Menyu kuu")
        else:
            reply = _no_record_found(lang)
        return next_state, ctx, reply

    if state == CHECK_RESULT_OPTIONS:
        lang = session_language or "en"
        select_dept = _t(lang,
            "Please select the department:\n1️⃣ Ardhi (Land)\n2️⃣ Electricity\n3️⃣ Health\n4️⃣ Maji (Water)\n5️⃣ Business & Trade\n6️⃣ Other",
            "Chagua idara:\n1️⃣ Ardhi (Ardhi)\n2️⃣ Umeme\n3️⃣ Afya\n4️⃣ Maji\n5️⃣ Biashara na Soko\n6️⃣ Nyingine")
        contact_support = _t(lang,
            "You can contact support at the district office.\n\n",
            "Unaweza wasiliana na msaada ofisi ya wilaya.\n\n")
        try_again = _t(lang, "1️⃣ Try again\n2️⃣ Contact support", "1️⃣ Jaribu tena\n2️⃣ Wasiliana na msaada")
        if msg == "1":
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            next_state = CHECK_DEPT
            reply = select_dept
        elif msg == "2":
            next_state = MAIN_MENU
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            reply = contact_support + get_main_menu(lang)
        elif msg == "3":
            next_state = MAIN_MENU
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            reply = get_main_menu(lang)
        else:
            reply = try_again
        return next_state, ctx, reply

    # ----- Submit question/complaint -----
    if state == SUBMIT_DEPT:
        lang = session_language or "en"
        dept = _get_dept_by_number(msg, with_other=False)
        if dept:
            ctx["submit_dept"] = dept
            next_state = SUBMIT_MESSAGE
            reply = _t(lang, "Please type your question or complaint below.", "Tafadhali andika swali au malalamiko yako hapa chini.")
        else:
            reply = _invalid_option(lang)
        return next_state, ctx, reply

    if state == SUBMIT_MESSAGE:
        lang = session_language or "en"
        if not msg or len(msg) < 3:
            reply = _t(lang, "Please type your question or complaint (at least a few words).", "Tafadhali andika swali au malalamiko (angalau maneno machache).")
            return next_state, ctx, reply
        ticket_id = _generate_ticket_id()
        ctx["ticket_id"] = ticket_id
        ctx["ticket_message"] = msg
        ctx["ticket_timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        ctx["ticket_dept"] = ctx.get("submit_dept", "other")
        next_state = SUBMIT_CONFIRMED_OPTIONS
        received = _t(lang, "Your message has been received.\n", "Ujumbe wako umepokelewa.\n")
        track_prompt = _t(lang, f"Ticket ID: {ticket_id}\n\n1️⃣ Main menu\n2️⃣ Track my ticket", f"Kitambulisho: {ticket_id}\n\n1️⃣ Menyu kuu\n2️⃣ Fuatilia tiketi yangu")
        reply = received + track_prompt
        return next_state, ctx, reply

    if state == SUBMIT_CONFIRMED_OPTIONS:
        lang = session_language or "en"
        main_menu_only = _t(lang, "1️⃣ Main menu\n2️⃣ Track my ticket", "1️⃣ Menyu kuu\n2️⃣ Fuatilia tiketi yangu")
        main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
        if msg == "1":
            next_state = MAIN_MENU
            reply = get_main_menu(lang)
        elif msg == "2":
            next_state = TRACK_TICKET
            tid = ctx.get("ticket_id", "N/A")
            tmsg = ctx.get("ticket_message", "")[:80]
            ttime = ctx.get("ticket_timestamp", "")
            ticket_label = _t(lang, "Ticket ID", "Kitambulisho")
            msg_label = _t(lang, "Message", "Ujumbe")
            recv_label = _t(lang, "Received", "Ilipokelewa")
            reply = f"{ticket_label}: {tid}\n{msg_label}: {tmsg}...\n{recv_label}: {ttime}\n\n{main_menu_opt}"
        else:
            reply = main_menu_only
        return next_state, ctx, reply

    if state == TRACK_TICKET:
        lang = session_language or "en"
        main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
        if msg == "1":
            next_state = MAIN_MENU
            reply = get_main_menu(lang)
        else:
            reply = main_menu_opt
        return next_state, ctx, reply

    # ----- Department info -----
    if state == DEPT_INFO_CHOICE:
        lang = session_language or "en"
        dept = _get_dept_by_number(msg, with_other=False)
        if dept:
            ctx["dept_info_shown"] = dept
            next_state = DEPT_INFO_SHOWN
            if lang == "sw":
                info = DEPT_INFO_SW.get(dept, DEPT_INFO_SW["other"])
            else:
                info = DEPT_INFO.get(dept, DEPT_INFO["other"])
            dept_label = next((d[1] for d in DEPARTMENTS if d[0] == dept), dept)
            main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
            reply = f"{dept_label}\n\n{info}\n\n{main_menu_opt}"
        else:
            reply = _invalid_option(lang)
        return next_state, ctx, reply

    if state == DEPT_INFO_SHOWN:
        lang = session_language or "en"
        main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
        if msg == "1":
            next_state = MAIN_MENU
            reply = get_main_menu(lang)
        else:
            reply = main_menu_opt
        return next_state, ctx, reply

    # Fallback: reset to main menu
    next_state = MAIN_MENU
    reply = get_main_menu(session_language or "en")
    return next_state, ctx, reply
