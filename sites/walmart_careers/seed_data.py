"""Deterministic seed for the Walmart Careers mirror.

Run directly (`PYTHONHASHSEED=0 python seed_data.py`) to rebuild
`instance_seed/walmart_careers.db` from `catalog_source.py`. The build is
byte-reproducible: one RNG, no wall-clock reads, sorted iteration only, and
werkzeug password hashes hard-coded because werkzeug salts randomly.
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("WEBSYN_SKIP_BOOTSTRAP", "1")

import _content as content_module
import catalog_source as source
from _content import MIRROR_REFERENCE_DATE
from app import (
    Application,
    Area,
    Category,
    Job,
    SavedJob,
    Store,
    User,
    app,
    confirmation_for,
    db,
    dumps_json,
)

RNG = random.Random(20260905)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "walmart_careers.db"
INSTANCE_SEED_DIR = BASE_DIR / "instance_seed"

# Hard-coded werkzeug hashes of DEMO_PASSWORD ("TestPass123!"). generate_password_hash
# salts randomly, so recomputing them here would break byte-identical rebuilds.
DEMO_PASSWORD_HASHES = {
    "alice.j@test.com": "scrypt:32768:8:1$x9JMG7iKsrRO1AGh$e8e195799326a6e1ff55d4d20dd2735d9d68c0ed4879bd6b263ac33fa9953b0f6c8505680f1a1d8a9fbe9b0d01ef5e88f99b77b89fc30299fda217185a3b7acf",
    "bob.c@test.com": "scrypt:32768:8:1$O14LIVdpqb3Q6D7E$4b9389cd00aad4417058fd629af5bf979b3f05bdf011791fbc65b7080fe898e50c7aedc2c22be92c71ae25a1df6922bb4ca44b386a7f17040b36888c0cdc8942",
    "carol.d@test.com": "scrypt:32768:8:1$9PGtFS6I89BOEugS$890b1c1935bb6c0c4a6f7f5ad689cc02415e4bd03b02e101f0c2095931d4f157a8504c0fa4f12c3073c94e1480fea3305ffbadc5e8540c5eaf1c16965cb47be7",
    "david.k@test.com": "scrypt:32768:8:1$luqs3gbiT1hPpw2c$09f31fef9514ae90d234cdd91a7f2c95d937e08a37fed60ce0b41755a097609040f7aa5083b94ecdd41804262dc778bd6f8d8e9f38f47f319fa8d6f3ed705d1b",
}

BENCHMARK_USERS = [
    ("alice.j@test.com", "alice.j", "Alice Johnson", "Alice", "Johnson", "479-555-0134", "Bentonville", "AR"),
    ("bob.c@test.com", "bob.c", "Bob Chen", "Bob", "Chen", "206-555-0178", "Seattle", "WA"),
    ("carol.d@test.com", "carol.d", "Carol Davis", "Carol", "Davis", "253-555-0119", "Tacoma", "WA"),
    ("david.k@test.com", "david.k", "David Kim", "David", "Kim", "214-555-0166", "Dallas", "TX"),
]
USER_CREATED_AT = datetime(2026, 6, 12, 9, 30, 0)

# (user email, job title, store number) — resolved to job ids after the catalog is built.
SEED_SAVED_JOBS = [
    ("alice.j@test.com", "Freight Handler", "9046", datetime(2026, 8, 3, 14, 12, 0)),
    ("alice.j@test.com", "Optician", "5991", datetime(2026, 8, 9, 10, 5, 0)),
    ("alice.j@test.com", "Cosmetics Cashier", "2503", datetime(2026, 8, 17, 19, 41, 0)),
    ("bob.c@test.com", "Asset Protection Associate", "5991", datetime(2026, 8, 4, 8, 22, 0)),
    ("bob.c@test.com", "Class A CDL Truck Driver", "6038", datetime(2026, 8, 11, 16, 48, 0)),
    ("bob.c@test.com", "Senior Data Scientist", "11500", datetime(2026, 8, 20, 12, 3, 0)),
    ("carol.d@test.com", "Pharmacy Technician", "4137", datetime(2026, 8, 6, 7, 55, 0)),
    ("carol.d@test.com", "Cafe Associate", "6318", datetime(2026, 8, 14, 21, 17, 0)),
    ("david.k@test.com", "Merchandising and Stocking Associate", "4750", datetime(2026, 8, 8, 11, 26, 0)),
    ("david.k@test.com", "IT Support Engineer", "10101", datetime(2026, 8, 19, 15, 34, 0)),
]

# (user email, job title, store number, submitted_at)
SEED_APPLICATIONS = [
    ("alice.j@test.com", "Team Lead", "144", datetime(2026, 8, 5, 13, 20, 0)),
    ("bob.c@test.com", "Order Filler", "6014", datetime(2026, 8, 12, 9, 2, 0)),
    ("carol.d@test.com", "Optician", "2073", datetime(2026, 8, 16, 17, 44, 0)),
    ("david.k@test.com", "Financial Analyst III", "11500", datetime(2026, 8, 21, 10, 11, 0)),
]

HERO_SETS = {
    "salaried": ["jobhero-corp-1.jpg", "jobhero-corp-2.jpg", "jobhero-corp-3.jpg"],
    "sams": ["jobhero-sams-1.png", "jobhero-sams-2.jpg", "jobhero-wm-2.jpg"],
    "walmart": ["jobhero-wm-1.png", "jobhero-wm-3.jpg", "jobhero-wm-4.jpg"],
    "walmart-alt": ["jobhero-wm-4.jpg", "jobhero-wm-2.jpg", "jobhero-wm-1.png"],
}

HOURLY_CLOSING = (
    "At Walmart, we offer competitive pay as well as performance-based incentive awards and other "
    "great benefits for a happier mind, body, and wallet. Health benefits include medical, vision and "
    "dental coverage. Financial benefits include 401(k), stock purchase and company-paid life "
    "insurance. Paid time off benefits include parental leave, family care leave, bereavement, jury "
    "duty, and voting."
)
LBU_CLOSING = (
    "Live Better U is a Walmart-paid education benefit program for full-time and part-time associates "
    "in Walmart and Sam's Club facilities. Programs range from high school completion to bachelor's "
    "degrees, including English Language Learning and short-form certificates. Tuition, books, and "
    "fees are completely paid for by Walmart."
)


# --------------------------------------------------------------------------- #
# Catalog construction
# --------------------------------------------------------------------------- #
def _shift_names(codes: str) -> list[str]:
    return [source.SHIFT_CODES[c] for c in codes.split(",")]


def _build_areas() -> dict[str, Area]:
    areas: dict[str, Area] = {}
    for slug, name, order, blurb, hero, has_index, filterable in source.AREAS:
        area = Area(
            slug=slug,
            name=name,
            display_order=order,
            blurb=blurb,
            hero_image=hero,
            has_index_page=has_index,
            is_filterable=filterable,
        )
        db.session.add(area)
        areas[slug] = area
    db.session.flush()
    return areas


def _build_categories(areas: dict[str, Area]) -> dict[tuple[str, str], Category]:
    categories: dict[tuple[str, str], Category] = {}
    for area_slug, name, slug, order in source.CATEGORIES:
        category = Category(
            area_id=areas[area_slug].id, name=name, slug=slug, display_order=order
        )
        db.session.add(category)
        categories[(area_slug, name)] = category
    db.session.flush()
    return categories


def _build_stores() -> dict[str, Store]:
    stores: dict[str, Store] = {}
    for row in source.STORES:
        (number, banner, location_name, street, city, state, zip_code,
         lat, lng, is_hub, is_office, _brand) = row
        store = Store(
            store_number=number,
            banner=banner,
            location_name=location_name,
            street=street,
            city=city,
            state=state,
            zip=zip_code,
            lat=lat,
            lng=lng,
            is_hub=is_hub,
            is_office=is_office,
        )
        db.session.add(store)
        stores[number] = store
    db.session.flush()
    return stores


def _store_brand() -> dict[str, str]:
    return {row[0]: row[11] for row in source.STORES}


def _hero_for(population: str, brand: str, index: int) -> list[str]:
    if population == "salaried":
        pool = HERO_SETS["salaried"]
    elif brand == "Sam's Club":
        pool = HERO_SETS["sams"]
    elif index % 2:
        pool = HERO_SETS["walmart-alt"]
    else:
        pool = HERO_SETS["walmart"]
    return list(pool)


def _build_jobs(areas, categories, stores) -> list[Job]:
    brands = _store_brand()
    used_ids: set[str] = set()
    for family in source.HOURLY_FAMILIES:
        for placement in family["placements"]:
            extras = placement[6] or {}
            if "job_id" in extras:
                used_ids.add(extras["job_id"])
    for family in source.SALARIED_FAMILIES:
        for placement in family["placements"]:
            extras = placement[6] or {}
            if "job_id" in extras:
                used_ids.add(extras["job_id"])

    jobs: list[Job] = []
    store_cursor: dict[str, int] = {}
    index = 0

    for family in source.HOURLY_FAMILIES:
        area = areas[family["area"]]
        category = categories[(family["area"], family["category"])]
        for placement in family["placements"]:
            store_no, emp_type, codes, min_pay, max_pay, positions, extras = placement
            extras = extras or {}
            store = stores[store_no]
            brand = brands[store_no]
            cursor = store_cursor.get(store_no, 10200) + RNG.randint(120, 980)
            job_id = extras.get("job_id")
            if job_id is None:
                job_id = f"CP-{store_no}-{cursor}"
                while job_id in used_ids:
                    cursor += 37
                    job_id = f"CP-{store_no}-{cursor}"
            store_cursor[store_no] = cursor
            used_ids.add(job_id)

            fmt = {
                "banner": store.banner,
                "store": store.store_number,
                "city": store.city,
                "state": store.state,
                "location_name": store.location_name,
            }
            paragraphs = [p.format(**fmt) for p in family["do"]]
            paragraphs.append(HOURLY_CLOSING)
            paragraphs.append(LBU_CLOSING)
            primary_code = codes.split(",")[0]
            job = Job(
                job_id=job_id,
                population="hourly",
                title=family["title"],
                brand=brand,
                store_id=store.id,
                area_id=area.id,
                category_id=category.id,
                shifts_json=dumps_json(_shift_names(codes)),
                employment_type=emp_type,
                pay_frequency="Hourly",
                min_pay=min_pay,
                max_pay=max_pay,
                posted_date=MIRROR_REFERENCE_DATE - timedelta(days=RNG.randint(1, 120)),
                sort_rank=0,
                summary=family["summary"].format(**fmt),
                description="\n\n".join(paragraphs),
                additional_description_json=dumps_json(
                    [b.format(**fmt) for b in family["bring"]]
                ),
                hashtag=family.get("hashtag"),
                shift_time=extras.get("shift_time", source.SHIFT_WINDOWS[primary_code]),
                positions_available=positions,
                min_age_note=emp_type != "Intern",
                hero_images_json=dumps_json(_hero_for("hourly", brand, index)),
            )
            db.session.add(job)
            jobs.append(job)
            index += 1

    salaried_cursor = 2410000
    posting_seq = 5210000
    for family in source.SALARIED_FAMILIES:
        area = areas[family["area"]]
        category = categories[(family["area"], family["category"])]
        for placement in family["placements"]:
            store_no, emp_type, min_pay, max_pay, worker_type, slots, extras = placement
            extras = extras or {}
            store = stores[store_no]
            brand = brands[store_no]
            salaried_cursor += RNG.randint(150, 900)
            job_id = extras.get("job_id")
            if job_id is None:
                job_id = f"R-{salaried_cursor}"
                while job_id in used_ids:
                    salaried_cursor += 13
                    job_id = f"R-{salaried_cursor}"
            used_ids.add(job_id)
            posting_seq += RNG.randint(400, 4000)

            degree_field, y1, y2, yp = slots
            fmt = {
                "banner": store.banner,
                "store": store.store_number,
                "city": store.city,
                "state": store.state,
                "location_name": store.location_name,
                "degree_field": degree_field,
                "y1": y1,
                "y2": y2,
                "yp": yp,
            }
            paragraphs = [p.format(**fmt) for p in family["do"]]
            paragraphs.append("About Team: " + family["about_team"].format(**fmt))
            job = Job(
                job_id=job_id,
                population="salaried",
                title=family["title"],
                brand=brand,
                store_id=store.id,
                area_id=area.id,
                category_id=category.id,
                shifts_json=dumps_json(_shift_names(family["shifts"])),
                employment_type=emp_type,
                pay_frequency="Annual",
                min_pay=min_pay,
                max_pay=max_pay,
                posted_date=MIRROR_REFERENCE_DATE - timedelta(days=RNG.randint(1, 120)),
                sort_rank=0,
                summary=family["summary"].format(**fmt),
                description="\n\n".join(paragraphs),
                additional_description_json=None,
                hashtag=None,
                shift_time=None,
                positions_available=None,
                min_age_note=False,
                worker_type=worker_type,
                job_posting_id=f"JOB_POSTING-3-{posting_seq}",
                min_qualifications_json=dumps_json(
                    [
                        family["min_qual_option1"].format(**fmt),
                        family["min_qual_option2"].format(**fmt),
                    ]
                ),
                preferred_qualifications=family["preferred"].format(**fmt),
                hero_images_json=dumps_json(_hero_for("salaried", brand, index)),
            )
            db.session.add(job)
            jobs.append(job)
            index += 1

    ranks = list(range(len(jobs)))
    RNG.shuffle(ranks)
    for job, rank in zip(jobs, ranks):
        job.sort_rank = rank
    db.session.flush()
    return jobs


# --------------------------------------------------------------------------- #
# Seed entry points (each gated as a whole — see AGENTS.md "Idempotent seeding")
# --------------------------------------------------------------------------- #
def seed_database(force: bool = False) -> None:
    if Job.query.count() > 0 and not force:
        return
    areas = _build_areas()
    categories = _build_categories(areas)
    stores = _build_stores()
    _build_jobs(areas, categories, stores)
    db.session.commit()


def seed_benchmark_users(force: bool = False) -> None:
    if User.query.filter_by(email="alice.j@test.com").first() and not force:
        return
    users: dict[str, User] = {}
    for email, username, display, first, last, phone, city, state in BENCHMARK_USERS:
        user = User(
            email=email,
            username=username,
            display_name=display,
            first_name=first,
            last_name=last,
            phone=phone,
            city=city,
            state=state,
            password_hash=DEMO_PASSWORD_HASHES[email],
            created_at=USER_CREATED_AT,
        )
        db.session.add(user)
        users[email] = user
    db.session.flush()

    for email, title, store_number, saved_at in SEED_SAVED_JOBS:
        job = _find_job(title, store_number)
        db.session.add(SavedJob(user_id=users[email].id, job_id=job.job_id, saved_at=saved_at))

    for email, title, store_number, submitted_at in SEED_APPLICATIONS:
        job = _find_job(title, store_number)
        user = users[email]
        application = Application(
            job_id=job.job_id,
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            status="Submitted",
            confirmation_no="pending",
            submitted_at=submitted_at,
        )
        db.session.add(application)
        db.session.flush()
        application.confirmation_no = confirmation_for(application.id)

    db.session.commit()


def _find_job(title: str, store_number: str) -> Job:
    store = Store.query.filter_by(store_number=store_number).one()
    job = (
        Job.query.filter_by(title=title, store_id=store.id)
        .order_by(Job.job_id)
        .first()
    )
    if job is None:
        raise RuntimeError(f"no seeded job {title!r} at store {store_number}")
    return job


# --------------------------------------------------------------------------- #
# Build-time invariants. Only ever called from build_seed_database().
# --------------------------------------------------------------------------- #
# (task index, title, locator kwargs, expected job_id). The locator is what the
# task text tells an agent to look for; the check below proves it resolves to
# exactly one posting in the catalog.
TASK_TARGETS = [
    (0, "Optician", {"city": "Wichita"}, "CP-5991-11240"),
    (1, "Staff, Software Engineer - Backend / ML", {"city": "Sunnyvale"}, "R-2463275"),
    (2, "Freight Handler", {"store": "9054"}, "CP-9054-10921"),
    (3, "Pharmacy Technician", {"city": "Bentonville"}, "CP-5260-11137"),
    (4, "Merchandising and Stocking Associate", {"state": "TX"}, "CP-4750-11184"),
    (5, "Senior Software Engineer", {"city": "Hoboken"}, "R-2411668"),
    (6, "Online Order Filling Team Supervisor", {"city": "Cleveland"}, "CP-2073-10625"),
    (7, "Merchandising Intern", {"store": "11109"}, "R-2442353"),
    (8, "Auto Care Center Technician", {"city": "Brookhaven"}, "CP-1230-11711"),
    (8, "Auto Care Center Technician", {"city": "Hazlehurst"}, "CP-954-11141"),
    (9, "Freight Handler", {"store": "6038"}, "CP-6038-10642"),
    (9, "Freight Handler", {"store": "9046"}, "CP-9046-10913"),
    (10, "Senior Manager, Delivery Search, Arrival & Matching (Last Mile Delivery)",
     {"city": "Bentonville"}, "R-2451180"),
    (10, "Senior Manager, Delivery Search, Arrival & Matching (Last Mile Delivery)",
     {"city": "Hoboken"}, "R-2439632"),
    (11, "Yard Driver-Off Property", {"city": "Williamsburg"}, "CP-6088-10488"),
    (12, "Asset Protection Associate", {"store": "5991"}, "CP-5991-10486"),
    (13, "Pharmacy Technician", {"city": "Tacoma"}, "CP-4137-11560"),
    (14, "eCom Warehouse Worker", {"store": "9046"}, "CP-9046-11101"),
    (16, "Cashier & Front End Services", {"city": "Bayamon"}, "CP-2503-10726"),
    (17, "Cosmetics Cashier", {"city": "Bayamon"}, "CP-2503-11683"),
    (18, "Class A CDL Truck Driver", {"city": "Ottawa"}, "CP-6014-12091"),
    (18, "Class A CDL Truck Driver", {"city": "Williamsburg"}, "CP-6088-11446"),
    (19, "Online Order Filling Team Supervisor", {"city": "Topeka"}, "CP-1179-11268"),
]


def _assert_distractors() -> None:
    """Build-time invariants behind the 20 benchmark tasks.

    Only ever called from build_seed_database(); never at import, bootstrap or
    /reset time. Every task in tasks.jsonl has a block here: the locator in the
    task text must resolve to exactly one posting, the natural query must return
    enough near-misses, and whatever the task asks the agent to report must have
    a unique answer.
    """
    from app import search_jobs

    problems: list[str] = []

    def base(**kwargs) -> dict:
        filters = {
            "q": "", "area": [], "category": [], "brand": [], "shift": [],
            "type": [], "rate": [], "loc": "", "radius": 25,
            "sort": "relevance", "page": 1, "tab": "jobs",
        }
        filters.update(kwargs)
        return filters

    def results(**kwargs) -> list[Job]:
        jobs, _location, _failed = search_jobs(base(**kwargs))
        return jobs

    def locate(title: str, *, city: str = "", state: str = "", store: str = "") -> list[Job]:
        rows = Job.query.filter_by(title=title).all()
        if city:
            rows = [j for j in rows if j.store.city == city]
        if state:
            rows = [j for j in rows if j.store.state == state]
        if store:
            rows = [j for j in rows if j.store.store_number == store]
        return sorted(rows, key=lambda j: j.job_id)

    def only(label: str, rows: list[Job], job_id: str) -> Job | None:
        if len(rows) != 1:
            problems.append(f"{label}: {len(rows)} postings match the task locator (want 1)")
            return None
        if rows[0].job_id != job_id:
            problems.append(f"{label}: resolved to {rows[0].job_id}, expected {job_id}")
        return rows[0]

    def breadth(label: str, rows: list[Job], full_matches: list[Job], minimum: int = 6) -> None:
        """Catalog breadth rule: >= `minimum` results, <= 50% of them full matches."""
        if len(rows) < minimum:
            problems.append(f"{label}: only {len(rows)} results (want >= {minimum})")
        elif len(full_matches) > len(rows) / 2:
            problems.append(
                f"{label}: {len(full_matches)}/{len(rows)} results satisfy every constraint (want <= 50%)"
            )

    # --- structural volumes ------------------------------------------------
    if Job.query.count() != 200:
        problems.append(f"expected 200 jobs, found {Job.query.count()}")
    for category in Category.query.all():
        count = Job.query.filter_by(category_id=category.id).count()
        if count < 4:
            problems.append(f"category {category.name!r} has only {count} jobs")
    for store in Store.query.all():
        count = Job.query.filter_by(store_id=store.id).count()
        if count < 3:
            problems.append(f"store #{store.store_number} has only {count} jobs")
    states = sorted({s.state for s in Store.query.all()})
    for state in states:
        count = Job.query.join(Store).filter(Store.state == state).count()
        if count < 8:
            problems.append(f"state {state} has only {count} jobs")
    shift_counts = {name: 0 for name in source.SHIFT_CODES.values()}
    for job in Job.query.all():
        for name in job.shifts:
            shift_counts[name] += 1
    for name, count in sorted(shift_counts.items()):
        if count < 24:
            problems.append(f"shift {name!r} appears on only {count} jobs")

    # --- global de-leak invariants ----------------------------------------
    hashtags = [f.get("hashtag") for f in source.HOURLY_FAMILIES]
    if len(set(hashtags)) != len(hashtags):
        problems.append("hourly hashtags are not unique per title family")
    quals = [j.min_qualifications_json for j in Job.query.filter_by(population="salaried").all()]
    if len(set(quals)) != len(quals):
        problems.append("salaried minimum-qualification texts are not unique per posting")
    target_ids = {job_id for _idx, _title, _loc, job_id in TASK_TARGETS}
    for job_id in content_module.TRENDING_JOB_IDS:
        if job_id in target_ids:
            problems.append(f"trending role {job_id} is a benchmark task target")
        if db.session.get(Job, job_id) is None:
            problems.append(f"trending role {job_id} does not exist")

    # --- every task locator resolves to exactly one posting ----------------
    resolved: dict[tuple[int, str], Job] = {}
    for index, title, locator, job_id in TASK_TARGETS:
        label = f"task {index} ({title} {locator})"
        job = only(label, locate(title, **locator), job_id)
        if job is not None:
            resolved[(index, job_id)] = job

    def target(index: int, job_id: str) -> Job | None:
        return resolved.get((index, job_id))

    # --- task 0: Optician in Wichita, KS ----------------------------------
    opticians = results(q="optician")
    breadth("task 0 (q=optician)", opticians,
            [j for j in opticians if j.title == "Optician"
             and j.store.banner == "Neighborhood Market" and j.store.city == "Wichita"])

    # --- task 1: Staff SWE in Sunnyvale — Option 2 unique among its family --
    staff = Job.query.filter_by(title="Staff, Software Engineer - Backend / ML").all()
    if len({j.min_qualifications[1] for j in staff}) != len(staff):
        problems.append("task 1: the Staff SWE postings share an Option 2 text")

    # --- task 2: Freight Handler #9054 — window + positions ---------------
    freight = results(q="freight handler")
    breadth("task 2 (q=freight handler)", freight,
            [j for j in freight if j.title == "Freight Handler" and j.store.store_number == "9054"])

    # --- task 3: Pharmacy Technician in Bentonville -----------------------
    pharmacy = [j for j in Job.query.all() if j.category and j.category.slug == "pharmacy-services"]
    breadth("task 3 (Pharmacy Services category)", pharmacy,
            [j for j in pharmacy if j.title == "Pharmacy Technician" and j.store.city == "Bentonville"])
    bentonville_pt = target(3, "CP-5260-11137")
    if bentonville_pt is not None:
        siblings = [j for j in Job.query.filter_by(title="Pharmacy Technician").all()
                    if j.job_id != bentonville_pt.job_id]
        if any(j.hashtag != bentonville_pt.hashtag for j in siblings):
            problems.append("task 3: Pharmacy Technician hashtags differ inside one title family")
        if all(j.positions_available == bentonville_pt.positions_available for j in siblings):
            problems.append("task 3: every Pharmacy Technician posting lists the same open positions")

    # --- task 4: Sam's Club / Part time / Weekend Overnight / <= $20 in TX --
    sams_pt_overnight = results(brand=["Sam's Club"], type=["Part time"], shift=["Weekend Overnight"])
    cheap = [j for j in sams_pt_overnight if float(j.max_pay) <= 20.00]
    cheap_tx = [j for j in cheap if j.store.state == "TX"]
    breadth("task 4 (Sam's Club PT weekend overnight)", sams_pt_overnight, cheap_tx)
    if len(cheap_tx) != 1:
        problems.append(f"task 4: {len(cheap_tx)} matching TX postings at or under $20/hr (want 1)")
    elif cheap_tx[0].job_id != "CP-4750-11184":
        problems.append(f"task 4: resolved to {cheap_tx[0].job_id}")

    # --- task 5: Full time Technology in Hoboken topping $200,000 ---------
    hoboken_tech = results(area=["technology"], type=["Full time"], loc="Hoboken, NJ", radius=25)
    over_200k = [j for j in hoboken_tech if float(j.max_pay) > 200000]
    breadth("task 5 (Full time Technology near Hoboken)", hoboken_tech, over_200k)
    if len(over_200k) != 1:
        problems.append(f"task 5: {len(over_200k)} Hoboken tech roles top out above $200,000 (want 1)")

    # --- task 6: Cleveland, OH / Full time / Weekday Day ------------------
    cleveland = results(loc="Cleveland, OH", radius=25)
    cleveland_full = results(loc="Cleveland, OH", radius=25, type=["Full time"], shift=["Weekday Day"])
    supervisors = [j for j in cleveland_full if j.title == "Online Order Filling Team Supervisor"]
    breadth("task 6 (within 25 miles of Cleveland)", cleveland, supervisors)
    if len(supervisors) != 1:
        problems.append(f"task 6: {len(supervisors)} Online Order Filling Team Supervisor roles near Cleveland")

    # --- task 7: Students / Intern / Sam's Club ---------------------------
    interns = results(area=["students"], type=["Intern"])
    sams_interns = [j for j in interns if j.brand == "Sam's Club"]
    merch_interns = [j for j in sams_interns if "Merchandising" in j.title]
    breadth("task 7 (Students interns)", interns, merch_interns)
    if len(merch_interns) != 1:
        problems.append(f"task 7: {len(merch_interns)} Sam's Club merchandising internships (want 1)")
    elif merch_interns[0].store.street != "2101 SE Simple Savings Dr":
        problems.append("task 7: the Sam's Club internship street address moved")

    # --- task 8: two MS Auto Care postings, different position counts ------
    ms_auto = [j for j in Job.query.join(Store).filter(Store.state == "MS").all()
               if j.title == "Auto Care Center Technician"]
    if len(ms_auto) != 2:
        problems.append(f"task 8: {len(ms_auto)} Auto Care Center Technician postings in MS (want 2)")
    elif ms_auto[0].positions_available == ms_auto[1].positions_available:
        problems.append("task 8: the two MS Auto Care postings list the same open positions")

    # --- task 9: two Marcy Freight Handlers, different windows ------------
    marcy_freight = [j for j in Job.query.join(Store).filter(Store.city == "Marcy").all()
                     if j.title == "Freight Handler"]
    if len(marcy_freight) != 2:
        problems.append(f"task 9: {len(marcy_freight)} Freight Handler postings in Marcy, NY (want 2)")
    elif marcy_freight[0].shift_time == marcy_freight[1].shift_time:
        problems.append("task 9: the two Marcy Freight Handler postings share a shift start window")

    # --- task 10: two Last Mile postings, different Option 2 years --------
    last_mile = Job.query.filter(Job.title.like("Senior Manager, Delivery Search%")).all()
    if len(last_mile) != 2:
        problems.append(f"task 10: {len(last_mile)} Last Mile Delivery postings (want 2)")
    else:
        years = [_years_in(j.min_qualifications[1]) for j in last_mile]
        if years[0] == years[1] or None in years:
            problems.append("task 10: the two Last Mile postings do not differ in Option 2 years")

    # --- task 11: Yard Driver search set ---------------------------------
    yard = results(q="yard driver")
    breadth("task 11 (q=yard driver)", yard,
            [j for j in yard if j.title == "Yard Driver-Off Property"
             and j.store.city == "Williamsburg"])

    # --- tasks 12 / 17: the seeded saved lists must disambiguate ----------
    for email, predicate, label in (
        ("bob.c@test.com", lambda j: j.store.banner == "Neighborhood Market",
         "task 12 (bob's Neighborhood Market saved role)"),
        ("alice.j@test.com", lambda j: j.employment_type == "Part time",
         "task 17 (alice's Part time saved role)"),
    ):
        user = User.query.filter_by(email=email).one()
        rows = [db.session.get(Job, s.job_id) for s in
                SavedJob.query.filter_by(user_id=user.id).order_by(SavedJob.id).all()]
        if len(rows) < 3:
            problems.append(f"{label}: only {len(rows)} saved roles (want >= 3)")
        matches = [j for j in rows if predicate(j)]
        if len(matches) != 1:
            problems.append(f"{label}: {len(matches)} saved roles match (want exactly 1)")

    # --- task 13: Pharmacy Technician in Tacoma --------------------------
    tacoma = results(q="pharmacy technician")
    breadth("task 13 (q=pharmacy technician)", tacoma,
            [j for j in tacoma if j.title == "Pharmacy Technician" and j.store.city == "Tacoma"])

    # --- task 14: eCom Warehouse Worker at #9046 -------------------------
    ecom = results(q="ecom warehouse worker")
    breadth("task 14 (q=ecom warehouse worker)", ecom,
            [j for j in ecom if j.title == "eCom Warehouse Worker"
             and j.store.store_number == "9046"])

    # --- task 15: david's profile starts different from the target values --
    david = User.query.filter_by(email="david.k@test.com").one()
    if david.phone == "479-555-0199" or (david.city, david.state) == ("Rogers", "AR"):
        problems.append("task 15: david's seeded profile already holds the target values")

    # --- task 16: PR cashiers ---------------------------------------------
    pr_cashiers = [j for j in Job.query.join(Store).filter(Store.state == "PR").all()
                   if "Cashier" in j.title and j.population == "hourly"]
    with_weekday_day = [j for j in pr_cashiers if "Weekday Day" in j.shifts]
    if len(pr_cashiers) < 5:
        problems.append(f"task 16: only {len(pr_cashiers)} PR cashier postings")
    if len(with_weekday_day) < 3:
        problems.append("task 16: fewer than 3 PR cashier postings list Weekday Day")
    if len(with_weekday_day) > len(pr_cashiers) / 2 and len(pr_cashiers) - len(with_weekday_day) < 1:
        problems.append("task 16: every PR cashier posting lists Weekday Day — no near-miss")
    tops = sorted((j.positions_available for j in with_weekday_day), reverse=True)
    if len(tops) >= 2 and tops[0] == tops[1]:
        problems.append("task 16: the PR Weekday Day cashiers tie on open positions")
    without = [j for j in pr_cashiers if j not in with_weekday_day]
    if tops and not any(j.positions_available >= tops[0] - 1 for j in without):
        problems.append("task 16: no near-miss PR cashier with a comparable open-position count")
    # both routes to the Puerto Rico result set must work
    by_state = results(q="cashier", loc="Puerto Rico")
    by_radius = results(q="cashier", loc="Bayamon, PR", radius=60)
    for label, rows in (("loc=Puerto Rico", by_state), ("loc=Bayamon, PR r=60", by_radius)):
        reachable = {j.job_id for j in rows}
        missing = [j.job_id for j in pr_cashiers if j.job_id not in reachable]
        if missing:
            problems.append(f"task 16: {label} misses PR cashier postings {missing}")

    # --- task 18: Drivers category, Ottawa vs Williamsburg ----------------
    drivers = results(area=["supply-chain-and-transportation"], category=["drivers"])
    cdl = [j for j in drivers if j.title == "Class A CDL Truck Driver"
           and j.store.city in ("Ottawa", "Williamsburg")]
    breadth("task 18 (Drivers category)", drivers, cdl, minimum=6)
    ottawa = target(18, "CP-6014-12091")
    williamsburg = target(18, "CP-6088-11446")
    if ottawa is not None and williamsburg is not None:
        if ottawa.positions_available == williamsburg.positions_available:
            problems.append("task 18: the two CDL postings list the same open positions")
        if ottawa.shift_time == williamsburg.shift_time:
            problems.append("task 18: the two CDL postings share a shift start window")

    # --- task 19: Digital Pickup and Delivery, Full time, fewest positions --
    pickup = results(area=["stores-and-clubs"], category=["digital-pickup-and-delivery"])
    pickup_full = [j for j in pickup if j.employment_type == "Full time"]
    counts = sorted(j.positions_available for j in pickup_full)
    breadth("task 19 (Digital Pickup and Delivery)", pickup,
            [j for j in pickup_full if counts and j.positions_available == counts[0]])
    if len(counts) < 3:
        problems.append(f"task 19: only {len(counts)} Full time digital pickup postings")
    elif counts[0] == counts[1]:
        problems.append("task 19: the fewest-open-positions posting is not unique")

    # --- relevance: no target is pinned to rank 1 of its natural query -----
    for index, query, job_id in (
        (0, "optician", "CP-5991-11240"),
        (2, "freight handler", "CP-9054-10921"),
        (13, "pharmacy technician", "CP-4137-11560"),
    ):
        rows = results(q=query)
        ids = [j.job_id for j in rows]
        if ids[:1] == [job_id]:
            problems.append(f"task {index}: the target is the first result for {query!r}")

    if problems:
        raise AssertionError(
            "seed distractor checks failed:\n  - " + "\n  - ".join(problems)
        )


def _years_in(text: str) -> int | None:
    match = re.search(r"(\d+)\s+years", text)
    return int(match.group(1)) if match else None


def build_seed_database() -> None:
    INSTANCE_SEED_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_database(force=True)
        seed_benchmark_users(force=True)
        _assert_distractors()
    shutil.copyfile(DB_PATH, INSTANCE_SEED_DIR / "walmart_careers.db")


if __name__ == "__main__":
    build_seed_database()
    print("Seed database generated from the deterministic Walmart Careers source catalog.")
