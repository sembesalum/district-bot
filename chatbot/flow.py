"""
District Citizen Services – WhatsApp bot conversation flow.
Single database stores session only; all responses are static/simple.
"""
import re
import random
import string
from datetime import datetime, timedelta
from django.conf import settings

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
    """Return English or Kiswahili text by lang ('en' or 'sw'). Default Kiswahili."""
    return en if (lang or "sw") == "en" else sw


def _invalid_option(lang="sw"):
    return _t(
        lang,
        "Sorry, I didn't understand that.\nPlease reply with a valid option number.",
        "Samahani, sikuweza kuelewa.\nTafadhali jibu kwa nambari sahihi.",
    )


def _no_record_found(lang="sw"):
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


def _ticket_status_message(ctx, lang="sw"):
    """
    Build a status message for the last submitted complaint/ticket based on
    the stored context (ticket_id, ticket_message, ticket_timestamp).
    Includes a 30-minute SLA style explanation and support contact if available.
    """
    ticket_id = ctx.get("ticket_id")
    if not ticket_id:
        # No ticket in this session yet
        return _t(
            lang,
            "You don't have a recent complaint recorded in this chat.\nPlease submit a new complaint from the main menu option 7.",
            "Huna malalamiko ya hivi karibuni yaliyoandikwa kwenye mazungumzo haya.\nTafadhali wasilisha malalamiko mapya kupitia chaguo la 7 kwenye menyu kuu.",
        )

    ticket_id = ctx.get("ticket_id", "N/A")
    ticket_message = ctx.get("ticket_message", "")[:80]
    ticket_timestamp = ctx.get("ticket_timestamp", "")
    ticket_label = _t(lang, "Ticket ID", "Kitambulisho")
    msg_label = _t(lang, "Message", "Ujumbe")
    recv_label = _t(lang, "Received", "Ilipokelewa")

    base = f"{ticket_label}: {ticket_id}\n{msg_label}: {ticket_message}...\n{recv_label}: {ticket_timestamp}"

    extra = ""
    try:
        if ticket_timestamp:
            submitted = datetime.strptime(ticket_timestamp, "%Y-%m-%d %H:%M")
            now = datetime.utcnow()
            diff_minutes = max(0, (now - submitted).total_seconds() / 60.0)
            answer_time = submitted + timedelta(minutes=30)
            answer_time_str = answer_time.strftime("%H:%M")
            if diff_minutes < 30:
                # Under 30 minutes – remind expected answer window
                extra = _t(
                    lang,
                    f"\n\nYour complaint was received at {ticket_timestamp}.\nYou will receive an answer by {answer_time_str} (within 30 minutes).",
                    f"\n\nMalalamiko yako yalipokelewa saa {ticket_timestamp}.\nUtapokea majibu kabla ya saa {answer_time_str} (ndani ya dakika 30).",
                )
            else:
                # More than 30 minutes – advise to contact support with phone number if configured
                support_phone = getattr(settings, "SUPPORT_PHONE", None)
                if support_phone:
                    extra = _t(
                        lang,
                        f"\n\nIt has been more than 30 minutes since you submitted your complaint.\nFor further assistance, please call: {support_phone}.",
                        f"\n\nImepita zaidi ya dakika 30 tangu ulipowasilisha malalamiko yako.\nKwa msaada zaidi, tafadhali piga simu: {support_phone}.",
                    )
                else:
                    extra = _t(
                        lang,
                        "\n\nIt has been more than 30 minutes since you submitted your complaint.\nPlease contact the district office for further assistance.",
                        "\n\nImepita zaidi ya dakika 30 tangu ulipowasilisha malalamiko yako.\nTafadhali wasiliana na ofisi ya wilaya kwa msaada zaidi.",
                    )
    except Exception:
        # If parsing or timing fails, just return the base info without timing text.
        extra = ""

    return base + extra


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


