"""Static CMS-style copy and design constants for the Walmart Careers mirror.

Nothing in here is runtime data: these are the marketing strings, benefit tiles
and map outlines that the real site serves from AEM. Runtime data (jobs, stores,
users, saved roles, applications) lives in SQLite only.
"""
from __future__ import annotations

from datetime import date

# The mirror is frozen against this date. Never call date.today() anywhere in
# the seed or bootstrap path.
MIRROR_REFERENCE_DATE = date(2026, 8, 31)

SITE_NAME = "Walmart Careers"
COPYRIGHT = "©2026 Walmart Inc."

# Job ids surfaced as "Trending roles" on the home page and the hiring page.
TRENDING_JOB_IDS = [
    "R-2463275",
    "R-2451180",
    "CP-9046-11101",
]

HERO_HEADLINE_1 = "Cashiers wanted."
HERO_HEADLINE_2 = "Next move, yours."
SEARCH_PLACEHOLDER = "Search by team, department, keyword"

CAROUSEL = [
    ("Jorden", "Associate Merchant", "Corporate Careers", "corporate", "home-tile-corporate.png"),
    ("Tatiana", "Software Engineer", "Tech Careers", "technology", "home-tile-tech.png"),
    ("Jamaily", "Club Manager", "Stores & Clubs Careers", "stores-and-clubs", "home-tile-stores.png"),
    ("Caleb", "Maintenance Tech", "Supply Chain Careers", "supply-chain-and-transportation", "home-tile-supply.png"),
    ("Yasinya", "Pharmacy Tech", "Healthcare Careers", "healthcare", "home-tile-health.png"),
]

VALUES = [
    ("Respect for the individual", "We listen, we support, and we help each other grow."),
    ("Service to the customer", "Everything starts with the people who shop with us."),
    ("Strive for excellence", "We look for a better way, every single day."),
    ("Act with integrity", "We do the right thing, especially when it is hard."),
]

BENEFIT_ROWS = [
    ("Financial perks", "Enjoy 401(k) matching and stock purchase plans.", "benefit-financial.svg"),
    ("Paid time off", "Take a break as needed for vacations, sick leave, holidays, parental leave and more.", "benefit-pto.svg"),
    ("Comprehensive health benefits", "Medical, dental, vision and wellness programs for you and your family.", "benefit-health.svg"),
    ("Wellbeing programs", "Access mental health resources and assistance programs for life's challenges.", "benefit-wellbeing.svg"),
    ("Career growth opportunities", "Training, leadership programs, and clear paths to advance.", "benefit-growth.svg"),
]

BENEFIT_FOOTNOTE = (
    "That's just the beginning. We offer more perks specific to your work location and role."
)

STAT_CARDS = [
    ("$1 billion", "invested in associate career training and development"),
    ("75%", "of salaried managers began as hourly associates"),
    ("300,000", "associates have earned a 10+ year badge"),
    ("120,000", "U.S. associates have participated in Live Better U"),
]

DAY_IN_THE_LIFE = [
    ("Store Coach", "Day in the life", "life-associates.jpg"),
    ("Optician", "Day in the life", "life-8th-plate.jpg"),
    ("Store Manager", "Day in the life", "life-crystal-bridges.jpg"),
    ("Pharmacy Tech", "Day in the life", "life-amp.jpg"),
]

# --------------------------------------------------------------------------- #
# Benefit tiles on the job detail page. Keyed by brand; hourly and salaried
# postings surface a slightly different Live Better U line, exactly as upstream.
# --------------------------------------------------------------------------- #
_WALMART_PLUS_TILE = (
    "Walmart+",
    "Free shipping",
    "As a Walmart Associate, you're eligible to become a Walmart+ member. Enjoy benefits "
    "like free store delivery and shipping, fuel savings, and video streaming. Sam's Club "
    "associates are eligible for a Club Membership.",
    "tile-walmart-plus.svg",
)
_DISCOUNT_TILE = (
    "Discount Card",
    "Get 10% off",
    "Walmart associates are eligible for a 10% discount card on all general merchandise "
    "items and fresh produce in-store and on select items at Walmart.com. Eligible after "
    "90 days of employment.",
    "tile-card.svg",
)
_LBU_FIELD_TILE = (
    "Live Better U",
    "100% covered",
    "Earn a degree or in-demand skills certificates with no debt - Walmart covers 100% of "
    "tuition and books. Live Better U offers 60+ programs for Associates to pursue their dreams.",
    "tile-graduation.svg",
)
_LBU_CORP_TILE = (
    "Live Better U",
    "100% covered",
    "Through Live Better U, Walmart and Sam's Club associates can learn critical skills and "
    "create pathways for promotion into in-demand jobs within the company. Whether earning a "
    "college degree, certificate or high school diploma, Walmart pays for tuition and books.",
    "tile-graduation.svg",
)
_ACADEMY_TILE = (
    "Walmart Academy",
    "Grow your skills",
    "Ready to grow your career? Walmart Academy offers job-specific retail training and "
    "leadership courses to help Associates reach their career goals.",
    "tile-growth.svg",
)


