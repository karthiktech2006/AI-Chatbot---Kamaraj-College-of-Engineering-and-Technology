import re
import csv
from difflib import SequenceMatcher

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ChatLead, CallRequest


# ==========================================================
# ===================== CONSTANT DATA =======================
# ==========================================================
MAIN_MENU = [
    {"id": "about", "label": "About Us"},
    {"id": "why", "label": "Why Us?"},
    {"id": "placements", "label": "Placements"},
    {"id": "infrastructure", "label": "Infrastructure"},
    {"id": "contact", "label": "Contact Details"},
    {"id": "callback", "label": "Request Callback"},
]




# ==========================================================
# ======================== HOME =============================
# ==========================================================
def home(request):
    request.session.flush()
    request.session["screen"] = "intro"
    return render(request, "kcetchatbot/home.html")


# ==========================================================
# ==================== FUZZY DETECTION ======================
# ==========================================================
def fuzzy_match(word, keyword, threshold=0.82):
    return SequenceMatcher(None, word, keyword).ratio() >= threshold


def phrase_in_text_fuzzy(text, phrase, threshold=0.82):
    text_words = text.split()
    phrase_words = phrase.split()

    if phrase in text:
        return True

    if len(phrase_words) == 1:
        return any(fuzzy_match(word, phrase_words[0], threshold) for word in text_words)

    for i in range(len(text_words) - len(phrase_words) + 1):
        window = text_words[i:i + len(phrase_words)]
        if all(fuzzy_match(window[j], phrase_words[j], threshold) for j in range(len(phrase_words))):
            return True

    return False


def detect_menu_action(user_text):
    text = user_text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    keyword_map = {
        "highest_salary": {
            "keywords": [
                "highest salary", "highest package", "top package", "best package","high salary",
                "maximum salary", "max package"
            ],
            "priority": 10
        },
        "avg_salary": {
            "keywords": [
                "average salary", "avg salary", "average package", "mean salary",
                "salary details", "package details"
            ],
            "priority": 9
        },
        "recruiters": {
            "keywords": [
                "recruiter", "recruiters", "companies", "top companies",
                "prominent recruiters", "who recruits"
            ],
            "priority": 9
        },
        "companies": {
            "keywords": [
                "visited companies", "number of companies", "companies visited",
                "how many companies"
            ],
            "priority": 8
        },
        "placements": {
            "keywords": [
                "placement", "placements", "job", "jobs", "placement details",
                "placement info", "placement information"
            ],
            "priority": 8
        },
        "boys_hostel": {
            "keywords": [
                "boys hostel", "gents hostel", "mens hostel", "male hostel"
            ],
            "priority": 10
        },
        "girls_hostel": {
            "keywords": [
                "girls hostel", "ladies hostel", "womens hostel", "female hostel"
            ],
            "priority": 10
        },
        "hostel": {
            "keywords": [
                "hostel", "accommodation", "stay", "room facility", "hostel details"
            ],
            "priority": 9
        },
        "academic_facilities": {
            "keywords": [
                "academic facilities", "classroom", "classrooms", "lab", "labs",
                "apple lab", "smart classroom", "academic infrastructure"
            ],
            "priority": 8
        },
        "library": {
            "keywords": [
                "library", "books", "journals", "digital library", "library details"
            ],
            "priority": 9
        },
        "sports": {
            "keywords": [
                "sports", "gym", "football", "basketball", "kabaddi",
                "kho kho", "games", "playground"
            ],
            "priority": 8
        },
        "safety": {
            "keywords": [
                "safety", "security", "cctv", "accessible", "accessibility",
                "safe campus"
            ],
            "priority": 8
        },
        "infrastructure": {
            "keywords": [
                "infrastructure", "facilities", "facility", "campus facilities",
                "college facilities"
            ],
            "priority": 6
        },
        "contact": {
            "keywords": [
                "contact", "phone", "email", "address", "location",
                "contact details", "phone number"
            ],
            "priority": 8
        },
        "callback": {
            "keywords": [
                "callback", "call me", "request callback", "counselor",
                "counselling", "please call", "need a call", "can you call"
            ],
            "priority": 9
        },
        "why": {
            "keywords": [
                "why us", "why choose", "reason to join", "why kcet", "give me the reason why i choose this college",
                 "why should i join", "benefits"
            ],
            "priority": 5
        },
        "about": {
            "keywords": [
                "about", "about kcet", "college history", "history", "tell me about kcet"
            ],
            "priority": 2
        }
    }

    scores = {}

    for action, config in keyword_map.items():
        score = 0
        priority = config["priority"]

        for keyword in config["keywords"]:
            if phrase_in_text_fuzzy(text, keyword):
                score += len(keyword.split()) + priority

        if score > 0:
            scores[action] = score

    if not scores:
        return None

    return max(scores, key=scores.get)


