import os
import re
import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

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

TAARIFA_MD_SNIPPET2 = """
1. Ngazi ya Uongozi (Uongozi wa sasa)
• Mkuu wa Wilaya (District Commissioner – DC):Mhe. Halima Okash (pia anajulikana kama Halima Okas au @okash_halima). Amekuwa akionekana katika shughuli rasmi hadi Februari 2026 (pamoja na usimamizi wa uchaguzi na shughuli za usalama). Anasimamia utekelezaji wa sera za serikali na amani wilayani.
• Katibu Tawala wa Wilaya (District Administrative Secretary – DAS):Bi. Sarah Ngalingasi. Anashughulikia masuala ya utawala na usimamizi wa mikutano wa halmashauri (k.m. kusoma matokeo ya uchaguzi wa mwenyekiti wa halmashauri hivi karibuni).
• Mkurugenzi Mtendaji wa Halmashauri (District Executive Director – DED):Bw. Hassan Juma Mnyikah (pia anaitwa Hassan Mnyika au Ndg. Hassan Mnyikah). Ndiye msimamizi mkuu wa utendaji wa halmashauri. Hivi karibuni (Januari 29, 2026) amezindua kampeni ya upandaji miti, na Desemba 2025 alitoa salamu za Krismasi.
• Mwenyekiti wa Halmashauri ya Wilaya:Bw. Raphael Lebba (kutokana na matangazo ya hivi karibuni ya shughuli za mafunzo na mikutano). (Kuna taarifa za awali za Erasto Mpete kurejea, lakini Raphael Lebba ndiye anayetajwa katika shughuli za sasa).
Wakurugenzi wa Idara (Heads of Departments): Halmashauri ina idara kuu kama Elimu, Afya, Kilimo, Mipango na Fedha, Ujenzi, Mazingira n.k. Majina ya wakurugenzi maalum hayajaorodheshwa wazi katika vyanzo vya sasa vya umma (wanasimamiwa moja kwa moja na DED). Unaweza kupata orodha kamili kwa kuwasiliana na ofisi ya DED.
Mawasiliano ya Ofisi Kuu ya Halmashauri:
• Sanduku la Posta: 830, Chemba.
• Simu: 026 236 0175 / Simu ya mkononi: 0765 980 765.
• Barua pepe: ded@chembadc.go.tz
• Tovuti rasmi: https://chembadc.go.tz/ (ina habari mpya, wasifu na matangazo).
Mkuu wa Mkoa (kwa muktadha): Mhe. Rosemary Senyamule (anashirikiana na uongozi wa wilaya katika miradi ya mkoa).
2. Taarifa Muhimu za Wilaya ya Chemba
• Jiografia na Mahali: Wilaya ipo katikati mwa Tanzania, Mkoa wa Dodoma. Imeanzishwa rasmi Julai 2013 baada ya kugawanywa kutoka Wilaya ya Kondoa. Makao makuu yako kijiji cha Chemba. Inapakana na: Wilaya ya Kondoa (kaskazini), Mkoa wa Manyara (mashariki), Wilaya ya Chamwino na Bahi (kusini), na Mkoa wa Singida (magharibi). Umbali: Km 140 kaskazini mwa Dodoma mjini, na km 40 kusini mwa

Kondoa. Barabara kuu T5 (Dodoma – Babati) inapita wilayani. Usafiri wa ndani mara nyingi hutumia punda. Eneo ni la nusu-kame (semi-arid), lenye changamoto za ukame na uhifadhi wa mazingira.
• Ugatuzi wa Utawala:
o Vitengo vya utawala (Divisions): 4 (Chemba, Kwamtoro, Mondo na nyingine). o Kata (Wards): 26.
o Vijiji: 114.
o Vitongoji (Hamlets): 494. (Idadi iliongezeka kutoka miaka ya awali).
• Idadi ya Wakazi (Population):
o Sensa ya Taifa 2022: 339,333 (wanaume 170,837; wanawake 168,496; wastani
wa kaya 4.5).
o Sensa ya 2012: 235,711 (uongozi wa wastani wa ukuaji ~1.7% kwa mwaka).
Wilaya ina jimbo moja la uchaguzi (Chemba).
• Uchumi na Shughuli Kuu: Kilimo (mazao ya nafaka, mboga) na ufugaji ndio mhimili
mkuu wa uchumi. Kuna migogoro ya mara kwa mara kati ya wafugaji na wakulima kuhusu ardhi (hasa maeneo ya Kwamtoro). Serikali inahamasisha uhifadhi wa misitu na upandaji miti (kampeni inaendelea). Miradi mingine: Ujenzi wa vituo vya afya, shule, na barabara. Wilaya inashiriki katika maonesho ya kilimo na uvuvi wa mkoa.
• Huduma za Msingi na Maendeleo:
o Afya: Vituo vya afya na zahanati (takwimu za kina zinapatikana ofisini).
o Elimu: Shule za msingi na sekondari; DED amewahamasisha walimu mara kwa
mara.
o Mazingira: Kampeni za kutunza misitu na kupanda miti zinaendelea (mfano
Januari 2026). Wilaya inashiriki kikamilifu katika uchaguzi wa serikali za mitaa
na taifa (Oktoba 2025 ilisimamiwa vizuri na DC).
• Changamoto Kuuzo: Ukame, migogoro ya ardhi, na uhifadhi wa wanyamapori (k.m.
eneo la Swagaswaga Game Reserve lililokaribu). Serikali inafanya utafiti na hatua za kushughulikia (k.m. agizo la Balozi Dkt. Emmanuel Nchimbi Februari 2026).
"""