def get_main_menu(lang="sw"):
    """
    Main menu text.

    NOTE: For now we only use Kiswahili as the active language.
    """
    return (
        "Habari,\n"
        "Karibu Wilaya ya Chemba!\n\n"
        "Nipo hapa kukuhudumia na kukupa taarifa zaidi kuhusu huduma, idara na fursa "
        "zinazopatikana katika Wilaya yetu ya Chemba.\n"
        "👉 Tafadhali chagua eneo unalotaka kupata taarifa:\n\n"
        "1️⃣ Utangulizi wa Wilaya\n"
        "2️⃣ Taasisi za Serikali zinazopatikana ndani ya Wilaya ya Chemba\n"
        "3️⃣ Halmashauri ya Wilaya\n"
        "4️⃣ Fursa zilizopo katika Wilaya\n"
        "5️⃣ Maswali ya Haraka\n"
        "6️⃣ Angalia Hali ya Maombi\n"
        "7️⃣ Wasilisha Malalamiko\n"
        "8️⃣ Fuatilia Malalamiko Yangu\n\n"
        "🔁 Jibu # kuanza upya wakati wowote."
    )


def get_welcome_message(lang="sw"):
    """Welcome message (currently same as main menu, in Kiswahili)."""
    return get_main_menu(lang)


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
        reply = get_welcome_message(session_language or "sw")
        return next_state, ctx, reply

    # ----- Welcome / first message -> main menu (default Kiswahili) -----
    if state == WELCOME:
        next_state = MAIN_MENU
        reply = get_welcome_message("sw")
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
        # For now, we only use Kiswahili.
        if msg == "1":
            # Utangulizi wa Wilaya
            reply = (
                "1️⃣ Utangulizi wa Wilaya ya Chemba\n\n"
                "• Jiografia na mipaka ya Wilaya:\n"
                "  - Kaskazini: Wilaya ya Kondoa\n"
                "  - Mashariki: Wilaya ya Kiteto\n"
                "  - Kusini: Wilaya ya Bahi\n"
                "  - Kusini Mashariki: Wilaya ya Chamwino\n"
                "  - Magharibi: Wilaya ya Manyoni na Singida\n"
                "  - Kaskazini Magharibi: Wilaya ya Hanang\n\n"
                "• Muundo wa utawala:\n"
                "  - Tarafa 4, Kata 26, Vijiji 114\n\n"
                "• Idadi ya watu:\n"
                "  - 339,333 (Me 170,837; Ke 168,496)\n\n"
                "• Jimbo la uchaguzi:\n"
                "  - Jimbo 1 la Uchaguzi\n\n"
                "• Halmashauri:\n"
                "  - Halmashauri 1 ya Wilaya ya Chemba\n\n"
                "• Dira ya Wilaya ya Chemba:\n"
                "  - Kuwa Halmashauri yenye utawala bora inayotoa huduma bora, "
                "inayochochea ukuaji endelevu wa uchumi na maendeleo jumuishi kwa wakazi wote.\n\n"
                "• Dhima ya Halmashauri:\n"
                "  - Kutoa utawala bora wa Serikali za Mitaa, kusimamia rasilimali kwa ufanisi, "
                "na kuboresha utoaji wa huduma ili kuendeleza maendeleo endelevu ya kijamii na kiuchumi.\n\n"
                "• Maadili ya msingi:\n"
                "  - Uwajibikaji\n"
                "  - Ubora katika huduma\n"
                "  - Ufanisi na thamani ya fedha\n"
                "  - Uwazi\n"
                "  - Uadilifu\n"
                "  - Ubunifu wa kimaendeleo\n"
                "  - Ushirikiano na kazi kwa pamoja\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "2":
            # Taasisi za Serikali
            reply = (
                "2️⃣ Taasisi za Serikali katika Wilaya ya Chemba\n\n"
                "Taasisi kuu za Serikali zinazopatikana ndani ya Wilaya ya Chemba ni:\n"
                "• TRA\n"
                "• TANESCO\n"
                "• VETA\n"
                "• RUWASA\n"
                "• TARURA\n"
                "• TFS\n"
                "• NIDA\n"
                "• RITA\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "3":
            # Halmashauri ya Wilaya
            reply = (
                "3️⃣ Halmashauri ya Wilaya ya Chemba\n\n"
                "Halmashauri ina idara na vitengo 20 vinavyotekeleza majukumu mbalimbali, ikiwemo:\n\n"
                "• Idara ya Huduma za Afya, Ustawi wa Jamii na Lishe:\n"
                "  - Vituo vya kutolea huduma za afya: Hospitali 1, Vituo vya afya 6, Zahanati 47 (jumla 54)\n"
                "  - Upatikanaji wa dawa: 52%\n"
                "  - Huduma bure kwa wazee wasiojiweza, mama mjamzito na watoto chini ya miaka 5\n\n"
                "• Idara ya Elimu ya Awali na Msingi:\n"
                "  - Shule za Msingi: 118\n"
                "  - Uandikishaji Awali: 7,548 (61%)\n"
                "  - Uandikishaji Darasa la Kwanza: 9,172 (76%)\n"
                "  - Walimu wa shule za msingi: 878\n\n"
                "• Idara ya Elimu ya Sekondari:\n"
                "  - Shule za Sekondari: 31\n"
                "  - Udahili Kidato cha Kwanza: 4,495\n"
                "  - Ufaulu: Kidato cha Pili 79.4%, Kidato cha Nne 94%, Kidato cha Sita 100%\n\n"
                "• Idara ya Viwanda, Biashara na Uwekezaji:\n"
                "  - Leseni za biashara (TAUSI): 721 (~30%)\n"
                "  - Viwanda vidogo na vya kati: Vidogo 543, Kati 3\n"
                "  - Fursa za uwekezaji: Maeneo maalum Chemba, Paranga na Kambi ya Nyasa\n\n"
                "• Idara ya Maendeleo ya Jamii:\n"
                "  - Mikopo isiyo na riba (10% ya mapato ya ndani): "
                "Tsh 408,125,000 (mwaka 2025/26)\n"
                "  - Wanufaika: wanawake, vijana na watu wenye ulemavu\n\n"
                "Halmashauri pia ina idara nyingine kama Kilimo, Miundombinu, Utawala, "
                "Sheria, Uhasibu, Ukaguzi wa Ndani, Tehama, Mawasiliano Serikalini na nyingine nyingi.\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "4":
            # Fursa zilizopo katika Wilaya
            reply = (
                "4️⃣ Fursa zilizopo katika Wilaya ya Chemba\n\n"
                "• Uwepo wa maeneo yaliyotengwa kwa ajili ya uwekezaji katika:\n"
                "  - Mji wa Chemba\n"
                "  - Paranga\n"
                "  - Kambi ya Nyasa\n\n"
                "Maeneo haya yana miundombinu wezeshi kama umeme, barabara na mawasiliano "
                "yanayorahisisha uwekezaji na shughuli za kiuchumi.\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "5":
            # Maswali ya Haraka (placeholder based on taarifa.md kichwa)
            reply = (
                "5️⃣ Maswali ya Haraka\n\n"
                "Sehemu hii inahusu maswali ya msingi kuhusu Wilaya ya Chemba, huduma na fursa zake.\n"
                "Kwa sasa tafadhali tumia menyu kuu kuchagua eneo unalotaka kupata taarifa zaidi, "
                "au wasiliana na Halmashauri ya Wilaya kwa ufafanuzi wa ziada.\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "6":
            # Angalia Hali ya Maombi (re-use existing check status flow)
            next_state = CHECK_DEPT
            reply = (
                "Chagua idara unayotaka kuangalia hali ya maombi:\n"
                "1️⃣ Ardhi (Ardhi)\n"
                "2️⃣ Umeme\n"
                "3️⃣ Afya\n"
                "4️⃣ Maji\n"
                "5️⃣ Biashara na Soko\n"
                "6️⃣ Nyingine"
            )
        elif msg == "7":
            # Wasilisha Malalamiko (re-use existing submit complaint flow)
            next_state = SUBMIT_DEPT
            reply = (
                "Chagua idara inayohusika na malalamiko yako:\n"
                "1️⃣ Ardhi\n"
                "2️⃣ Umeme\n"
                "3️⃣ Afya\n"
                "4️⃣ Maji\n"
                "5️⃣ Biashara na Soko"
            )
        elif msg == "8":
            # Fuatilia Malalamiko Yangu – same tracking logic as ticket tracking
            next_state = TRACK_TICKET
            lang = session_language or "sw"
            main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
            status_text = _ticket_status_message(ctx, lang)
            reply = f"{status_text}\n\n{main_menu_opt}"
        else:
            reply = _invalid_option("sw")
        return next_state, ctx, reply

    # ----- Check status: department -> ID type -> ID value -----
    if state == CHECK_DEPT:
        lang = session_language or "sw"
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
        lang = session_language or "sw"
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
        lang = session_language or "sw"
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
        lang = session_language or "sw"
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
        lang = session_language or "sw"
        dept = _get_dept_by_number(msg, with_other=False)
        if dept:
            ctx["submit_dept"] = dept
            next_state = SUBMIT_MESSAGE
            reply = _t(lang, "Please type your question or complaint below.", "Tafadhali andika swali au malalamiko yako hapa chini.")
        else:
            reply = _invalid_option(lang)
        return next_state, ctx, reply

    if state == SUBMIT_MESSAGE:
        lang = session_language or "sw"
        if not msg or len(msg) < 3:
            reply = _t(lang, "Please type your question or complaint (at least a few words).", "Tafadhali andika swali au malalamiko (angalau maneno machache).")
            return next_state, ctx, reply
        ticket_id = _generate_ticket_id()
        ctx["ticket_id"] = ticket_id
        ctx["ticket_message"] = msg
        ctx["ticket_timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        ctx["ticket_dept"] = ctx.get("submit_dept", "other")
        next_state = SUBMIT_CONFIRMED_OPTIONS
        received = _t(
            lang,
            "Your message has been received.\n",
            "Ujumbe wako umepokelewa, tutakurudia baada ya nusu saa na majibu sahihi.\n",
        )
        track_prompt = _t(lang, f"Ticket ID: {ticket_id}\n\n1️⃣ Main menu\n2️⃣ Track my ticket", f"Kitambulisho: {ticket_id}\n\n1️⃣ Menyu kuu\n2️⃣ Fuatilia tiketi yangu")
        reply = received + track_prompt
        return next_state, ctx, reply

    if state == SUBMIT_CONFIRMED_OPTIONS:
        lang = session_language or "sw"
        main_menu_only = _t(lang, "1️⃣ Main menu\n2️⃣ Track my ticket", "1️⃣ Menyu kuu\n2️⃣ Fuatilia tiketi yangu")
        main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
        if msg == "1":
            next_state = MAIN_MENU
            reply = get_main_menu(lang)
        elif msg == "2":
            next_state = TRACK_TICKET
            status_text = _ticket_status_message(ctx, lang)
            reply = f"{status_text}\n\n{main_menu_opt}"
        else:
            reply = main_menu_only
        return next_state, ctx, reply

    if state == TRACK_TICKET:
        lang = session_language or "sw"
        main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
        if msg == "1":
            next_state = MAIN_MENU
            reply = get_main_menu(lang)
        else:
            reply = main_menu_opt
        return next_state, ctx, reply

    # ----- Department info -----
    if state == DEPT_INFO_CHOICE:
        lang = session_language or "sw"
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
        lang = session_language or "sw"
        main_menu_opt = _t(lang, "1️⃣ Main menu", "1️⃣ Menyu kuu")
        if msg == "1":
            next_state = MAIN_MENU
            reply = get_main_menu(lang)
        else:
            reply = main_menu_opt
        return next_state, ctx, reply

    # Fallback: reset to main menu
    next_state = MAIN_MENU
    reply = get_main_menu(session_language or "sw")
    return next_state, ctx, reply