def benefit_tiles_for(brand: str, population: str) -> list[tuple[str, str, str, str]]:
    first = _DISCOUNT_TILE if population == "salaried" else _WALMART_PLUS_TILE
    second = _LBU_CORP_TILE if population == "salaried" else _LBU_FIELD_TILE
    return [first, second, _ACADEMY_TILE]


JOB_BENEFIT_ROWS = [
    ("Financial perks", "Enjoy 401(k) matching and stock purchase plans", "benefit-financial.svg"),
    ("Wellbeing programs", "Access mental health resources and assistance programs for life's challenges", "benefit-wellbeing.svg"),
    ("Paid time off", "Take a break as needed for vacation, sick leave, holidays, parental leave, and more", "benefit-pto.svg"),
    ("Career growth opportunities", "Training, leadership programs, and clear paths to advance", "benefit-growth.svg"),
    ("Comprehensive health benefits", "Medical, dental, vision, and wellness programs for you and your family", "benefit-health.svg"),
]

LIFE_AT_WALMART_HEADING = "Life at Walmart"
LIFE_AT_WALMART = [
    "At Walmart, you're welcome for who you are, no matter your background, experiences, or perspectives.",
    "Our stores and services are for everyone, and so is our workplace. We believe different experiences "
    "drive our ability to better serve our communities and deliver affordable products across the nation.",
    "Here, your unique insights and ideas are encouraged, valued, and essential to creating a "
    "forward-thinking company that thrives on fresh ideas and dedicated teamwork.",
    "Since our founding, we've focused on bringing affordable essentials to families everywhere, and "
    "today, Walmart is one of the most recognizable names in retail worldwide.",
]
LIFE_AT_WALMART_QUOTE = (
    "Join us, and help us continue our mission to bring everyday value and support to communities everywhere."
)

DRUG_FREE_NOTICE = (
    "Walmart is committed to maintaining a drug-free workplace and has a no tolerance policy regarding "
    "the use of illegal drugs and alcohol on the job. This policy applies to all employees and aims to "
    "create a safe and productive work environment."
)

HOURLY_PAY_NOTICE = [
    "The actual hourly rate will equal or exceed the required minimum wage applicable to the job location.",
    "Additional compensation includes annual or quarterly performance incentives.",
    "Additional compensation in the form of premiums may be paid in amounts ranging from $0.35 per hour "
    "to $3.00 per hour in specific circumstances. Premiums may be based on schedule, facility, season, "
    "or specific work performed. Multiple premiums may apply if applicable criteria are met.",
]

MIN_QUAL_PREAMBLE = (
    "Outlined below are the required minimum qualifications for this position. If none are listed, "
    "there are no minimum qualifications."
)
PREF_QUAL_PREAMBLE = (
    "Outlined below are the optional preferred qualifications for this position. If none are listed, "
    "there are no preferred qualifications."
)

