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
COUNCIL_MENU = "council_menu"  # Sub-menu for option 3 (Halmashauri ya Wilaya)
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
# Submit swali (after FAQ button)
SUBMIT_QUESTION = "submit_question"
# Fuatilia: choose Malalamiko or Maswali then list
TRACK_CHOICE = "track_choice"
TRACK_LIST_SHOWN = "track_list_shown"  # after showing list, "1" or "Menyu kuu" -> main menu
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
        "Sorry, I didn't understand that.\nPlease reply with a valid option number, or reply # to return to the main menu.",
        "Samahani, sikuweza kuelewa.\nTafadhali jibu kwa nambari sahihi, au jibu # kurudi kwenye menyu kuu.",
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
    Includes a 24-hour SLA and support contact if available.
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
            diff_hours = max(0, (now - submitted).total_seconds() / 3600.0)
            answer_time = submitted + timedelta(hours=24)
            answer_time_str = answer_time.strftime("%Y-%m-%d %H:%M")
            if diff_hours < 24:
                # Under 24 hours – remind expected answer window
                extra = _t(
                    lang,
                    f"\n\nYour complaint was received at {ticket_timestamp}.\nYou will receive an answer within 24 hours (by {answer_time_str}).",
                    f"\n\nMalalamiko yako yalipokelewa saa {ticket_timestamp}.\nUtapokea majibu ndani ya masaa 24 (kabla ya {answer_time_str}).",
                )
            else:
                # More than 24 hours – advise to contact support
                support_phone = getattr(settings, "SUPPORT_PHONE", None)
                if support_phone:
                    extra = _t(
                        lang,
                        f"\n\nIt has been more than 24 hours since you submitted your complaint.\nPlease contact the district office for further assistance at: {support_phone}.",
                        f"\n\nImepita zaidi ya masaa 24 tangu ulipowasilisha malalamiko yako.\nTafadhali wasiliana na ofisi ya wilaya kwa msaada zaidi kupitia: {support_phone}.",
                    )
                else:
                    extra = _t(
                        lang,
                        "\n\nIt has been more than 24 hours since you submitted your complaint.\nPlease contact the district office for further assistance.",
                        "\n\nImepita zaidi ya masaa 24 tangu ulipowasilisha malalamiko yako.\nTafadhali wasiliana na ofisi ya wilaya kwa msaada zaidi.",
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


def get_main_menu(lang="sw", name=None):
    """
    Main menu text. Optional name for personalisation: "Habari, {name}" when provided.
    NOTE: For now we only use Kiswahili as the active language.
    """
    name_clean = (name or "").strip()
    greeting = "Habari, " + name_clean + "\n" if name_clean else "Habari,\n"
    return (
        greeting
        + "Karibu Wilaya ya Chemba!\n\n"
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
        "8️⃣ Fuatilia Malalamiko/Maswali Yangu\n\n"
        "🔁 Jibu # kuanza upya wakati wowote."
    )


def get_welcome_message(lang="sw", name=None):
    """Welcome message (currently same as main menu, in Kiswahili)."""
    return get_main_menu(lang, name=name)


# Greetings: if user sends any of these (exact match, case-insensitive), clear session and send welcome
GREETING_WORDS = frozenset({
    "hi", "hello", "hellow", "helo", "hey", "boss", "hei",
    "habari", "mambo", "niaje", "vipi", "vp", "kwema", "salama", "oi", "bablai",
    "za sahizi", "za asubuhi",
})

# Complaint keywords: if user sends any of these, go directly to option 7 (Wasilisha Malalamiko)
COMPLAINT_KEYWORDS = frozenset({
    "kero", "malalamiko", "changamoto",
})

# Question keywords: if user sends any of these, go to Maswali ya Haraka (option 5) – submit question flow
QUESTION_KEYWORDS = frozenset({
    "swali", "maswali",
})


def process_message(session_state, session_context, session_language, user_message, profile_name=None):
    """
    Process one user message. No DB for applications/complaints; session only.
    profile_name: optional WhatsApp display name for personalised welcome/menu.
    Returns: (next_state, context_update_dict, reply_text)
    """
    state = session_state or WELCOME
    ctx = dict(session_context or {})
    msg = (user_message or "").strip()
    reply = ""
    next_state = state
    name = (profile_name or "").strip() or None

    # ----- # = reset session (default key) -----
    if msg == "#":
        next_state = MAIN_MENU
        ctx = {}
        reply = get_welcome_message(session_language or "sw", name=name)
        return next_state, ctx, reply

    # ----- Greeting words: clear session and send welcome (same as #) -----
    msg_lower = msg.lower()
    if msg_lower in GREETING_WORDS:
        next_state = MAIN_MENU
        ctx = {}
        reply = get_welcome_message(session_language or "sw", name=name)
        return next_state, ctx, reply

    # ----- Complaint keywords: go directly to option 7 (Wasilisha Malalamiko) -----
    if msg_lower in COMPLAINT_KEYWORDS:
        next_state = SUBMIT_DEPT
        ctx.pop("submit_dept", None)
        reply = (
            "Chagua idara inayohusika na malalamiko yako:\n"
            "1️⃣ Ardhi\n"
            "2️⃣ Umeme\n"
            "3️⃣ Afya\n"
            "4️⃣ Maji\n"
            "5️⃣ Biashara na Soko"
        )
        return next_state, ctx, reply

    # ----- Question keywords (e.g. "swali"): go to Maswali ya Haraka – submit question flow -----
    if msg_lower in QUESTION_KEYWORDS:
        next_state = SUBMIT_QUESTION
        reply = _t(
            session_language or "sw",
            "Please type your question below. You will receive an answer within 24 hours.",
            "Andika swali lako hapa chini. Utapokea majibu ndani ya masaa 24.",
        )
        return next_state, ctx, reply

    # ----- Welcome / first message -> main menu (default Kiswahili) -----
    if state == WELCOME:
        next_state = MAIN_MENU
        reply = get_welcome_message("sw", name=name)
        return next_state, ctx, reply

    # ----- Language choice (option 4 from main menu) -----
    if state == LANGUAGE_CHOICE:
        lang_prompt_en = "Please choose language:\n1️⃣ Kiswahili\n2️⃣ English"
        lang_prompt_sw = "Chagua lugha:\n1️⃣ Kiswahili\n2️⃣ English"
        lang_prompt = lang_prompt_sw if session_language == "sw" else lang_prompt_en
        if msg == "1":
            ctx["language"] = "sw"
            next_state = MAIN_MENU
            reply = get_welcome_message("sw", name=name)
        elif msg == "2":
            ctx["language"] = "en"
            next_state = MAIN_MENU
            reply = get_welcome_message("en", name=name)
        else:
            reply = lang_prompt
        return next_state, ctx, reply

    # ----- Main menu -----
    if state == MAIN_MENU:
        # For now, we only use Kiswahili.
        if msg == "1":
            # Utangulizi wa Wilaya – full content from taarifa.md
            reply = (
                "1️⃣ Utangulizi wa Wilaya ya Chemba\n\n"
                "• Jiografia na mipaka ya Wilaya: Wilaya ya Chemba kwa upande wa Kaskazini imepakana na Wilaya ya Kondoa, "
                "Mashariki imepakana na Wilaya ya Kiteto, Kusini imepakana na Wilaya ya Bahi, Kusini Mashariki imepakana na "
                "Wilaya ya Chamwino, Magharibi imepakana na Wilaya ya Manyoni na Wilaya ya Singida na Kaskazini Magharibi "
                "imepakana na Wilaya ya Hanang.\n"
                "• Muundo wa utawala (Tarafa, Kata, Vijiji): Tarafa 4, Kata 26 na Vijiji 114.\n\n"
                "• Idadi ya watu: Wilaya ina jumla ya wakazi 339,333 (Me- 170,837 na Ke- 168,496).\n"
                "• Jimbo: Wilaya ya Chemba ina Jimbo 1 la Uchaguzi.\n"
                "• Halmashauri: Wilaya ya Chemba ina Halmashauri 1 ya Wilaya.\n\n"
                "• Dira ya Wilaya ya Chemba: Kuwa Halmashauri yenye utawala bora inayotoa huduma bora zenye ubora wa hali ya juu, "
                "inayochochea ukuaji endelevu wa uchumi na maendeleo jumuishi kwa wakazi wote.\n"
                "• Dhima ya Halmashauri: Kutoa utawala bora wa Serikali za Mitaa, kusimamia rasilimali kwa ufanisi, na kuboresha "
                "utoaji wa huduma ili kuendeleza maendeleo endelevu ya kijamii na kiuchumi.\n\n"
                "• Maadili ya Msingi:\n"
                "  - Uwajibikaji: Kudumisha wajibu na uwajibikaji katika utoaji wa huduma na utekelezaji wa miradi ya maendeleo.\n"
                "  - Ubora katika Huduma: Kutoa huduma bora, kwa wakati, na zinazokidhi mahitaji ya jamii.\n"
                "  - Ufanisi na Thamani ya Fedha: Kuhakikisha matumizi bora ya rasilimali katika utoaji wa huduma na uhamasishaji wa uwekezaji.\n"
                "  - Uwazi: Kukuza uwazi na upatikanaji wa taarifa ili kuongeza imani ya umma.\n"
                "  - Uadilifu: Kudumisha uaminifu, maadili mema, utawala wa sheria, na heshima kwa utu wa binadamu.\n"
                "  - Ubunifu wa Kimaendeleo: Kuweka na kutumia mbinu bunifu kuboresha utoaji wa huduma na maendeleo ya uchumi wa eneo.\n"
                "  - Ushirikiano na Kazi kwa Pamoja: Kukuza ushirikiano miongoni mwa watumishi, wadau, na washirika wa maendeleo.\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "2":
            # Taasisi za Serikali – full content from taarifa.md
            reply = (
                "2️⃣ Taasisi za Serikali zinazopatikana ndani ya Wilaya ya Chemba\n\n"
                "• TRA: Mamlaka ya Mapato Tanzania, ilianzishwa kwa Sheria ya Bunge Na. 11 ya mwaka 1995, na ilianza kufanya "
                "kazi tarehe 1 Julai 1996. Katika kutekeleza majukumu yake ya kisheria, TRA inaongozwa kwa sheria na ina "
                "jukumu la kusimamia kwa uadilifu kodi mbalimbali za Serikali Kuu.\n\n"
                "• VETA: Taasisi hii ilianzishwa kwa Sheria ya Bunge Na. 1 ya mwaka 1994 ikiwa na jukumu la kuratibu, kusimamia, "
                "kuwezesha, kukuza na kutoa elimu ya ufundi na mafunzo nchini Tanzania. Chuo cha VETA Chemba kinatoa mafunzo "
                "katika fani za mapambo, ushonaji, umeme wa majumbani, uchomeleaji, ujasiriamali na ujenzi.\n\n"
                "• RUWASA: Taasisi hii ina jukumu la kuandaa mipango, kusanifu miradi ya maji, kujenga na kusimamia uendeshaji "
                "wake. Inaendeleza vyanzo vya maji kwa kufanya utafiti wa maji chini ya ardhi na kuchimba visima pamoja na "
                "kujenga mabwawa, pamoja na kufanya matengenezo makubwa ya miundombinu ya maji vijijini. Mpaka sasa, taasisi "
                "inasimamia mradi wa maji wa miji 28 wenye thamani ya Shilingi bilioni 11 katika mji wa Chemba na vijiji vya "
                "Paranga, Chemba, Chambalo, Kambi ya Nyasa na Gwandi.\n\n"
                "• TARURA: Taasisi hii ina jukumu la kusimamia ujenzi, ukarabati na matengenezo ya mtandao wa barabara za Wilaya.\n\n"
                "• NIDA: Mamlaka ya Vitambulisho vya Taifa ina majukumu yafuatayo miongoni mwa mengine:\n"
                "  - Kutoa Namba ya Utambulisho wa Taifa (NIN) kwa wakazi halali wa Tanzania.\n"
                "  - Kusimamia mfumo wa utambulisho wa taifa na kuhakikisha unafanya kazi ipasavyo na kuhifadhi taarifa sahihi za wananchi.\n"
                "  - Kutoa kadi ya NIDA kama nyaraka ya kisheria inayotumika kama kitambulisho cha msingi kwa wakazi halali wa Tanzania.\n\n"
                "• RITA: Taasisi hii inasimamia na kutoa vyeti mbalimbali kama cheti cha kuzaliwa ndani ya siku tano (5) baada ya "
                "kukamilisha taratibu za maombi; vyeti vya kifo ndani ya siku 5 za kazi baada ya kukamilisha taratibu za maombi; "
                "pamoja na vyeti vya kuasili ndani ya siku 3 baada ya kukamilisha taratibu husika.\n\n"
                "• TFS: Wakala wa Huduma za Misitu Tanzania (TFS) ni taasisi ya serikali iliyopewa jukumu la kusimamia kwa "
                "uendelevu na kuhifadhi rasilimali za misitu na nyuki nchini Tanzania. TFS ilianzishwa mwaka 2010 kwa lengo la "
                "kulinda mifumo hii muhimu ya ikolojia kwa manufaa ya vizazi vya sasa na vijavyo.\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "3":
            # Halmashauri ya Wilaya – open sub-menu to avoid long single message
            ctx["council_mode"] = "menu"
            next_state = COUNCIL_MENU
            reply = (
                "3️⃣ Halmashauri ya Wilaya ya Chemba\n\n"
                "Halmashauri ina idara na vitengo 20 vinavyotekeleza majukumu mbalimbali.\n\n"
                "Chagua idara au kitengo unachotaka kujua zaidi:\n"
                "1️⃣ Afya, Ustawi wa Jamii na Lishe\n"
                "2️⃣ Elimu ya Awali na Msingi\n"
                "3️⃣ Elimu ya Sekondari\n"
                "4️⃣ Mipango na Uratibu\n"
                "5️⃣ Viwanda, Biashara na Uwekezaji\n"
                "6️⃣ Maendeleo ya Jamii\n"
                "7️⃣ Kilimo, Mifugo na Uvuvi\n"
                "8️⃣ Miundombinu, Maendeleo ya Vijijini na Mjini\n"
                "9️⃣ Utawala na Rasilimali Watu\n"
                "🔟 Vitengo vingine (Taka, Mazingira, Michezo, Uchaguzi, Uhasibu, Sheria, Ukaguzi, Ununuzi, Tehama, Mawasiliano, Ufuatiliaji na Tathmini)\n\n"
                "👉 Jibu kwa namba ya idara (1–10), au jibu 0 kurudi kwenye menyu kuu."
            )
        elif msg == "4":
            # Fursa zilizopo katika Wilaya – content from taarifa.md (plus brief explanation)
            reply = (
                "4️⃣ Fursa zilizopo katika Wilaya ya Chemba\n\n"
                "• Uwepo wa maeneo yaliyotengwa kwa ajili ya uwekezaji katika Mji wa Chemba, Paranga na Kambi ya Nyasa.\n\n"
                "Maeneo haya yana miundombinu wezeshi kama umeme, barabara na mawasiliano yanayorahisisha uwekezaji na shughuli za kiuchumi.\n\n"
                "👉 Unaweza kuchagua namba nyingine au jibu # kuanza upya."
            )
            next_state = MAIN_MENU
        elif msg == "5":
            # Maswali ya Haraka – Maswali Yanayoulizwa Mara kwa Mara (FAQ)
            reply = (
                "5️⃣ Maswali ya Haraka – Maswali Yanayoulizwa Mara kwa Mara (FAQ)\n\n"
                "1. Wilaya ya Chemba ipo katika eneo gani na inapakana na wilaya zipi?\n"
                "Wilaya ya Chemba ipo Mkoa wa Dodoma. Inapakana na Wilaya ya Kondoa (Kaskazini), Kiteto (Mashariki), Bahi (Kusini), Chamwino (Kusini Mashariki), Manyoni na Singida (Magharibi), na Hanang (Kaskazini Magharibi).\n\n"
                "2. Muundo wa utawala wa Wilaya ya Chemba ukoje?\n"
                "Wilaya ya Chemba ina Tarafa 4, Kata 26 na Vijiji 114 vinavyosimamiwa chini ya Halmashauri ya Wilaya ya Chemba.\n\n"
                "3. Idadi ya watu wa Wilaya ya Chemba ni kiasi gani?\n"
                "Wilaya ya Chemba ina wakazi wapatao 339,333, kati yao wanaume ni 170,837 na wanawake ni 168,496.\n\n"
                "4. Je, Wilaya ya Chemba ina majimbo na halmashauri ngapi?\n"
                "Wilaya ya Chemba ina Jimbo 1 la Uchaguzi na Halmashauri 1 ya Wilaya.\n\n"
                "5. Dira na dhima ya Halmashauri ya Wilaya ya Chemba ni ipi?\n"
                "Dira ni kuwa Halmashauri yenye utawala bora inayotoa huduma bora na kuchochea maendeleo endelevu ya kiuchumi na kijamii. Dhima ni kutoa utawala bora wa Serikali za Mitaa, kusimamia rasilimali kwa ufanisi na kuboresha utoaji wa huduma kwa wananchi.\n\n"
                "6. Ni taasisi zipi za Serikali zinazopatikana ndani ya Wilaya ya Chemba?\n"
                "Baadhi ya taasisi zilizopo ni TRA, TANESCO, VETA, RUWASA, TARURA, TFS, NIDA na RITA.\n\n"
                "7. Huduma za afya zinapatikana vipi katika Wilaya ya Chemba?\n"
                "Wilaya ina jumla ya vituo vya kutolea huduma za afya 54, ikijumuisha Hospitali 1, Vituo vya Afya 6 na Zahanati 47. Huduma kwa wazee wasiojiweza, mama wajawazito na watoto chini ya miaka 5 hutolewa bure.\n\n"
                "8. Sekta ya elimu ikoje katika Wilaya ya Chemba?\n"
                "Wilaya ina shule za msingi 118 na shule za sekondari 31. Ufaulu wa Darasa la Saba mwaka 2025 ulikuwa 88.6%, huku ufaulu wa Kidato cha Sita ukiwa 100%.\n\n"
                "9. Je, kuna mikopo kwa wanawake, vijana na watu wenye ulemavu?\n"
                "Ndiyo. Halmashauri hutoa mikopo isiyo na riba kupitia 10% ya mapato ya ndani. Mwaka wa fedha 2025/26 jumla ya Tsh 408,125,000 zilitolewa kwa vikundi vya wanawake, vijana na watu wenye ulemavu.\n\n"
                "10. Ni masharti gani ya kuomba mikopo ya 10%?\n"
                "Kikundi kiwe na wanachama 5 au zaidi, kiwe kimesajiliwa, kiwe na katiba, mradi halali, akaunti ya benki ya kikundi, na wanachama wasiwe na ajira rasmi. Vijana wawe na umri wa miaka 18–45.\n\n"
                "11. Fursa za uwekezaji zinapatikana wapi katika Wilaya ya Chemba?\n"
                "Fursa za uwekezaji zipo katika maeneo yaliyotengwa Mji wa Chemba, Paranga na Kambi ya Nyasa, yenye miundombinu ya umeme, barabara na mawasiliano.\n\n"
                "12. Sekta ya kilimo na mifugo ina mchango gani kwa Wilaya?\n"
                "Takribani 85% ya wananchi wanajihusisha na kilimo cha mazao ya chakula na biashara. Huduma za ugani, mifugo na chanjo zinatolewa ili kuongeza uzalishaji na kipato cha wananchi.\n\n"
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
        elif msg == "Wasilisha swali":
            # Button from FAQ (option 5): go to submit-question flow
            next_state = SUBMIT_QUESTION
            reply = _t(
                session_language or "sw",
                "Please type your question below. You will receive an answer within 24 hours.",
                "Andika swali lako hapa chini. Utapokea majibu ndani ya masaa 24.",
            )
        elif msg == "8":
            # Fuatilia Malalamiko/Maswali Yangu – show choice (view sends 2 buttons)
            next_state = TRACK_CHOICE
            reply = _t(
                session_language or "sw",
                "What would you like to track?",
                "Unataka Fuatilia?",
            )
        else:
            reply = _invalid_option("sw")
        return next_state, ctx, reply

    # ----- Halmashauri sub-menu (option 3) -----
    if state == COUNCIL_MENU:
        lang = session_language or "sw"
        mode = ctx.get("council_mode", "menu")

        # 0 = back to main menu
        if msg == "0":
            next_state = MAIN_MENU
            reply = get_main_menu(lang, name=name)
            return next_state, ctx, reply

        # In detail mode, 3 = back to Halmashauri sub-menu list
        if mode == "detail" and msg == "3":
            ctx["council_mode"] = "menu"
            next_state = COUNCIL_MENU
            reply = (
                "3️⃣ Halmashauri ya Wilaya ya Chemba\n\n"
                "Halmashauri ina idara na vitengo 20 vinavyotekeleza majukumu mbalimbali.\n\n"
                "Chagua idara au kitengo unachotaka kujua zaidi:\n"
                "1️⃣ Afya, Ustawi wa Jamii na Lishe\n"
                "2️⃣ Elimu ya Awali na Msingi\n"
                "3️⃣ Elimu ya Sekondari\n"
                "4️⃣ Mipango na Uratibu\n"
                "5️⃣ Viwanda, Biashara na Uwekezaji\n"
                "6️⃣ Maendeleo ya Jamii\n"
                "7️⃣ Kilimo, Mifugo na Uvuvi\n"
                "8️⃣ Miundombinu, Maendeleo ya Vijijini na Mjini\n"
                "9️⃣ Utawala na Rasilimali Watu\n"
                "🔟 Vitengo vingine (Taka, Mazingira, Michezo, Uchaguzi, Uhasibu, Sheria, Ukaguzi, Ununuzi, Tehama, Mawasiliano, Ufuatiliaji na Tathmini)\n\n"
                "👉 Jibu kwa namba ya idara (1–10), au jibu 0 kurudi kwenye menyu kuu."
            )
            return next_state, ctx, reply

        # For all other numeric options, stay within COUNCIL_MENU
        next_state = COUNCIL_MENU
        back_hint = "\n\n👉 Jibu 3 kurudi kwenye orodha ya Halmashauri, au jibu # kurudi kwenye menyu kuu."

        if msg == "1":
            # Afya, Ustawi wa Jamii na Lishe
            reply = (
                "i. Idara ya Huduma za Afya, Ustawi wa Jamii na Lishe\n\n"
                "• Hospitali, vituo vya afya na zahanati: jumla ya vituo 54 (Hospitali 1, Vituo vya Afya 6 na Zahanati 47).\n"
                "• Upatikanaji wa dawa: 52%.\n"
                "• Huduma kwa wazee na watoto: Huduma kwa wazee wasiojiweza, mama wajawazito na watoto chini ya miaka 5 zinatolewa bure.\n"
                "• Rasilimali watu katika sekta ya afya: 282.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "2":
            # Elimu ya Awali na Msingi
            reply = (
                "ii. Idara ya Elimu ya Awali na Msingi\n\n"
                "• Shule za Msingi: 118.\n"
                "• Uandikishaji Darasa la Awali na la Kwanza: Awali 7,548 (61%) na Darasa la Kwanza 9,172 (76%).\n"
                "• Walimu na mazingira ya kujifunzia: walimu 878.\n"
                "• Ufaulu wa Darasa la Saba: Mwaka 2025 ni 88.6%.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "3":
            # Elimu ya Sekondari
            reply = (
                "iii. Idara ya Elimu ya Sekondari\n\n"
                "• Shule za Sekondari: 31.\n"
                "• Udahili Kidato cha Kwanza: 4,495.\n"
                "• Walimu wa Sekondari: 391.\n"
                "• Ufaulu wa mitihani ya Taifa: Kidato cha Pili 79.4%, Kidato cha Nne 94%, Kidato cha Sita 100%.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "4":
            # Mipango na Uratibu
            reply = (
                "iv. Idara ya Mipango na Uratibu\n\n"
                "Idara hii inajihusisha na usimamizi wa miradi ya maendeleo.\n"
                "Kwa mwaka wa fedha 2025/26, jumla ya Tsh 3,582,222,007 zimepokelewa kutoka Serikali Kuu na wahisani kwa ajili ya "
                "kutekeleza miradi mbalimbali ya maendeleo.\n\n"
                "Baadhi ya miradi mikubwa iliyopokea fedha ni:\n"
                "• Ujenzi wa shule 3 mpya za Msingi:\n"
                "  - Chemba: Tsh 397,200,000\n"
                "  - Kidoka: Tsh 302,200,000\n"
                "  - Soya: Tsh 302,200,000\n"
                "• Ujenzi wa Stendi ya mabasi katika mji wa Chemba: Tsh 650,000,000\n"
                "• Ujenzi wa nyumba 2 za watumishi wa Afya (Hospitali ya Wilaya, nyumba 3-in-1): Tsh 300,000,000\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "5":
            # Viwanda, Biashara na Uwekezaji
            reply = (
                "v. Idara ya Viwanda, Biashara na Uwekezaji\n\n"
                "• Leseni za biashara (TAUSI): 721 sawa na takribani 30% ya walengwa.\n"
                "• Viwanda vidogo na vya kati: viwanda vya kati 3 na vidogo 543.\n"
                "• Fursa za uwekezaji: uwepo wa maeneo yaliyotengwa kwa ajili ya viwanda katika mji wa Chemba, Paranga na Kambi ya Nyasa.\n"
                "• Miundombinu wezeshi: miundombinu ya umeme, barabara na mawasiliano ipo na maeneo yanafikika kwa urahisi.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "6":
            # Maendeleo ya Jamii
            reply = (
                "vi. Idara ya Maendeleo ya Jamii\n\n"
                "• Mikopo isiyo na riba (10% ya mapato ya ndani): Fedha zilizokopeshwa kwa mwaka wa fedha 2025/26 ni Tsh 408,125,000.\n"
                "• Wanufaika: wanawake, vijana na watu wenye ulemavu.\n"
                "• Masharti na hatua za kuomba mikopo:\n"
                "  - Kikundi kiwe na idadi ya watu 5 au zaidi.\n"
                "  - Wanakikundi wawe na umri wa kuanzia miaka 18 na kuendelea kwa vikundi vya wanawake na wenye ulemavu, "
                "na miaka 18–45 kwa vikundi vya vijana.\n"
                "  - Kikundi kiwe kimesajiliwa na kupata cheti na kiwe na katiba.\n"
                "  - Kikundi kiwe na shughuli (mradi) halali.\n"
                "  - Kikundi kiwe na akaunti ya benki iliyofunguliwa kwa jina la kikundi.\n"
                "  - Wanakikundi wasiwe na ajira rasmi.\n"
                "  - Kwa vikundi vya watu wenye ulemavu, kuanzia mshiriki 1 na kuendelea.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "7":
            # Kilimo, Mifugo na Uvuvi
            reply = (
                "vii. Idara ya Kilimo, Mifugo na Uvuvi\n\n"
                "• Mazao ya biashara na chakula: takribani 85% ya wananchi wanajihusisha na kilimo cha mazao ya chakula na biashara.\n"
                "• Huduma za ugani kwa wakulima: 65%.\n"
                "• Huduma za mifugo (chanjo, tiba, usimamizi wa malisho): 68%.\n"
                "• Ufugaji wa kisasa na uzalishaji wa mifugo: ufugaji wa kisasa unakadiriwa kufikia 24%.\n"
                "• Uvuvi na ufugaji wa samaki pamoja na fursa za mikopo na vikundi vya wakulima/wafugaji vinaendelezwa na Halmashauri.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "8":
            # Miundombinu, Maendeleo ya Vijijini na Mjini
            reply = (
                "viii. Idara ya Miundombinu, Maendeleo ya Vijijini na Mjini\n\n"
                "Idara hii ina jukumu la kusimamia miradi mbalimbali ya maendeleo, kuandaa makadirio ya gharama za ujenzi, kufanya "
                "ukaguzi na kutoa vibali vya ujenzi wa majengo ya Serikali, taasisi na watu binafsi.\n"
                "Mpaka sasa, idara inasimamia miradi 47 iliyopata fedha kutoka Serikali Kuu na kutoka kwa wahisani.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "9":
            # Utawala na Rasilimali Watu
            reply = (
                "ix. Idara ya Utawala na Usimamizi wa Rasilimali Watu\n\n"
                "Idara hii ina jukumu la kusimamia masuala ya kiutawala na rasilimali watu ndani ya Halmashauri.\n"
                "Inahakikisha nidhamu ya watumishi mahali pa kazi, kupanga na kusimamia mahitaji ya watumishi kulingana na majukumu "
                "ya ofisi.\n"
                "Mpaka sasa, Halmashauri ina jumla ya watumishi 1,921 kwa kada mbalimbali.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        elif msg == "10":
            # Vitengo vingine (grouped)
            reply = (
                "x–xx. Vitengo vingine vya Halmashauri ya Wilaya ya Chemba\n\n"
                "x. Kitengo cha Udhibiti wa Taka Ngumu na Usafi wa Mazingira:\n"
                "• Kudhibiti taka ngumu na kuuweka mji katika hali ya usafi.\n"
                "• Kusimamia uoteshaji wa vitalu vya miti na upandaji miti katika taasisi za Serikali, shule za msingi na sekondari.\n"
                "  Mpaka sasa jumla ya miche 260,000 imepandwa kati ya lengo la miti 500,000 kwa mwaka.\n\n"
                "xi. Kitengo cha Mali Asili na Hifadhi ya Mazingira:\n"
                "• Kusimamia shughuli za mali asili ikijumuisha misitu, nyuki, wanyamapori na mazingira.\n"
                "• Kutoa elimu kwa jamii juu ya uhifadhi endelevu wa rasilimali za misitu.\n"
                "  Halmashauri ina misitu ya vijiji 16 iliyohifadhiwa pamoja na pori 1 la akiba Swagaswaga, na hifadhi za nyuki 4 "
                "katika vijiji vya Jogolo, Baaba, Sanzawa na Mialo.\n\n"
                "xii. Kitengo cha Michezo, Utamaduni na Sanaa:\n"
                "• Kusimamia michezo, utamaduni na sanaa.\n"
                "• Kuibua na kulea vipaji kutoka kwenye jamii na kutoa elimu juu ya umuhimu wa michezo na utunzaji wa utamaduni.\n\n"
                "xiii. Kitengo cha Uchaguzi:\n"
                "• Kuratibu shughuli zote zihusuzo uchaguzi (Serikali za Mitaa, Uchaguzi Mkuu na chaguzi ndogo).\n"
                "• Kuratibu mazoezi ya uboreshaji wa daftari la kudumu la wapiga kura na orodha za wapiga kura.\n"
                "• Kumshauri Mkurugenzi juu ya masuala yote yahusuyo uchaguzi ndani ya Halmashauri.\n\n"
                "xiv. Kitengo cha Uhasibu:\n"
                "• Kusimamia mapato ya ndani ya Halmashauri.\n"
                "• Kwa miaka 2 mfululizo, Halmashauri imevuka lengo la kukusanya mapato ya ndani: 2023/2024 - 110%, 2024/2025 - 117%.\n"
                "  Mpaka sasa imekusanya 63% ya lengo la mwaka 2025/26.\n\n"
                "xv. Kitengo cha Sheria:\n"
                "• Kusimamia masuala mbalimbali ya kisheria yanayohusu Halmashauri.\n"
                "• Kwa sasa, jumla ya kesi 6 zinasimamiwa na kitengo hiki.\n\n"
                "xvi. Kitengo cha Ukaguzi wa Ndani:\n"
                "• Kutathmini michakato ya kifedha, uendeshaji na usimamizi wa Halmashauri.\n"
                "• Kupima udhibiti wa ndani na kutoa taarifa za ukaguzi kwa uongozi na kamati ya ukaguzi.\n"
                "• Kupendekeza maboresho ya mifumo na utendaji kazi.\n\n"
                "xvii. Kitengo cha Usimamizi wa Ununuzi:\n"
                "• Kusimamia sheria, kanuni na taratibu za ununuzi.\n"
                "• Kusimamia mikataba yote ya utekelezaji wa miradi kati ya wazabuni na mafundi wa Halmashauri, pamoja na ngazi za chini.\n"
                "  Mpaka sasa kitengo kinasimamia mikataba 47 ya miradi ya maendeleo ya mwaka 2025/26.\n\n"
                "xviii. Kitengo cha Tehama:\n"
                "• Kusimamia mifumo yote ya TEHAMA ndani ya Halmashauri, ikiwemo TAUSI, GOTHOMIS, IFTMIS, SIS na e-UTENDAJI (PEPMIS na PlanRep).\n\n"
                "xix. Kitengo cha Mawasiliano Serikalini:\n"
                "• Kutoa taarifa kwa umma kuhusu shughuli mbalimbali zinazotekelezwa na Halmashauri na Serikali kwa ujumla.\n\n"
                "xx. Kitengo cha Ufuatiliaji na Tathmini:\n"
                "• Kufuatilia na kufanya tathmini ya miradi ya maendeleo inayotekelezwa katika Halmashauri ili kuhakikisha miradi "
                "inakamilika kwa wakati na kwa ubora uliokusudiwa. Kwa sasa miradi 47 inaendelea kusimamiwa.\n"
            ) + back_hint
            ctx["council_mode"] = "detail"
        else:
            reply = _invalid_option(lang)

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
            reply = contact_support + get_main_menu(lang, name=name)
        elif msg == "3":
            next_state = MAIN_MENU
            ctx.pop("check_dept", None)
            ctx.pop("check_id_type", None)
            ctx.pop("last_check_identifier", None)
            reply = get_main_menu(lang, name=name)
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
            "Your message has been received. We will get back to you within 24 hours.\n\n",
            "Ujumbe wako umepokelewa. Utapokea majibu ndani ya masaa 24.\n\n",
        )
        reply = (
            received
            + _t(lang, f"Tracking ID: {ticket_id}\nMessage: {msg}\n\n", f"Kitambulisho: {ticket_id}\nUjumbe: {msg}\n\n")
        )
        reply += _t(lang, "Tap a button below.", "Bonyeza button hapa chini.")
        return next_state, ctx, reply

    if state == SUBMIT_CONFIRMED_OPTIONS:
        lang = session_language or "sw"
        main_menu_only = _t(lang, "Tap: Menyu kuu or Fuatilia tiketi yangu", "Bonyeza: Menyu kuu au Fuatilia tiketi yangu")
        if msg in ("1", "Menyu kuu"):
            next_state = MAIN_MENU
            reply = get_main_menu(lang, name=name)
        elif msg in ("2", "Fuatilia tiketi yangu", "Fuatilia tiketi"):
            next_state = TRACK_TICKET
            status_text = _ticket_status_message(ctx, lang)
            reply = status_text
        else:
            reply = main_menu_only
        return next_state, ctx, reply

    if state == TRACK_TICKET:
        lang = session_language or "sw"
        main_menu_opt = _t(lang, "Tap Menyu kuu to return.", "Bonyeza Menyu kuu kurudi.")
        if msg in ("1", "Menyu kuu"):
            next_state = MAIN_MENU
            reply = get_main_menu(lang, name=name)
        else:
            reply = main_menu_opt
        return next_state, ctx, reply

    # ----- After showing track list: only "1" or "Menyu kuu" goes to main menu -----
    if state == TRACK_LIST_SHOWN:
        lang = session_language or "sw"
        if msg in ("1", "Menyu kuu"):
            next_state = MAIN_MENU
            reply = get_main_menu(lang, name=name)
        else:
            reply = _t(lang, "Tap Menyu kuu to return to main menu.", "Bonyeza Menyu kuu kurudi kwenye menyu kuu.")
        return next_state, ctx, reply

    # ----- Submit swali (after FAQ "Wasilisha swali" button) -----
    if state == SUBMIT_QUESTION:
        lang = session_language or "sw"
        if not msg or len(msg.strip()) < 2:
            reply = _t(
                lang,
                "Please type your question (at least a few characters).",
                "Tafadhali andika swali lako (angalau herufi chache).",
            )
            return next_state, ctx, reply
        ticket_id = _generate_ticket_id()
        ctx["ticket_id"] = ticket_id
        ctx["ticket_message"] = msg.strip()
        ctx["ticket_type"] = "question"
        ctx["ticket_timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        # After submitting a question, treat \"1\" / \"Menyu kuu\" like TRACK_TICKET:
        # pressing 1 should show the full main menu, not option 1.
        next_state = TRACK_TICKET
        reply = _t(
            lang,
            f"Your question has been received. Tracking ID: {ticket_id}\nYou will get an answer within 24 hours.\n\n1️⃣ Main menu",
            f"Umewasilisha swali lako.\nKitambulisho chako: {ticket_id}\nUtapokea majibu ndani ya masaa 24. Unaweza kufuatilia kwa chaguo 8 (Fuatilia Malalamiko/Maswali Yangu).\n\n1️⃣ Menyu kuu",
        )
        return next_state, ctx, reply

    # ----- Fuatilia: Malalamiko or Maswali (view sends list from DB) -----
    if state == TRACK_CHOICE:
        lang = session_language or "sw"
        if msg == "Malalamiko":
            ctx["track_list_type"] = "complaint"
            next_state = TRACK_LIST_SHOWN
            reply = ""  # view will build list from DB
            return next_state, ctx, reply
        if msg == "Maswali":
            ctx["track_list_type"] = "question"
            next_state = TRACK_LIST_SHOWN
            reply = ""  # view will build list from DB
            return next_state, ctx, reply
        # invalid: re-ask with same prompt
        reply = "Unataka Fuatilia?"
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
            reply = get_main_menu(lang, name=name)
        else:
            reply = main_menu_opt
        return next_state, ctx, reply

    # Fallback: reset to main menu
    next_state = MAIN_MENU
    reply = get_main_menu(session_language or "sw", name=name)
    return next_state, ctx, reply
