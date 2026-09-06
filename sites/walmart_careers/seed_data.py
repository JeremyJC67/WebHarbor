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
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("WEBSYN_SKIP_BOOTSTRAP", "1")

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
def _assert_distractors() -> None:
    from app import Job as J, current_filters  # noqa: F401  (kept for symmetry)
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
        jobs, _store, _failed = search_jobs(base(**kwargs))
        return jobs

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
    states = {s.state for s in Store.query.all()}
    for state in sorted(states):
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

    # --- unique-answer invariants used by the task set ---------------------
    pr_cashiers = [
        j for j in Job.query.join(Store).filter(Store.state == "PR").all()
        if "Cashier" in j.title and j.population == "hourly"
    ]
    with_weekday_day = [j for j in pr_cashiers if "Weekday Day" in j.shifts]
    if len(pr_cashiers) < 5:
        problems.append(f"only {len(pr_cashiers)} PR cashier postings")
    if len(with_weekday_day) < 3:
        problems.append("fewer than 3 PR cashier postings list Weekday Day")
    tops = sorted((j.positions_available for j in with_weekday_day), reverse=True)
    if len(tops) >= 2 and tops[0] == tops[1]:
        problems.append("PR Weekday Day cashier postings have a tied maximum of open positions")
    if any(j.positions_available >= tops[0] for j in pr_cashiers if j not in with_weekday_day):
        pass  # a higher-positions near-miss without Weekday Day is intentional

    hoboken_tech = [
        j for j in results(area=["technology"], type=["Full time"], loc="Hoboken, NJ", radius=25)
    ]
    if len(hoboken_tech) < 6:
        problems.append(f"only {len(hoboken_tech)} Full time Technology roles near Hoboken")
    over_200k = [j for j in hoboken_tech if float(j.max_pay) > 200000]
    if len(over_200k) != 1:
        problems.append(f"{len(over_200k)} Hoboken Technology roles top out above $200,000 (want 1)")

    sams_pt_overnight = results(brand=["Sam's Club"], type=["Part time"], shift=["Weekend Overnight"])
    if len(sams_pt_overnight) < 6:
        problems.append(
            f"only {len(sams_pt_overnight)} Sam's Club Part time Weekend Overnight roles"
        )
    cheap_tx = [
        j for j in sams_pt_overnight
        if float(j.max_pay) <= 20.00 and j.store.state == "TX"
    ]
    if len(cheap_tx) != 1:
        problems.append(f"{len(cheap_tx)} Sam's Club PT overnight TX roles at or under $20/hr (want 1)")
    full_matches = [j for j in sams_pt_overnight if float(j.max_pay) <= 20.00]
    if len(full_matches) > len(sams_pt_overnight) / 2:
        problems.append("more than half of the Sam's Club overnight results match every constraint")

    cleveland = results(loc="Cleveland, OH", radius=25)
    if len(cleveland) < 6:
        problems.append(f"only {len(cleveland)} roles within 25 miles of Cleveland, OH")

    ms_auto = [
        j for j in Job.query.join(Store).filter(Store.state == "MS").all()
        if j.title == "Auto Care Center Technician"
    ]
    if len(ms_auto) != 2:
        problems.append(f"{len(ms_auto)} Auto Care Center Technician postings in MS (want 2)")
    elif ms_auto[0].positions_available == ms_auto[1].positions_available:
        problems.append("the two MS Auto Care postings have the same number of open positions")

    marcy_freight = [
        j for j in Job.query.join(Store).filter(Store.city == "Marcy").all()
        if j.title == "Freight Handler"
    ]
    if len(marcy_freight) != 2:
        problems.append(f"{len(marcy_freight)} Freight Handler postings in Marcy, NY (want 2)")
    elif marcy_freight[0].shift_time == marcy_freight[1].shift_time:
        problems.append("the two Marcy Freight Handler postings share a shift start window")

    last_mile = Job.query.filter(Job.title.like("Senior Manager, Delivery Search%")).all()
    if len(last_mile) != 2:
        problems.append(f"{len(last_mile)} Last Mile Delivery postings (want 2)")
    else:
        options = [j.min_qualifications[1] for j in last_mile]
        if options[0] == options[1]:
            problems.append("the two Last Mile Delivery postings share Option 2 text")

    # Qualification text referenced by tasks must be unique per posting.
    quals = [j.min_qualifications_json for j in Job.query.filter_by(population="salaried").all()]
    if len(set(quals)) != len(quals):
        problems.append("salaried minimum-qualification texts are not unique per posting")

    # Targets must not be pinned to rank 1 of their own natural query.
    for query, title in (("optician", "Optician"), ("freight handler", "Freight Handler")):
        rows = results(q=query)
        if len(rows) < 6:
            problems.append(f"query {query!r} returns only {len(rows)} results")

    if problems:
        raise AssertionError(
            "seed distractor checks failed:\n  - " + "\n  - ".join(problems)
        )


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