TAARIFA_MD_SNIPPET3 = """
1.1 Utangulizi
1.1.2 Eneo la Kiutawala
Wilaya ya Chemba ni miongoni mwa Wilaya 7 za Mkoa wa Dodoma yenye ukubwa wa kilomita za mraba 7,653 ambalo ni sawa na asilimia 18.5 ya eneo lote la Mkoa wa Dodoma. Wilaya ya Chemba kwa kulinganisha na Wilaya zingine za ndani ya Mkoa wa Dodoma ni changa ambayo imeanza mwezi Julai 2012 baada ya Tangazo la Mhehimiwa Rais wa Jamhuri ya Muungano wa Tanzania Dkt. Jakaya Mrisho Kikwete. Wilaya ipo umbali wa Kilometa 110 kutoka Dodoma mjini ambapo ndio Makao Makuu ya Mkoa na Nchi yetu, katika Latitude 4°12’ mpaka 5°38’ kusini na  longitudo 35°06’ mpaka 36°02’ Mashariki. Wilaya ya Chemba ina jimbo moja (01) la uchaguzi ambayo ni Chemba, Halmashauri moja (01) ya Wilaya Chemba. Tarafa nne (4) ambazo ni Goima, Mondo, Farkwa na Kwamtoro, Kata ishirini na sita (26) ambazo ni Chemba, Kidoka, Soya, Chandama, Kimaha, Mrijo, Songolo, Msaada, Goima, Mondo, Paranga, Churuku, Jangalo, Dalai, Farkwa, Makorongo, Gwandi, Tumbakose, Babayu, Kwamtoro, Lahoda, Lalta, Ovada, Kinyamsindo, Sanzawa na Mpendo. Vijiji mia moja kumi na nne (114) na Vitongoji mia nne themanini na nane (488).

1.1.3 Uongozi
Wilaya ya Chemba inaongozwa na Mkuu wa Wilaya anaitwa Halima Okash, Mkurugenzi Mtendaji wa Halmashauri Hassan Mnyika na Mbunge wa Jimbo ni Kunti Majala.

1.1.4 Idadi ya watu
Kwa mujibu wa Sensa ya watu na Makazi ya mwaka 2022, Wilaya ya Chemba ina jumla ya watu laki tatu thelethini na tisa elfu mia tatu thelathini na tatu (339,333), kati yao laki moja na elfu sabini mia nane thelathini na saba (170,837) ni wanaume na laki moja sitini na nane elfu mia nne tisini na sita (168,496) ni wanawake.

1.1.5 Jiografia na mipaka ya Wilaya
Wilaya ya Chemba kwa upande wa kaskazini imepakana na Wilaya ya Kondoa, Mashariki imepakana na Wilaya ya Kiteto, Kusini imepakana na Wilaya ya Bahi, Kusini Mashariki imepakana na Wilaya ya Chamwino, Magharibi imepakana na Wilaya ya Manyoni na Wilaya ya Singida na Kaskazini Magharibi imepakana na Wilaya ya Hanang.

1.1.6 Hali ya Kisiasa
Hali ya kisiasa kwa ujumla katika Wilaya ya Chemba ni shwari. Kwa mujibu wa Uchaguzi Mkuu wa Oktoba, 2025. Chama Cha Mapinduzi (CCM) kimeshinda kwa asilimia 99.6 kwa Kiti cha Urais na asilimia 96.5 kwa kiti cha Mbunge na madiwani wote wa Kata wanatokana na Chama Cha Mapinduzi (CCM). Aidha vyama vyote vya kisiasa vinaendelea na shughuli zake za kawaida za kila siku ikiwa ni pamoja na vikao mbalimbali vya Vyama, vikao vya Madiwani, ziara za Mbunge kwa maeneo mbalimbali ndani ya jimbo na ukaguzi wa miradi ya maendeleo. Aidha, vyama vyote vya kisiasa vinashirikiana kwa ukaribu na Serikali, katika mustakabali wa Maendeleo ya Wilaya.

1.1.7 Uchumi wa Wilaya
Uchumi wa Wilaya hii hutegemea zaidi kilimo na mifugo. Wakazi wote wa wilaya hii hupata pato lao kutokana na shughuli za kilimo na ufugaji, hivyo mapato katika Wilaya hii hutegemea zaidi sekta hizo.

1.1.8 Hali ya Hewa
Wilaya ya Chemba ina mwinuko wa Mita 1,200 hadi 1,500 kutoka usawa wa bahari. Wilaya ina wastani wa nyuzi joto 15–30°C. Mvua ni za msimu mmoja kwa mwaka ambazo ni za wastani wa kiasi cha Milimita 500–800 ambazo hunyesha kuanzia mwezi Desemba hadi Machi/Aprili.

1.1.9 Dira
Kuwa Wilaya yenye utawala bora inayotoa huduma zenye ubora wa hali ya juu, inayochochea ukuaji endelevu wa uchumi na maendeleo jumuishi kwa wakazi wote.

1.1.20 Dhima
Kutengeneza mazingira wezeshi ya Maendeleo ili kutoa huduma bora kwa wananchi na kuondoa umaskini.

2.1.1 Muhtasari wa utekelezaji wa Shughuli za Maendeleo
Wilaya ya Chemba inatekeleza shughuli zake kwa kuzingatia maelekezo na ahadi zilizomo katika Ilani ya Uchaguzi ya Chama Cha Mapinduzi (CCM) ya Mwaka 2025–2030, ambayo imegusa mambo makubwa yafuatayo:-
I. Kuimarisha Uchumi
II. Kuboresha maisha ya watu na ustawi wa jamii
III. Kuwawezesha wananchi kuongeza kipato
IV. Kuimarisha Miundombinu ya Kisasa ya Usafiri na Usafirishaji
V. Kulinda na kuimarisha amani, utulivu na usalama wa nchi

2.1: Wilaya kupitia Halmashauri imetekeleza majukumu yake kupitia Idara na vitengo vyake ambavyo ni; Idara ya Mipango na Uratibu, Idara ya Elimu Msingi na Sekondari, Idara ya Maendeleo ya Jamii, Idara ya Utawala na Utumishi, Idara ya Afya na Ustawi wa Jamii, Idara ya Ardhi, Idara ya Elimu Msingi, Idara ya Kilimo, Mifugo na Uvuvi, Idara ya Viwanda, Biashara na Uwekezaji, Idara ya Fedha, Kitengo cha Usimamizi wa Taka na Usafi wa Mazingira, Kitengo cha Maliasili na Hifadhi ya Mazingira, Kitengo cha TEHAMA, Kitengo cha Manunuzi na Kitengo cha Sheria.

Kupitia Serikali ya awamu ya sita inayoongozwa na Mheshimiwa Dkt. Samia Suluhu Hassan, Rais wa Jamhuri ya Muungano wa Tanzania jumla ya Shilingi 9,892,273,726.75 kwa kipindi cha Mwaka 2025/26 zimetolewa katika Wilaya ya Chemba kwa ajili ya kuwezesha utekelezaji wa miradi mbalimbali. Fedha hizi zimeelekezwa katika Halmashauri, TANESCO, TARURA, na RUWASA. Utekelezaji wa huu umezingatia Dira ya Taifa ya Maendeleo ya Mwaka 2025, Mpango wa tatu wa maendeleo wa Taifa 2021/22 – 2025/26, Malengo ya Maendeleo Endelevu (SDGs) na maelekezo ya Viongozi wa Kitaifa. Katika kipindi chote Wilaya imeendelea kuimarisha utawala bora, miundombinu ya barabara na umeme, huduma za kiuchumi na kijamii pamoja na kuhamasisha uwekezaji.

2.1.2 Elimu ya Msingi
Wilaya ya Chemba ina jumla ya shule 118, kati ya hizo shule 113 zinamilikiwa na Serikali na shule 5 zinamilikiwa na watu/ taasisi binafsi. Shule hizo zina walimu 878 (Me 565, Ke 313), na wanafunzi wa darasa la Awali hadi la saba ni 74,818.

2.1.3 Elimu Sekondari
Wilaya ya Chemba ina jumla ya shule 31 za Sekondari, ambapo shule 1 inamilikiwa na Kanisa la KKT na shule 30 zinamilikiwa na serikali. Kati ya hizo shule 3 ni za kidato cha Kwanza hadi cha Sita ambazo ni Msakwalo, Mondo na Soya. Mafanikio yaliyopatikana kutokana na utekelezaji huu katika sekta ya elimu ni ujenzi wa vyumba vya madarasa ambao umesaidia kupunguza msongamano wa wanafunzi madarasani na kuhakikisha wanafunzi wote waliofaulu darasa la saba Mwaka 2025 wanapata nafasi ya kujiunga na kidato cha kwanza Mwaka 2026, ujenzi wa shule mpya za msingi na sekondari ambao umesaidia kupunguza umbali wa kufuata huduma za elimu.

2.1.4 Sekta ya Afya
Wilaya ya Chemba ina jumla ya vituo vya kutolea huduma za afya 53, kati ya vituo hivyo 50 vinamilikiwa na Serikali na vituo 3 vinamilikiwa na watu na mashirika ya dini. Kati ya hivyo 1 ni Hospitali ya Wilaya, 6 ni vituo vya afya na 43 ni zahanati. Vituo hivi vinahudumiwa na watumishi wapatao 254 wa serikali wa kada mbalimbali na watumishi 23 wanaofanya kazi chini ya mashirika yasiyo ya kiserikali. Katika sekta ya afya, ujenzi wa zahanati, ujenzi wa vituo vya afya pamoja na ununuzi wa dawa na vifaa tiba umesaidia kuboresha huduma za afya katika Wilaya na kupunguza vifo vya watoto na akina mama wajawazito.

Huduma zinazopatikana kwenye Hospitali ya Wilaya ya Chemba:
• Huduma za wagonjwa wa nje
• Upasuaji mdogo
• Upasuaji mkubwa
• Huduma ya kinywa na meno
• Huduma ya macho
• Huduma ya wagonjwa wanaoishi na VVU/UKIMWI
• Huduma za kifua kikuu
• Huduma za maabara
• Huduma za Radiologia
• Huduma za mama wajawazito na watoto chini ya miaka mitano
• Huduma za kulaza wagonjwa
• Huduma za kuhifadhi maiti

Huduma zinazopatikana kwenye Vituo vya Afya:
• Huduma za matibabu ya wagonjwa wa nje
• Huduma za maabara
• Huduma za wanaoishi na virusi vya Ukimwi na kifua kikuu
• Huduma za mama na mtoto
• Huduma za macho
• Huduma za kuhifadhi maiti
• Huduma za upasuaji wa dharura kwa akina mama walioshindwa kujifungua kwa njia ya kawaida
• Huduma ya upasuaji mdogo

Huduma zinazopatikana kwenye Zahanati:
• Huduma za wagonjwa wa nje
• Huduma za mama na mtoto
• Huduma za kuzalisha akina mama wajawazito
• Huduma za uzazi wa mpango

2.1.5 Maliasili na Mazingira
Wilaya ya Chemba inatekeleza shughuli za Maliasili ikijumuisha misitu, nyuki, wanyamapori, malikale na mazingira kwa kutoa elimu kwa jamii juu ya uhifadhi na matumizi endelevu ya rasilimali za misitu, wanyamapori na nyuki; kutekeleza sera na sheria za misitu, nyuki, mazingira na wanyamapori; kutoa elimu juu ya kukabiliana na wanyama wakali na waharibifu; kudhibiti uvunaji na usafirishaji haramu wa mazao ya misitu; kutoa elimu juu ya ufugaji bora wa nyuki; kusimamia na kukusanya mapato yatokanayo na mazao ya maliasili; kupanda miti katika maeneo ya taasisi za serikali za kidini, mashirika yasiyo ya kiserikali, vikundi na watu binafsi; kusimamia maeneo ya utalii; kutoa elimu juu ya kukabiliana na athari za mabadiliko ya tabianchi pamoja na kutafuta suluhisho za changamoto mbalimbali zinazoikabili sekta ya maliasili.

2.1.6 Kilimo na Mifugo
Wakazi wengi wa Wilaya ya Chemba wanajishughulisha zaidi na sekta ya kilimo na mifugo kama shughuli kuu za kiuchumi. Eneo linalofaa kwa kilimo linakadiriwa kuwa na takribani hektare 480,000 na linalotumika kwa kilimo kwa sasa ni hektare 148,000 na idadi ya kaya zinazo jishughulisha na kilimo ni 75,050. Wananchi wa Chemba wanafuga mifugo ya kujiongezea kipato ambayo jumla yake ni 1,149,892.

Mazao yanayopatikana Chemba:
Mahindi, Alizeti, Ufuta, Mbaazi, Mpunga, Mtama, Ulezi, Dengu, Pamba, Choroko, Viazi vitamu na Mihogo.

Msimu wa Kilimo:
Novemba hadi Aprili.
- Novemba – Desemba: Mazao yanayolimwa ni Mahindi, Mtama, Uwele, Ulezi, Ufuta, Mbaazi, Pamba na Mpunga.
- Januari – Februari: Mazao yanayolimwa ni Alizeti, Viazi Vitamu, Mihogo na Choroko.
- Machi – Aprili: Mazao yanayolimwa ni Dengu tu.

Mifugo inayopatikana Chemba kwa mujibu wa sensa ya mifugo ya mwaka 2022 ni kama ifuatavyo:
• Ng'ombe – 530,999
• Mbuzi – 352,445
• Kondoo – 57,445
• Punda – 12,933
• Kuku – 386,094
• Bata – 118,234
• Mbwa – 32,943
• Paka – 612

1. Minada na tarehe zinazofanyika kwenye kata:
NA  KATA        TAREHE YA MNADA
1   SOYA        KILA JUMAPILI
2   GWANDI      14 NA 25 KILA MWEZI
3   LAHODA      16 KILA MWEZI
4   MPENDO      17 KILA MWEZI
5   SANZAWA     18 KILA MWEZI
6   KINYAMSINDO 19 KILA MWEZI
7   LALTA       20 KILA MWEZI
8   KWAMTORO    1 NA 21 KILA MWEZI
9   FARKWA      22 KILA MWEZI
10  MAKORONGO   2 NA 23 KILA MWEZI
11  BABAYU      24 KILA MWEZI
12  MONDO       12 KILA MWEZI
13  PARANGA     3 KILA MWEZI
14  KIDOKA      29 KILA MWEZI

2.1.7 Sekta ya Miundombinu ya Barabara (TARURA)
TARURA inasimamia miradi ya mtandao wa barabara wenye kilomita 979.83 kwa mijini na vijijini na ukaguzi wa madaraja. Katika kipindi cha mwaka 2025/2026 miradi 4 yenye thamani ya shilingi milioni 999.6 inaendelea kutekelezwa ikiwa na wastani wa 60% ya utekelezaji.

2.1.8 Sekta ya Miundombinu ya Maji (RUWASA)
Wilaya ya Chemba kwa mwaka wa fedha 2025/2026 Wakala wa Maji na Usafi wa Mazingira Vijijini (RUWASA) imetekeleza miradi 12 yenye gharama za TZS 2,546,091,813.9, na uimarishaji wa utoaji huduma ya maji ngazi ya jamii (CBWSO’s) katika Tarafa 4 za Wilaya ya Chemba. Katika utekelezaji wa miradi ya maji kwa mwaka wa fedha 2025/2026 Wilaya ya Chemba imeendelea kutekeleza miradi hii na iko katika hatua mbalimbali za utekelezaji; mingine iko hatua ya manunuzi na mingine iko hatua ya utekelezaji.

2.1.9 Sekta ya Nishati
TANESCO Wilaya ya Chemba inatoa huduma ya usambazaji wa umeme vijijini na mijini ambapo wananchi zaidi ya 23,300 wameunganishiwa umeme. Katika kipindi cha mwaka wa fedha 2025/26 imetekelezwa miradi ya thamani ya shilingi bilioni 48.2.

3.0.1 Fursa za uwekezaji
• Shamba la BBT katika eneo la Gwandi lenye ukubwa wa ekari 3,420
• Eneo la viwanda lenye ukubwa wa ekari 79.14 ambalo linapatikana Kitongoji cha Aliso Chemba mjini
• Ujenzi wa stendi ukikamilika kutakuwepo na vibanda zaidi ya 40 kwa ajili ya wafanyabiashara wa kati na wadogo
• Eneo la masoko lenye ukubwa wa ekari 15
• Uwepo wa minada 17 na magulio 32
• Huduma ya usafirishaji wa ndani na nje
• Eneo la uchimbaji madini aina ya quartz kata ya Mondo
• Uwekezaji wa majengo kwa ajili ya biashara
• Maeneo yaliyotengwa kwa ajili ya uwekezaji wa shule binafsi, ujenzi wa malls, hoteli, lodges, hospitali binafsi n.k.
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


# Use the embedded taarifa snippets for AI answers (no runtime file dependency)
TAARIFA_TEXT: str = (
    TAARIFA_MD_SNIPPET
    + "\n\n"
    + TAARIFA_MD_SNIPPET2
    + "\n\n"
    + TAARIFA_MD_SNIPPET3
)


CHEMBADC_URL = "https://chembadc.go.tz/"


_CHEMBADC_CACHE_TEXT: str = ""
_CHEMBADC_CACHE_TS: float | None = None
_CHEMBADC_CACHE_TTL_SECONDS = 3600  # 1 hour


def _fetch_chembadc_text(max_chars: int = 8000) -> str:
    """
    Fetch and aggregate text from multiple pages on the official Chemba DC website.
    - Crawls only within https://chembadc.go.tz/
    - Limits number of pages and total characters
    - Uses a short cache to avoid hitting the site on every question
    """
    global _CHEMBADC_CACHE_TEXT, _CHEMBADC_CACHE_TS

    now = time.time()
    if _CHEMBADC_CACHE_TS and _CHEMBADC_CACHE_TEXT and (now - _CHEMBADC_CACHE_TS) < _CHEMBADC_CACHE_TTL_SECONDS:
        logger.info("ChembaBot: using cached chembadc.go.tz text (len=%s)", len(_CHEMBADC_CACHE_TEXT))
        return _CHEMBADC_CACHE_TEXT[:max_chars]

    logger.info("ChembaBot: crawling official site %s", CHEMBADC_URL)
    root_netloc = urlparse(CHEMBADC_URL).netloc
    to_visit: List[str] = [CHEMBADC_URL]
    visited: set[str] = set()
    texts: List[str] = []
    total_len = 0
    max_pages = 8
    hard_char_limit = max_chars * 2  # fetch a bit more, then trim

    while to_visit and len(visited) < max_pages and total_len < hard_char_limit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        logger.info("ChembaBot: fetching %s", url)
        try:
            resp = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "ChembaBot/1.0 (+https://chembadc.go.tz/)"},
            )
            logger.info(
                "ChembaBot: %s status_code=%s length=%s",
                url,
                resp.status_code,
                len(resp.text or ""),
            )
            if resp.status_code != 200 or not resp.text:
                continue
            html = resp.text
            # Collect internal links for further crawling (same domain only)
            for href in re.findall(r'href=["\']([^"\']+)["\']', html):
                full = urljoin(url, href)
                parsed = urlparse(full)
                if parsed.netloc != root_netloc:
                    continue
                # Normalise to avoid fragments and query-only duplicates
                clean = parsed._replace(fragment="", query="").geturl()
                if clean not in visited and clean not in to_visit:
                    to_visit.append(clean)

            # Remove script/style blocks
            html = re.sub(
                r"<(script|style)[^>]*>.*?</\1>",
                " ",
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            # Convert common line-break tags to newlines
            html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
            # Strip all remaining tags
            text = re.sub(r"<[^>]+>", " ", html)
            # Collapse whitespace
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            texts.append(text)
            total_len += len(text)
        except Exception as e:
            logger.exception("ChembaBot: error fetching %s: %s", url, e)
            continue

    combined = " ".join(texts).strip()
    if not combined:
        logger.warning("ChembaBot: no text extracted from chembadc.go.tz")
        return ""
    if len(combined) > max_chars:
        combined = combined[:max_chars]
    _CHEMBADC_CACHE_TEXT = combined
    _CHEMBADC_CACHE_TS = now
    logger.info(
        "ChembaBot: aggregated chembadc.go.tz text len=%s from pages=%s",
        len(combined),
        len(visited),
    )
    return combined


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

    # Kiswahili only.
    target_lang = "Kiswahili"

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
        # If the AI call fails, return a single, friendly fallback (Kiswahili only).
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
        logger.warning("ChembaBot: answer_freeform_question skipped (missing OPENAI_API_KEY or TAARIFA_TEXT)")
        return None, False

    target_lang = "Kiswahili"
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
    logger.info("ChembaBot: answer_freeform_question using taarifa.md only")
    response = _call_openai_chat(
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
    )
    if not response:
        logger.warning("ChembaBot: answer_freeform_question got no response from OpenAI")
        return None, False
    response_clean = response.strip()
    # Treat NO_ANSWER only when it is the whole response, to avoid false negatives
    if response_clean.upper() == NO_ANSWER_MARKER:
        logger.info("ChembaBot: answer_freeform_question → NO_ANSWER from taarifa.md")
        return None, False
    logger.info("ChembaBot: answer_freeform_question answered from taarifa.md")
    return response_clean, True


def answer_from_web_search(user_message: str, lang: str = "sw") -> Tuple[Optional[str], bool]:
    """
    Answer the user's free-form question with strict official-source priority:
    1) TAARIFA_MD_SNIPPET2 + TAARIFA_MD_SNIPPET (local official document)
    2) Chemba DC official website / other official knowledge (AI, instructed to use chembadc.go.tz and .go.tz only)

    Returns (answer_text, True) or (None, False) if no official answer is available.
    """
    user_message = (user_message or "").strip()
    if not user_message:
        return None, False
    if not OPENAI_API_KEY:
        logger.warning("ChembaBot: answer_from_web_search skipped (missing OPENAI_API_KEY)")
        return None, False

    logger.info("ChembaBot: free-form question received: %s", user_message)

    # Step 1: try to answer from local taarifa snippets only
    doc_answer, doc_answered = answer_freeform_question(user_message, lang)
    if doc_answered and doc_answer:
        logger.info("ChembaBot: answered from taarifa.md (no need for website)")
        return doc_answer, True
    logger.info("ChembaBot: taarifa.md had no answer, moving to official website / .go.tz logic")

    # Step 2: fall back to AI with instructions to rely on official sources only
    system_msg = (
        "You are a professional AI Assistant for Chemba District Council in Tanzania. "
        "Your role is to provide accurate, official, and helpful information to citizens. "
        "When answering any free-form user question, you MUST follow this strict information priority order:\n"
        "1) Primary source: the local Chemba document (taarifa.md snippets) which has already been checked.\n"
        "2) Secondary source: the official Chemba District website (https://chembadc.go.tz/).\n"
        "3) Tertiary source: other official Tanzanian Government websites with domain .go.tz.\n"
        "Rules: Always prioritise sources in this exact order. Do NOT use non-government websites. "
        "Do NOT generate speculative or unverified information. If information is not available from these official "
        "sources, reply with exactly: Information not available in official sources."
    )

    # Fetch official Chemba DC website content (secondary source)
    site_text = _fetch_chembadc_text()
    if site_text:
        logger.info("ChembaBot: including chembadc.go.tz text in OpenAI prompt")
        user_content = (
            "Hii ni nukuu ya ukurasa wa tovuti rasmi ya Halmashauri ya Wilaya ya Chemba "
            "(https://chembadc.go.tz/):\n\n"
            f"{site_text}\n\n"
            f"Swali la mtumiaji: {user_message}\n\n"
            "Jibu kwa Kiswahili, ukitumia tu taarifa kutoka kwenye hati ya taarifa au nukuu ya tovuti "
            "na maarifa yako ya tovuti rasmi za serikali (.go.tz). "
            "Ikiwa taarifa haipo katika vyanzo hivi rasmi, andika: Information not available in official sources."
        )
    else:
        # If website content is not reachable, fall back to using only model's knowledge of official sources
        logger.warning("ChembaBot: chembadc.go.tz content not available; using model knowledge of official sources only")
        user_content = user_message

    logger.info("ChembaBot: calling OpenAI with official-source rules")
    response = _call_openai_chat(
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content},
        ]
    )
    if not response:
        logger.warning("ChembaBot: OpenAI returned no response for free-form official-source question")
        return None, False
    response_clean = response.strip()
    if response_clean == "Information not available in official sources.":
        logger.info("ChembaBot: OpenAI reported 'Information not available in official sources.'")
        return None, False
    logger.info("ChembaBot: OpenAI answered from official sources")
    return response_clean, True