# --------------------------------------------------------------------------- #
# Resources pages
# --------------------------------------------------------------------------- #
LOCATIONS_HEADING = "Our locations"
LOCATIONS_BLURB = (
    "Our hubs spark collaboration and innovation, so you're free to energize and push boundaries "
    "from the space that serves you best."
)
HUB_COPY = {
    "10101": (
        "Northwest Arkansas",
        "Northwest Arkansas offers trails, local eats, and the Crystal Bridges Museum - while our "
        "12 new Home Office buildings reflect the company's story through thoughtful design.",
        "loc-nwa.jpg",
    ),
    "11807": (
        "Sunnyvale",
        "A weekend hike through the mountains. An evening walk next to the ocean. A quick visit to a "
        "museum. The best of both worlds - work and leisure - are waiting for you right here.",
        "loc-sunnyvale.jpg",
    ),
    "11003": (
        "Hoboken",
        "Just across from Lower Manhattan, Hoboken is a walkable, character-filled town on the Hudson "
        "with a truly unique charm.",
        "loc-hoboken.jpg",
    ),
    "11500": (
        "Dallas",
        "Our Dallas office anchors merchandising, finance and supply chain teams in the middle of one "
        "of the fastest-growing metros in the country.",
        "loc-dc-metro.jpg",
    ),
}
LOCATIONS_CLOSING = (
    "Between making an impact at scale and our culture of promoting from within, from coders all the "
    "way to cashiers, Walmart is the best place to build a career, period."
)

HIRING_HEADING = "How we hire"
HIRING_BLURB = (
    "Every career starts with a first step. Whether you're applying for your first job or your next "
    "big move, this is the beginning of something new. At Walmart and Sam's Club, the hiring process "
    "is about more than landing a role, it's about discovering where you belong, where you can grow, "
    "and where your work can make a real difference."
)
HIRING_STEPS = [
    ("1. Find your role", "Search open roles by keyword, career area or location, then save the ones you like."),
    ("2. Apply online", "Share your contact details and work history. Most applications take 20-25 minutes."),
    ("3. Interview", "A recruiter or hiring manager reaches out, usually within a week of your application."),
    ("4. Offer and onboarding", "Accept your offer, complete pre-employment steps and pick your start date."),
]
HIRING_FAQ = [
    (
        "Before you apply",
        [
            (
                "Do I need a resume or CV to apply for all Walmart jobs?",
                "Not necessarily. A resume or CV is not required to apply, but you will need to provide "
                "details about your job history and other information on the application. If you would "
                "like to include your resume, LinkedIn profile, portfolio or website, there will be a "
                "section where you can add it to your application.",
            ),
            (
                "How long does it take to fill out an application on average?",
                "On average, it takes 20-25 minutes to complete your application for the first time. "
                "Subsequent applications will take less time to apply as our system saves your "
                "application information.",
            ),
            (
                "Can I start the application process and finish it later?",
                "For hourly roles within the Walmart Online Hiring Center, you have the ability to save "
                "your work and log back in at a later time.",
            ),
            (
                "Can I change my application after submitting?",
                "No, you cannot change your application after submitting. Please make sure that "
                "everything is finalized before you hit the submit button.",
            ),
        ],
    ),
    (
        "After you apply",
        [
            (
                "Will I receive confirmation that my application was successfully submitted?",
                "Yes. Once you complete your application you will see a confirmation screen with a "
                "confirmation number that starts with WMC-.",
            ),
            (
                "When should I expect to hear back after submitting my application?",
                "Timing varies, but we try to respond to applicants within a week of submission.",
            ),
            (
                "Will I be notified if I am not selected for an interview?",
                "Yes, you will be informed if you are not selected for an interview at this time.",
            ),
            (
                "Do you provide reasonable accommodations during the application process?",
                "Yes, reach out to your manager, recruiter or recruiting coordinator about any needs "
                "you have. We are happy to do what we can to support you.",
            ),
        ],
    ),
]

TERMS_HEADING = "Terms & Conditions"
TERMS_SECTIONS = [
    (
        "About this mirror",
        "This is an offline WebHarbor mirror of careers.walmart.com built for agent benchmarking. "
        "No application submitted here reaches Walmart Inc., and no data leaves the container.",
    ),
    (
        "Candidate accounts",
        "Accounts created on this mirror exist only inside the local database and are removed whenever "
        "the environment is reset to its seed state.",
    ),
    (
        "Applications",
        "Submitting an application records a row in the local database and returns a confirmation number "
        "in the form WMC-000000. It creates no relationship, express or implied, with Walmart Inc.",
    ),
    (
        "Accuracy of postings",
        "Job postings, pay ranges, store addresses and requisition IDs shown here are synthetic mirror "
        "data modelled on the structure of the real site.",
    ),
]