# ==========================================================
# ======================= CHAT API ==========================
# ==========================================================
@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    screen = request.session.get("screen", "intro")
    message = request.POST.get("message", "").strip()
    action = request.POST.get("action", "").strip()

    # ---------------- INTRO ----------------
    if screen == "intro":
        request.session.flush()
        request.session["screen"] = "get_name"
        return JsonResponse({
            "bot": "Hello! Welcome to KCET College Virtual Assistant.\n\nMay I know your name?"
        })

    # ---------------- GET NAME ----------------
    if screen == "get_name":
        name = message.strip()

        if not name:
            return JsonResponse({
                "bot": "Hello! Welcome to KCET College Virtual Assistant.\n\nMay I know your name?"
            })

        if re.match(r"^[A-Za-z ]{2,}$", name):
            request.session["name"] = name
            request.session["screen"] = "main_menu"

            ChatLead.objects.create(name=name)

            return JsonResponse({
                "bot": f"Nice to meet you, {name}!\n\nHow can I help you today?",
                "menu": MAIN_MENU
            })

        return JsonResponse({
            "bot": "Please enter a valid name (minimum 2 letters, only alphabets)."
        })

    # ---------------- CALLBACK MOBILE ----------------
    if screen == "callback_mobile":
        mobile = message.strip()

        if re.match(r"^[6-9]\d{9}$", mobile):
            request.session["mobile"] = mobile

            CallRequest.objects.create(
                name=request.session.get("name", ""),
                mobile=mobile
            )

            request.session["screen"] = "main_menu"

            return JsonResponse({
                "bot": f"""Thank you, {request.session.get('name', 'User')}

Our Team will call you shortly. &#9742;

If you'd like to explore more information, click below.""",
                "menu": [
                    {"id": "know_more", "label": "Know More"},
                    {"id": "back_main", "label": "← Back to Menu"}
                ]
            })

        return JsonResponse({
            "bot": "Please enter a valid 10-digit mobile number."
        })

    # ---------------- MAIN MENU ----------------
    if screen == "main_menu":
        if not action and message:
            detected_action = detect_menu_action(message)

            if detected_action:
                action = detected_action
            else:
                return JsonResponse({
                    "bot": "Sorry, I couldn’t understand that. Please choose an option below.",
                    "menu": MAIN_MENU
                })

        # ----- ABOUT US -----
        if action == "about":
            return JsonResponse({
                "bot": """&#127970; About KCET College

Our College was established in the year 1998. It is promoted and supported by
Virudhunagar Hindu Nadars' Devasthanam, various Hindu Nadars' Mahamai Tharappus
in Virudhunagar and other places and educational institutions of Virudhunagar.

The management of the institution consists of the elected members of various
Mahamai Tharappus and ex-officio members of various educational institutions
of Virudhunagar. The office bearers - the President, Vice-President, Secretary,
Joint Secretary and Treasurer - are elected by the managing board members.

Our College is ideally located on the homeland of Karmaveerar
"Bharat Ratna" K. Kamaraj and our institution is one of
Virudhunagar's most recognisable landmarks.

Our beloved Patron Thiru A.S.K.A.M. Nagarajan magnanimously donated ₹50 Lakhs
and our Founder Secretary Er. S.P.G.C. Srimurugan donated 25 acres of land
for the progress of our college.

Our institution continues to grow with sustained progress due to generous
contributions from Virudhunagar Devasthanam, Mahamai Tharappus and various
Educational Institutions.""",
                "menu": [{"id": "back_main", "label": "← Back to Menu"}],
                "url": "/about"
            })

        # ----- WHY US -----
        if action == "why":
            return JsonResponse({
                "bot": """
Kamaraj College of Engineering and Technology (KCET) in Virudhunagar is a top choice due to its autonomous status, offering flexible, industry-relevant curriculum, and a strong placement record (approx. 100% placement rate) with packages up to 13 LPA. It features excellent infrastructure, including Wi-Fi, modern labs (e.g., Apple lab), and dedicated, experienced faculty.

Key Reasons to Choose KCET:
Academic Autonomy & Quality: As an autonomous institution, it offers specialized, updated curriculum with 17+ programs across UG/PG/PhD levels.

Strong Placement & Industry Ties: The college has a dedicated placement cell, with major recruiters like CTS, TCS, and others, often achieving over 100% placement for eligible students.

Excellent Infrastructure & Research Focus: The 47-acre campus includes well-equipped labs, 24/7 Wi-Fi, and a focus on research, including partnerships for AI and UI/UX.

Holistic Development: The college provides strong support for extracurriculars, including sports, having won zonal championships.

Supportive Faculty: Faculty members are described as highly qualified and supportive, contributing to better student growth.
""",
                "menu": [{"id": "back_main", "label": "← Back to Menu"}]
            })

        # ----- PLACEMENTS -----
        if action == "placements":
            return JsonResponse({
                "bot": "What placement information would you like to see?",
                "url": "https://kamarajengg.edu.in/tdpc",
                "menu": [
                    {"id": "recruiters", "label": "Our Prominent Recruiters"},
                    {"id": "avg_salary", "label": "Average Salary"},
                    {"id": "highest_salary", "label": "Highest Salary"},
                    {"id": "companies", "label": "No. of Companies Visited"},
                    {"id": "back_main", "label": "← Back to Menu"}
                ]
            })

        # ----- RECRUITERS -----
        if action == "recruiters":
            companies = [
                "TCS", "Infosys", "Wipro", "HCL", "Accenture", "Cognizant", "Zoho",
                "Tech Mahindra", "Hexaware", "UST", "USTS", "Zifo", "Kaar",
                "Data Patterns", "Centizen", "Movate", "Aptean", "E-con Systems",
                "Relevantz", "Xmplar", "CSCS", "Tessolve", "SureSoft Systems",
                "Finsurge", "Sensedge", "Pruvity", "Propel", "Unifo", "Quintessence",
                "Avantor", "Episource", "Clustrex", "Lucid Imaging", "SmartDV",
                "Amphisoft", "RND DIGITAL LABS", "Solartis", "Vinsinfo",
                "TECH7 Automation Systems", "SELVA LLC", "DWB Tech Solutions LLP",
                "Pranion", "Raini Industries", "Neeyamo", "AID Novacis Digital",
                "REBARD&D", "JASMIN INFOTECH", "CHAIN SYS", "Youngshin",
                "Caliber Interconnect Solutions"
            ]

            return JsonResponse({
                "bot": "&#127970; Our Prominent Recruiters\n\n" + "\n".join(f"• {c}" for c in companies),
                "menu": [{"id": "placements", "label": "← Back"}]
            })

        # ----- AVERAGE SALARY -----
        if action == "avg_salary":
            return JsonResponse({
                "bot": """&#128176; Total Offers: 354
Total Unique Offers: 291

Average Salary Package ₹4.5 LPA (2025-26)

&#9679 ADS: ₹4.26 LPA
&#9679 BIO-TECH: ₹2.73 LPA
&#9679 CSE: ₹5.2 LPA
&#9679 ECE: ₹3 LPA
&#9679 EEE: ₹3.03 LPA
&#9679 IT: ₹3.60 LPA
&#9679 MECH: ₹3.21 LPA
&#9679 MTRE: ₹3.25 LPA
&#9679 CIVIL: ₹2.40 LPA""",
                "menu": [{"id": "placements", "label": "← Back"}]
            })

        # ----- HIGHEST SALARY -----
        if action == "highest_salary":
            return JsonResponse({
                "bot": """&#128176 &#128640;Total Offers: 354
Total Unique Offers: 291

Highest Salary Package (2025-26) ₹13 LPA

&#9679 ADS     : ₹13 LPA
&#9679 BIO-TECH: ₹3.6 LPA
&#9679 CSE     : ₹8 LPA
&#9679 ECE     : ₹4.2 LPA
&#9679 EEE     : ₹4.2 LPA
&#9679 IT      : ₹6.5 LPA
&#9679 MECH    : ₹4.5 LPA
&#9679 MTRE    : ₹8 LPA
&#9679 CIVIL   : ₹3 LPA""",
                "menu": [{"id": "placements", "label": "← Back"}]
            })

        # ----- COMPANIES VISITED -----
        if action == "companies":
            return JsonResponse({
                "bot": """&#127970; Companies Visited

100+ Companies

&#9679 IT & Software: 65
&#9679 Core Engineering: 28
&#9679 Banking & Finance: 12
&#9679 Consulting: 8
&#9679 Others: 7""",
                "menu": [{"id": "placements", "label": "← Back"}]
            })

        # ----- INFRASTRUCTURE -----
        if action == "infrastructure":
            return JsonResponse({
                "bot": "Please choose a facility:",
                "menu": [
                    {"id": "hostel", "label": "Hostel Facilities"},
                    {"id": "academic_facilities", "label": "Academic Facilities"},
                    {"id": "library", "label": "Library"},
                    {"id": "sports", "label": "Sports & Recreation"},
                    {"id": "safety", "label": "Safety & Accessibility"},
                    {"id": "back_main", "label": "← Back to Menu"}
                ],
                "url": "https://kamarajengg.edu.in/infra"
            })

        # ----- ACADEMIC FACILITIES -----
        if action == "academic_facilities":
            return JsonResponse({
                "bot": """&#127891; Academic Facilities

&#9679 Laboratories & Workshops: Well-equipped labs for all engineering departments, regularly calibrated by experts.
&#9679 Digital Classrooms: Smart classrooms fitted with projectors and modern teaching aids.
&#9679 Library: Digitalized library system with access to online courses and resources, open during holidays.
&#9679 Audio & Video Hub: Specialized space for creating high-quality content, video conferencing, and virtual learning.
&#9679 Research Centers: Dedicated centers focusing on research, publications, and development.
&#9679 Center of Excellence: Offers specialized programs tailored to industry needs.""",
                "menu": [{"id": "infrastructure", "label": "← Back"}],
                "url": "https://kamarajengg.edu.in/facilities"
            })

        # ----- LIBRARY -----
        if action == "library":
            return JsonResponse({
                "bot": """&#128218; Library

The Central Library at Kamaraj College of Engineering and Technology (KCET) serves as a key academic resource center, offering a robust collection of, e-books, journals, and technical project reports. It operates from 9:00 a.m. to 6:00 p.m., supporting students and faculty with modern digital resources, including DELNET, N-List, and NDLI access.

Key Features and Resources:
&#9679 Collection: Extensive print materials, including textbooks, reference books, and technical journals.
&#9679 Digital Library: Provides access to e-journals and e-books, with specialized digital library systems to aid research.
&#9679 Working Hours: Open daily from 9:00 a.m. to 6:00 p.m..
&#9679 Loan Policy: Students can borrow up to five books for a period of fifteen days, while faculty and Ph.D. scholars are eligible for twelve books.
&#9679 Infrastructure: Well-equipped with a modern, computerized environment, including internet access to support research and learning.
&#9679 Services: Includes an online catalogue, access to Anna University e-resource consortium, and dedicated study spaces.
&#9679 The library is designed to support the academic and research needs of the institution's user community.

                """,
                "menu": [{"id": "infrastructure", "label": "← Back"}],
                "url": "https://kamarajengg.edu.in/libraryfacilities"
            })

        # ----- SPORTS -----
        if action == "sports":
            return JsonResponse({
                "bot": """&#127941; Sports

Kamaraj College of Engineering and Technology (KCET)
offers robust sports and recreational facilities, featuring extensive indoor/outdoor courts (cricket, football, tennis, gym, yoga), mandatory weekly physical education, and active inter-collegiate participation

It promotes holistic development through tournaments, specialized training, and various clubs, fostering team spirit and fitness.
Here are the key details regarding sports and recreation at KCET:

&#9679 Outdoor Games: Cricket field and nets, football, hockey, handball, volleyball, basketball, Kabaddi, kho-kho, and lawn tennis courts.
&#9679 Indoor Games: Table tennis, badminton courts (including hostel facilities), chess, carrom, and specialized gyms with fitness/weight-training rooms.
&#9679 Fitness: Dedicated yoga and meditation halls.
""",
                "menu": [{"id": "infrastructure", "label": "← Back"}]
            })

        # ----- SAFETY -----
        if action == "safety":
            return JsonResponse({
                "bot": """&#128737; Safety & Accessibility
Here are the key details regarding safety and accessibility at KCET:

Safety & Security Measures

&#9679 Anti-Ragging & Discipline: The college maintains a strong Anti-Ragging Committee and a Discipline and Welfare Committee to ensure a safe atmosphere.
&#9679 Campus Rules: Strict guidelines are in place, including mandatory ID cards, restrictions on guest access during class hours, and prohibition of two-wheelers for students.
&#9679 Hostel Safety: Separate, clean, and hygienic hostels are provided for boys and girls.
&#9679 Cyber Security Focus: The institution emphasizes creating a secure digital environment and proactively identifying system vulnerabilities.
&#9679 General Order: Good maintenance of labs with necessary safety measures and AC facilities is reported.

Accessibility Features

&#9679 Barrier-Free Infrastructure: The campus is designed to be disabled-friendly.
&#9679 Physical Access: Includes wheelchair-accessible entrances, parking lots, and restrooms.
&#9679 Ramp Facilities: Ramps are installed in all blocks to ensure ease of movement for disabled persons.
""",
                "menu": [{"id": "infrastructure", "label": "← Back"}]
            })

        # ----- HOSTEL -----
        if action == "hostel":
            return JsonResponse({
                "bot": "Select hostel type:",
                "menu": [
                    {"id": "boys_hostel", "label": "Boys Hostel"},
                    {"id": "girls_hostel", "label": "Girls Hostel"},
                    {"id": "back_infra", "label": "← Back"}
                ]
            })

        # ----- BOYS HOSTEL -----
        if action == "boys_hostel":
            return JsonResponse({
                "bot": """&#127968; Boys Hostel

&#9679 Each room is provided with ceiling fans, tables, chairs, cupboards, writing pad etc...
&#9679 Bathrooms are kept clean and are fitted with geysers.
&#9679 Other recreational facilities like indoor games.
&#9679 A well equipped gymnasium is also available.
&#9679 Each block has purifier which provides cool ,hot ,normal water for all the seasons.
&#9679 Medical facilities are also provided for the students along with ambulance facilities.
&#9679 24*7 Wi-Fi Internet Connection.
&#9679 Tuck Shop.
&#9679 CCTV Surveillance Camera.
&#9679 News Paper Reading Room.
&#9679 Residential Doctor to render service to our Hostel students.
&#9679 Computer room with 16 systems with 45 Mbps Internet connection.
""",
                "menu": [{"id": "hostel", "label": "← Back"}],
                "url": "https://kamarajengg.edu.in/boys"
            })

        # ----- GIRLS HOSTEL -----
        if action == "girls_hostel":
            return JsonResponse({
                "bot": """&#127968; Girls Hostel

Hostel facilities are earmarked in such a way, that the students can feel homely and pursue their studies in serene atmosphere.

The various infrastructure facilities available in the hostel are:

&#9679 Modern Kitchen
&#9679 Dining Hall
&#9679 Reading room with news papers, periodicals and magazines
&#9679 Television
&#9679 Tuck shop and Telephone Booth
&#9679 Gymnasium
&#9679 Shuttle Court
&#9679 Hostel 24/7 Wi-Fi
&#9679 Uninterrupted Power Supply
&#9679 Public Addressing system to announce Reminders & Circulars
&#9679 Eco friendly garden
&#9679 Parents' waiting Hall
&#9679 Treatment of organic Waste materials using Incinerator""",
                "menu": [{"id": "hostel", "label": "← Back"}],
                "url": "https://kamarajengg.edu.in/girls"
            })

        # ----- CONTACT -----
        if action == "contact":
            return JsonResponse({
                "bot": """&#128205; Key Contact Details & Info

&#127970; Address:
S.P.G. Chidambara Nadar - C. Nagammal Campus,
S.P.G.C. Nagar, K. Vellakulam - 625 701
(Near Virudhunagar), Tamil Nadu

&#9993; General Email:
mail@kamarajengg.edu.in

&#9742; Phone Numbers:
(+91) 4549-278791
(+91) 4549-278171
+91 94885 24988
+91 94435 44988

&#128221; Placement Cell Email:
placement@kamarajengg.edu.in

&#128241; Placement Phone:
+91 94423 25078
+91 79047 17255

&#128221; Counselling Code: 4959""",
                "menu": [{"id": "back_main", "label": "← Back to Menu"}],
                "url": "https://kamarajengg.edu.in/captcha"
            })

        # ----- CALLBACK -----
        if action == "callback":
            request.session["screen"] = "callback_mobile"
            return JsonResponse({
                "bot": f"Sure, {request.session.get('name', 'there')}! Please enter your mobile number."
            })

        # ----- KNOW MORE -----
        if action == "know_more":
            return JsonResponse({
                "bot": "Please choose an option to continue exploring KCET.",
                "menu": MAIN_MENU
            })

        # ----- BACK ACTIONS -----
        if action in ["back_main", "back_infra"]:
            request.session["screen"] = "main_menu"
            return JsonResponse({
                "bot": "How can I help you?",
                "menu": MAIN_MENU
            })

        # ----- DEFAULT -----
        return JsonResponse({
            "bot": "Please use the menu buttons below &#128071;",
            "menu": MAIN_MENU
        })

    # ---------------- FALLBACK ----------------
    return JsonResponse({
        "bot": "Something went wrong. Please refresh the page and try again."
    })