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


def _invalid_option():
    return (
        "Sorry, I didn't understand that.\n"
        "Please reply with a valid option number."
    )


def _no_record_found():
    return (
        "No record found with the provided details.\n\n"
        "1️⃣ Try again\n"
        "2️⃣ Contact support"
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


def get_welcome_message():
    """Welcome message sent when user texts the bot for the first time."""
    return (
        "Karibu! 👋\n"
        "This is the District Citizen Services Assistant.\n\n"
        "I can help you:\n"
        "1️⃣ Check application status\n"
        "2️⃣ Submit a question or complaint\n"
        "3️⃣ Get department information\n\n"
        "Please reply with a number to continue.\n"
        "(Reply # to reset / start over)"
    )


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
        reply = get_welcome_message()
        return next_state, ctx, reply

    # ----- Welcome / first message -> main menu -----
    if state == WELCOME:
        next_state = MAIN_MENU
        reply = get_welcome_message()
        return next_state, ctx, reply

    # ----- Optional: language choice (if we add trigger later) -----
    if state == LANGUAGE_CHOICE:
        if msg == "1":
            ctx["language"] = "sw"
            next_state = MAIN_MENU
            reply = (
                "Karibu! 👋\n"
                "Huu ni Msaidizi wa Huduma za Raia wa Wilaya.\n\n"
                "Naweza kukusaidia:\n"
                "1️⃣ Angalia hali ya maombi\n"
                "2️⃣ Wasilisha swali au malalamiko\n"
                "3️⃣ Pata taarifa za idara\n\n"
                "Tafadhali jibu kwa nambari kuendelea."
            )
        elif msg == "2":
            ctx["language"] = "en"
            next_state = MAIN_MENU
            reply = (
                "Karibu! 👋\n"
                "This is the District Citizen Services Assistant.\n\n"
                "I can help you:\n"
                "1️⃣ Check application status\n"
                "2️⃣ Submit a question or complaint\n"
                "3️⃣ Get department information\n\n"
                "Please reply with a number to continue."
            )
        else:
            reply = (
                "Please choose language:\n"
                "1️⃣ Kiswahili\n"
                "2️⃣ English"
            )
        return next_state, ctx, reply

    # ----- Main menu -----
    if state == MAIN_MENU:
        if msg == "1":
            next_state = CHECK_DEPT
            reply = (
                "Please select the department:\n"
                "1️⃣ Ardhi (Land)\n"
                "2️⃣ Electricity\n"
                "3️⃣ Health\n"
                "4️⃣ Maji (Water)\n"
                "5️⃣ Business & Trade\n"
                "6️⃣ Other"
            )
        elif msg == "2":
            next_state = SUBMIT_DEPT
            reply = (
                "Please select the department your issue relates to:\n"
                "1️⃣ Ardhi\n"
                "2️⃣ Electricity\n"
                "3️⃣ Health\n"
                "4️⃣ Maji\n"
                "5️⃣ Business & Trade"
            )
        elif msg == "3":
            next_state = DEPT_INFO_CHOICE
            reply = (
                "Select a department to get information:\n"
                "1️⃣ Ardhi\n"
                "2️⃣ Electricity\n"
                "3️⃣ Health\n"
                "4️⃣ Maji\n"
                "5️⃣ Business & Trade"
            )
        else:
            reply = _invalid_option()
        return next_state, ctx, reply

    # ----- Check status: department -> ID type -> ID value -----
    if state == CHECK_DEPT:
        dept = _get_dept_by_number(msg, with_other=True)
        if dept:
            ctx["check_dept"] = dept
            dept_label = next((d[1] for d in DEPARTMENTS if d[0] == dept), dept)
            next_state = CHECK_ID_TYPE
            reply = (
                f"You selected {dept_label} 🏡\n\n"
                "How would you like to check your status?\n"
                "1️⃣ Application Reference Number\n"
                "2️⃣ National ID (NIDA)\n"
                "3️⃣ Phone Number"
            )
        else:
            reply = _invalid_option()
        return next_state, ctx, reply

    if state == CHECK_ID_TYPE:
        if msg in ("1", "2", "3"):
            ctx["check_id_type"] = msg
            next_state = CHECK_ID_VALUE
            if msg == "1":
                reply = "Please enter your Application Reference Number:"
            elif msg == "2":
                reply = "Please enter your National ID (NIDA):"
            else:
                reply = "Please enter your Phone Number:"
        else:
            reply = _invalid_option()
        return next_state, ctx, reply

    if state == CHECK_ID_VALUE:
        id_type = ctx.get("check_id_type", "1")
        valid = False
        if id_type == "1":
            valid = _validate_ref_number(msg)
        elif id_type == "2":
            valid = _validate_nida(msg)
        else:
            valid = _validate_phone(msg)

        if not valid:
            reply = _invalid_option()
            return next_state, ctx, reply

        # No real DB (session only): static demo success for REF-12345, otherwise "No record found".
        next_state = CHECK_RESULT_OPTIONS
        ctx["last_check_identifier"] = msg
        dept = ctx.get("check_dept", "ardhi")
        dept_label = next((d[1] for d in DEPARTMENTS if d[0] == dept), dept)
        if msg.strip().upper() in ("REF-12345", "DEMO"):
            reply = (
                f"{dept_label} – Application Status\n\n"
                "Application Status: IN REVIEW\n"
                "Stage: Survey Verification\n"
                "Last Update: 12 Jan 2026\n\n"
                "1️⃣ Check another application\n"
                "2️⃣ Contact officer\n"
                "3️⃣ Main menu"
            )
        else:
            reply = _no_record_found()
        return next_state, ctx, reply

    if state == CHECK_RESULT_OPTIONS:
        main_menu_text = (
            "1️⃣ Check application status\n"
            "2️⃣ Submit a question or complaint\n"
            "3️⃣ Get department information\n\n"
            "Please reply with a number to continue."
        )
        if msg == "1":
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            next_state = CHECK_DEPT
            reply = (
                "Please select the department:\n"
                "1️⃣ Ardhi (Land)\n"
                "2️⃣ Electricity\n"
                "3️⃣ Health\n"
                "4️⃣ Maji (Water)\n"
                "5️⃣ Business & Trade\n"
                "6️⃣ Other"
            )
        elif msg == "2":
            next_state = MAIN_MENU
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            reply = (
                "You can contact support at the district office.\n\n"
                + main_menu_text
            )
        elif msg == "3":
            next_state = MAIN_MENU
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            reply = main_menu_text
        else:
            reply = (
                "1️⃣ Try again\n"
                "2️⃣ Contact support"
            )
        return next_state, ctx, reply

    # ----- Submit question/complaint -----
    if state == SUBMIT_DEPT:
        dept = _get_dept_by_number(msg, with_other=False)
        if dept:
            ctx["submit_dept"] = dept
            next_state = SUBMIT_MESSAGE
            reply = "Please type your question or complaint below."
        else:
            reply = _invalid_option()
        return next_state, ctx, reply

    if state == SUBMIT_MESSAGE:
        if not msg or len(msg) < 3:
            reply = "Please type your question or complaint (at least a few words)."
            return next_state, ctx, reply
        ticket_id = _generate_ticket_id()
        ctx["ticket_id"] = ticket_id
        ctx["ticket_message"] = msg
        ctx["ticket_timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        ctx["ticket_dept"] = ctx.get("submit_dept", "other")
        next_state = SUBMIT_CONFIRMED_OPTIONS
        reply = (
            "Your message has been received.\n"
            f"Ticket ID: {ticket_id}\n\n"
            "1️⃣ Main menu\n"
            "2️⃣ Track my ticket"
        )
        return next_state, ctx, reply

    if state == SUBMIT_CONFIRMED_OPTIONS:
        if msg == "1":
            next_state = MAIN_MENU
            reply = (
                "1️⃣ Check application status\n"
                "2️⃣ Submit a question or complaint\n"
                "3️⃣ Get department information\n\n"
                "Please reply with a number to continue."
            )
        elif msg == "2":
            next_state = TRACK_TICKET
            tid = ctx.get("ticket_id", "N/A")
            tmsg = ctx.get("ticket_message", "")[:80]
            ttime = ctx.get("ticket_timestamp", "")
            reply = (
                f"Ticket ID: {tid}\n"
                f"Message: {tmsg}...\n"
                f"Received: {ttime}\n\n"
                "1️⃣ Main menu"
            )
        else:
            reply = "1️⃣ Main menu\n2️⃣ Track my ticket"
        return next_state, ctx, reply

    if state == TRACK_TICKET:
        if msg == "1":
            next_state = MAIN_MENU
            reply = (
                "1️⃣ Check application status\n"
                "2️⃣ Submit a question or complaint\n"
                "3️⃣ Get department information\n\n"
                "Please reply with a number to continue."
            )
        else:
            reply = "1️⃣ Main menu"
        return next_state, ctx, reply

    # ----- Department info -----
    if state == DEPT_INFO_CHOICE:
        dept = _get_dept_by_number(msg, with_other=False)
        if dept:
            ctx["dept_info_shown"] = dept
            next_state = DEPT_INFO_SHOWN
            info = DEPT_INFO.get(dept, DEPT_INFO["other"])
            dept_label = next((d[1] for d in DEPARTMENTS if d[0] == dept), dept)
            reply = f"{dept_label}\n\n{info}\n\n1️⃣ Main menu"
        else:
            reply = _invalid_option()
        return next_state, ctx, reply

    if state == DEPT_INFO_SHOWN:
        if msg == "1":
            next_state = MAIN_MENU
            reply = (
                "1️⃣ Check application status\n"
                "2️⃣ Submit a question or complaint\n"
                "3️⃣ Get department information\n\n"
                "Please reply with a number to continue."
            )
        else:
            reply = "1️⃣ Main menu"
        return next_state, ctx, reply

    # Fallback: reset to main menu
    next_state = MAIN_MENU
    reply = (
        "1️⃣ Check application status\n"
        "2️⃣ Submit a question or complaint\n"
        "3️⃣ Get department information\n\n"
        "Please reply with a number to continue."
    )
    return next_state, ctx, reply