# --------------------------------------------------------------------------- #
# Footer
# --------------------------------------------------------------------------- #
FOOTER_CAREER_LINKS = [
    ("Stores and Clubs", "stores-and-clubs"),
    ("Supply Chain and Transportation", "supply-chain-and-transportation"),
    ("Healthcare", "healthcare"),
    ("Technology", "technology"),
    ("Corporate", "corporate"),
]
FOOTER_BRANDS = ["Walmart", "Sam's Club", "VIZIO"]
FOOTER_SOCIAL = [
    ("Facebook", "social-facebook.svg"),
    ("Instagram", "social-instagram.svg"),
    ("LinkedIn", "social-linkedin.svg"),
    ("X", "social-x.svg"),
    ("YouTube", "social-youtube.svg"),
    ("Glassdoor", "social-glassdoor.svg"),
]
FOOTER_EEO = (
    "Walmart, Inc. is an Equal Opportunity Employer. We believe we are best equipped to help our "
    "associates, customers, and the communities we serve live better when we really know them. That "
    "means understanding, respecting, and valuing unique styles, experiences, identities, abilities, "
    "ideas and opinions- while welcoming all people. Walmart Inc. participates in E-verify. Learn more "
    "about applicant rights under Federal Employment Laws."
)
FOOTER_BENEFITS_NOTE = (
    "Eligibility for benefits depends on your job classification, and benefits are subject to specific "
    "plan or program terms. For more information about your benefits options, please see the Associate "
    "Benefits Book at One.Walmart.com/BenefitsBook."
)

EMPTY_FUTURE_ROLES = (
    "Future roles are not part of this mirror. Every posting in this environment is an open role you "
    "can browse, save and apply to from the Open roles tab."
)
EMPTY_CONTENT_TAB = (
    "Content search is not part of this mirror. Use the Open roles tab, the career area pages or the "
    "Resources pages to explore this site."
)

# --------------------------------------------------------------------------- #
# Coarse lat/lng outlines used by the deterministic server-rendered cluster map.
# Points are (lng, lat).
# --------------------------------------------------------------------------- #
US_OUTLINE = [
    (-124.7, 48.4), (-123.0, 48.2), (-122.6, 47.0), (-124.0, 46.3), (-124.1, 43.7),
    (-124.4, 42.0), (-124.2, 40.4), (-122.4, 37.8), (-121.9, 36.6), (-120.6, 34.6),
    (-118.4, 33.7), (-117.1, 32.5), (-114.7, 32.7), (-111.1, 31.3), (-108.2, 31.3),
    (-106.5, 31.8), (-104.9, 30.6), (-103.1, 29.0), (-101.4, 29.8), (-99.1, 26.4),
    (-97.1, 25.9), (-97.4, 28.0), (-95.0, 29.1), (-93.8, 29.7), (-91.0, 29.2),
    (-89.4, 29.0), (-89.0, 30.2), (-87.5, 30.3), (-85.0, 29.7), (-84.0, 30.1),
    (-82.8, 27.9), (-81.8, 25.9), (-80.1, 25.2), (-80.1, 27.0), (-81.4, 30.7),
    (-80.8, 32.0), (-78.9, 33.7), (-75.7, 35.2), (-76.0, 36.9), (-75.1, 38.3),
    (-74.0, 39.7), (-73.9, 40.6), (-71.9, 41.3), (-70.0, 41.7), (-70.2, 42.6),
    (-70.8, 43.2), (-69.0, 43.9), (-67.0, 44.8), (-67.8, 45.7), (-69.2, 47.5),
    (-71.5, 45.0), (-74.7, 45.0), (-76.9, 43.3), (-79.2, 43.4), (-82.4, 41.7),
    (-83.1, 42.2), (-82.5, 45.3), (-84.4, 46.5), (-87.6, 46.0), (-88.0, 48.2),
    (-89.5, 48.0), (-95.2, 49.0), (-104.0, 49.0), (-116.0, 49.0), (-123.0, 49.0),
]
PR_OUTLINE = [
    (-67.3, 18.5), (-66.4, 18.5), (-65.6, 18.4), (-65.6, 17.9), (-66.6, 17.9), (-67.3, 18.1),
]
