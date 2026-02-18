import os
from pathlib import Path
from typing import Optional, Tuple

import requests
from django.conf import settings


OPENAI_API_KEY: Optional[str] = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = getattr(settings, "OPENAI_MODEL", None) or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Sentinel: when the model says the document has no answer
NO_ANSWER_MARKER = "NO_ANSWER"

# Core taarifa content used by the bot (embedded; we do NOT depend on the file at runtime)
TAARIFA_MD_SNIPPET = """
🤖 CHATBOT FLOW – WILAYA YA CHEMBA (TOLEO LILILOBORESHWA)
Habari,
Karibu Wilaya ya Chemba!

Nipo hapa kukuhudumia na kukupa taarifa zaidi kuhusu huduma, Idara na fursa zinazopatikana katika Wilaya yetu ya Chemba.
👉 Tafadhali chagua eneo unalotaka kupata taarifa:
1. Utangulizi wa Wilaya
• Jiografia na mipaka ya Wilaya :   Wilaya ya Chemba kwa upande wa Kaskazini imepakana na Wilaya ya  Kondoa, Mashariki imepakana na Wilaya ya Kiteto, Kusini imepekana na Wilaya ya Bahi, Kusini Mashariki imepakana na Wilaya ya Chamwino, Magharibi imepakana na Wilaya ya Manyoni na Wilaya ya Singida na Kaskazini Magharibi imepakana na Wilaya ya Hanang.  Muundo wa utawala (Tarafa, Kata, Vijiji) : Tarafa 4,  Kata 26 na Vijiji 114
• Idadi ya watu : Wilaya ina jumla ya wakazi 339,333 (Me- 170,837 na  Ke- 168,496)
• Jimbo : Wilaya ya Chemba ina Jimbo 1 la Uchaguzi
• Halmashauri : Wilaya ya Chemba ina halmashauri 1 ya Wilaya

• Dira ya Wilaya ya Chemba:  Kuwa Halmashauri yenye utawala bora inayotoa huduma bora zenye ubora wa hali ya juu, inayochochea ukuaji endelevu wa uchumi na maendeleo jumuishi kwa wakazi wote.
• Dhima ya Halmashauri : Kutoa utawala bora wa Serikali za Mitaa, kusimamia rasilimali kwa ufanisi, na kuboresha utoaji wa huduma ili kuendeleza maendeleo endelevu ya kijamii na kiuchumi.
 
• Maadili ya Msingi :
Uwajibikaji: Kudumisha wajibu na uwajibikaji katika utoaji wa huduma na utekelezaji wa miradi ya maendeleo
Ubora katika Huduma: Kutoa huduma bora, kwa wakati, na zinazokidhi mahitaji ya jamii
Ufanisi na Thamani ya Fedha: Kuhakikisha matumizi bora ya rasilimali katika utoaji wa huduma na uhamasishaji wa uwekezaji
Uwazi: Kukuza uwazi na upatikanaji wa taarifa ili kuongeza imani ya umma
Uadilifu: Kudumisha uaminifu, maadili mema, utawala wa sheria, na heshima kwa utu wa binadamu
Ubunifu na Ubunifu wa Kimaendeleo: Kuweka na kutumia mbinu bunifu kuboresha utoaji wa huduma na maendeleo ya uchumi wa eneo
Ushirikiano na Kazi kwa Pamoja: Kukuza ushirikiano miongoni mwa watumishi, wadau, na washirika wa maendeleo
 
2. Taasisi za Serikali zinazopatikana ndani ya Wilaya ya Chemba
• TRA : Mamlaka ya mapato Tanzania, ilianzishwa kwa sheria ya Bunge na.11 ya Mwaka 1995, na ilianza kufanya kazi tarehe 1, Julai 1996. Katika kutekeleza majukumu yake ya Kisheria,TRA inaongozwa kwa sheria na in ajukumu la kusimamia kwa uadilifu kodi mbali mbali za Serikali kuu
• VETA : Taasisi hii ilianzishwa kwa Sheria ya Bunge Namba 1 ya mwaka 1994 ikiwa na jukumu la kuratibu, kusimamia, Kuwezesha, Kukuza na kutoa elimu ya ufundi na mafunzo nchini Tanzania. Chuo cha Veta Chemba kinatoa mafunzo kwa fani zifuatazo; Mapambo, ushonaji,umeme wa majumbani uchomeleaji, ujasiria mali na ujenzi.
• RUWASA : Taasisi hii ina jukumu la kuaandaa mipango,kusanifu miradi ya maji,kujenga na kusimamia uendeshaji wake. Kuendeleza vyanzo vya maji kwa kufanya utafiti wa maji chini ya ardhi na kuchimba visima pamoja na kujenga mabwawa, Kufanya matengenezo makubwa ya miundo mbinu ya maji vijijini. Mpka sasa Taasisi ina simamia mradi wa maji wa miji 28 wenye thamani ya Shilingi bilioni 11 katika mji wa chemba vijiji vya paranga,chemba,chambalo kambi ya nyasa na gwandi.
• TARURA ; Tasisis hii jukumu la kusimamia ujenzi, ukarabati na matengenezo ya mtandao wa barabara za Wilaya.
● NIDA  : Yafuatayo ni baadhi ya majukumu yanayofanywa na taasisi ya NIDA,
Kutoa Namba ya Utambulisho wa Taifa (NIN): NIDA inahusika na utoaji wa NIN kwa wakazi halali wa Tanzania.
Kusimamia mfumo wa utambulisho: NIDA inahakikisha kuwa mfumo wa utambulisho wa taifa unafanya kazi ipasavyo na unahifadhi taarifa sahihi za wananchi.
Kutoa kadi ya NIDA: Kadi hii ni nyaraka ya kisheria inayotumika kama kitambulisho cha msingi kwa wakazi halali wa Tanzania
• RITA : Kusimamia na kutatoa vyeti mbali mbali kama cheti cha kuzaliwa ndani ya siku tano (5) baada ya kukamilisha taratibu za maombi; Kutatoa Cheti vya kifo ndani ya siku 5 za kazi ya baada ya kukamilisha taratibu za maombi; Kutoa vyeti vya kuasili ndani ya siku 3 baada ya kukamilisha taratibu za maombi.
• TFS : Wakala wa Huduma za Misitu Tanzania (TFS) ni taasisi ya serikali iliyopewa jukumu la kusimamia kwa uendelevu na kuhifadhi rasilimali za misitu na nyuki nchini Tanzania. Kama wakala wa utekelezaji, TFS ilianzishwa mwaka 2010 kwa lengo la kulinda mifumo hii muhimu ya ikolojia kwa manufaa ya vizazi vya sasa na vijavyo.
 
3. Halmashauri ya Wilaya:
Halmashauri ina idara na vitengo 20 ambazo hutekeleza majukumu mbalimbali kama ilivyoainishwa hapa chini:
i. Idara ya huduma za Afya,Ustawi wa Jamii na lishe;
• Hospitali, vituo vya afya na zahanati : 54 ( Hospitali 1, Vituo vya Afya 6 na Zahanati 47)
• Upatikanaji wa dawa :  52%
• Huduma kwa wazee na watoto : Huduma kwa wazee wasiojiweza, mama mjamzito na watoto chini ya miaka 5 zinatolewa bure
• Rasilimali watu katika sekta ya afya : 282
 
ii. Idara ya Elimu ya awali na  Msingi;  
• Shule za Msingi: 118
• Uandikishaji Darasa la Awali na la Kwanza : Awali 7,548 sawa  61% na Darasa la kwanza 9,172 sawa na 76%.
• Walimu na mazingira ya kujifunzia : 878
• Ufaulu wa Darasa la Saba : Mwaka 2025 ni sawa na 88.6%
iii. Idara ya Elimu ya sekondari:  Shule za Sekondari: 31
• Udahili Kidato cha Kwanza : 4,495
• Walimu wa Sekondari : 391
• Ufaulu wa Kidato cha Pili, Nne na Sita :  II- 79.4% , IV-94%, na VI-100%
 
iv. Idara ya Mipango na Uratibu; Idara hii inajihusisha na usimamizi wa miradi ya maendeleo ambapo kwa mwaka wa fedha 2025/26 jumla ya Tsh 3,582,222,007 zimepokelewa kutoka serikali kuu na wahisani kwa ajili ya kutekeleza miradi mbali mbali ya maendeleo. Badhi ya miradi mikubwa iliyopokea fedha ni kama ilivyoainishwa hapa chini:
Ujenzi wa shule 3 mpya za Msingi (Chemba-397,200,000, Kidoka - 302,200,000 na Soya- 302,200,000 ) , Ujenzi wa Stendi ya mabasi katika mji wa chemba- 650,000,000/=, Ujenzi wa nyumba 2 za watumishi wa Afya Hospitali ya Wilayaa 3in1 sh.300,000,000/=
 
v. Idara ya Viwanda,Biashara na uwekezaji;
• Leseni za biashara (TAUSI) : 721 sawa na asilimia 30%
• Viwanda vidogo na vya kati : Kati 03 na vidogo 543
• Fursa za uwekezaji : Uwepo wa maeneo yaliyotengwa kwa ajili ya viwanda katika mji wa Chemba ,Paranga na kambi ya nyasa.
• Miundombinu wezeshi (umeme, barabara, mawasiliano): Miundo mbinu ipo na maeneo yanafikika
 
vi. Idara ya Maendeleo ya jamii;
• Mikopo isiyo na riba (10% ya mapato ya ndani) : Fedha zilizokopesha kwa mwaka huu wa fedha 2025/26 ni Tsh. 408,125,000
• Wanufaika: wanawake, vijana na watu wenye ulemavu
• Masharti na hatua za kuomba:  Kikundi kiwe na idadi ya watu 5 na kuendelea (Pia wana kikundi wawe na umri wa kuanzia miaka 18 na kuendelea kwa vikundi vya wananwake na wenye ulemavu , vijana ni kuanzia miaka 18-45), Kikundi kiwe kimesajiliwa na kupata cheti, kiwe na katiba, kiwe na shughuli (mradi), kiwe na akaunti ya benki iliyofunguliwa kwa jina la kikundi,wana kikundi wasiwe na ajira rasmi na kwa walemavu kuanzia mtu 1
 
vii. Idara ya Kilimo, Mifugo na uvuvi ;
• Mazao ya biashara na chakula :  85%
• Huduma za ugani kwa wakulima : 65%
• Huduma za mifugo (chanjo, tiba, usimamizi wa malisho) : 68%
• Ufugaji wa kisasa na uzalishaji wa mifugo : Ufugaji wa kisasa 24%
• Uvuvi na ufugaji wa samaki :
• Fursa za mikopo na vikundi vya wakulima/wafugaji :
viii. Idara ya Miundombinu,Maendeleo ya Vijijini na Mjini; Idara hii ina jukumu la kusimamia miradi mbali mbali ya maendeleo , Kuandaa makadirio ya gharama za ujenzi , Ukaguzi na utoaji wa vibali vya ujenzi wa majengo ya serikali,taasisi na watu binafsi. Mpaka sasa Idara inasimamia miradi 47 iliyopata fedha kutoka serikali kuu na kutoka kwa wahisani.
 
ix. Idara ya Utawala na Usimamizi wa rasili mali Watu;
Idara hii  ina jukumu la kusimamia masuala ya kiutawala na rasilimali watu. Kusimamia nidhamu za watumishi mahali pa kazi, kuhakikisha idadi ya watumishi waliopo inaendana na mahitaji ya Ofisi na shughuli nyingine za kiutawala. Mpaka sasa watumishi waliopo kwa kada mbali mbali ni 1921.
 
x. Kitengo cha  Udhibiti wa Taka Ngumu na Usafi wa mazingira; Kitengo huki kina jukumu la kudhibiti taka ngumu na kuuweka mji katika hali nzuri pia kusimamia uoteshaji wa vitalu vya miti pamoja na kusimamia upandaji miti katika taasisi za serikali, Shule za msingi na Sekondari. Mpaka sasa  jumla ya miche 260,000 imepandwa katika Taasisi mbali mbali kati ya lengo la kupanda miti 500,000 kwa mwaka.
 
xi. Kitengo cha Mali asili na Hifadhi ya Mazingira ; Kitengo hiki kina jukumu la kusimamia shughuli zote za mali asili ikijumuisha misitu, nyuki, wanyamapori na mazingira. Pia kutoa elimu kwa jamii juu ya uhifadhi endelevu wa rasili mali za misitu. Mpaka sasa Halmashauri ya wilaya ya Chemba ina Misitu vijiji 16 iliyohifadhiwa  pamoja na pori 1 la akiba swagaswaga, hifadhi za nyuki 4 katika vijiji vya (Jogolo, Baaba, Sanzawa na Mialo)
 
xii. Kitengo cha Michezo,Utamaduni na sanaa ; Kitengo hiki kina simamia masuala mbali mbali yahusuyo michezo,utamaduni na sanaa. Kuibua vipaji kutoka kwenye jamii na kuvilea. Kutoa elimu kwa jamii kuhusiana na umuhimu wa michezo ,Utunzaji wa utamaduni wa jamii.
 
xiii. Kitengo cha Uchaguzi ;
• Kuratibu shughuli zote zihusuzo uchaguzi (uchaguzi wa serikali za mitaa, uchaguzi mkuu na chaguzi ndogo zote zitakazo jitokeza baada ya uchaguzi kufanyika).
• Kuratibu mazoezi yote ya uboreshaji wa daftari la kudumu la wapiga kura kwa uchaguzi mkuu na Orodha ya wapiga kura kwa Uchaguzi wa serikali za mitaa
• Kumshauri Mkurugenzi juu ya maswala yote yahusuyo uchaguzi katika Halmashauri ili kuwezesha mazoezi hayo kufanyika kwa mujibu wa Sheria
 
xiv. Kitengo cha uhasibu: Kusimamia mapato ya ndani ya Halmashauri ambapo kwa kipindi miaka 2 mfulululizo Halmashauri imevuka lengo la kukusanya mapato yake ya ndani kwa 100% ambapo mwaka  2023/2024 - 110% na 2024/25 -117% na mpaka sasa halmashauri imekusanya mapato kwa 63% ya lengo la kukusanya 100% kwa mwaka huu.
 
xv. Kitengo cha Sheria: Kusimamia masuala mbali mbali ya kisheria yanayohusu Halmashauri ambapo jumla kesi 6  zinasimamiwa na kitengo cha Sheria
 
xvi. Kitengo cha Ukaguzi wa ndani: Kitengo hiki kina jukumu la kutathimini michakato ya kifedha, uendeshaji na usimamizi wa Halmashauri. Pia kupima udhibiti wa ndani, kutoa taarifa ya matokeo ya ukaguzi kwa uongozi (management) na kamati ya ukaguzi na kupendekeza uboreshaji wa utendaji kazi.
 
xvii. Kitengo cha Usimamizi wa Ununuzi: Kitengo hiki kina jukumu la kusimamia sheria ,kanunui na taratibu za ununuzi. Kusimamia mikataba yote ya utekelezaji wa miradi kati ya wazabuni na mafundi Halmashauri pamoja na ngazi za chini. Mpaka sasa kitengo kimefanikiwa kusimamia mikataba 47 ya miradi ya maendeleo inayoendelea kutekelezwa kwa mwaka huu wa fedha 2025/26.
 
xviii. Kitengo cha Tehama: Kitengo hiki kina jukumu la kusimamia mifumo yote inayotumika ndani ya Halmashauri,  baadhi ya mifumo hiyo TAUSI, GOTHOMIS, IFTMIS,SIS,e-UTENDAJI (PEPMIS na PlanRep).
 
xix. Kitengo cha Mawasiliano Serikalini: Kutoa taarifa kwa Umma kuhusu shughuli mbalimbali zinazotekelezwa na Halmashauri na Serikali kwa ujumla.
 
xx. Kitengo cha Ufuatiliaji na Tathimini: Kitengo hiki kina jukumu la kufuatilia na kufanya tathimini ya miradi ya maendeleo inayotekelezwa katika Halmashauri ili kuhakikisha miradi inakamilika kwa wakati na kwa ubora uliokusudiwa. Kwa sasa miradi inayoendelea kusimamiwa ni 47.
 
4. Fursa zilizopo katika Wilaya:
• Uwepo wa maeneo yaliyotengwa kwa ajili ya Uwekezaji katika Mji wa Chemba, Paranga na Kambi ya Nyasa
"""


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


# Use only the embedded taarifa snippet for AI answers (no runtime file dependency)
TAARIFA_TEXT: str = TAARIFA_MD_SNIPPET


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
        "kwa ufupi na kwa maneno ya binadamu. Tumia namba na majina kama yalivyo kwenye hati. "
        "Kama hati HAINA taarifa inayojibu swali hilo kabisa, jibu kwa neno moja tu: NO_ANSWER. "
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
    # Treat NO_ANSWER only when it is the whole response, to avoid false negatives
    if response_clean.upper() == NO_ANSWER_MARKER:
        return None, False
    return response_clean, True

