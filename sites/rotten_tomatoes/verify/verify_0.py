"""R0: source-frozen Netflix Sci-Fi at-home streaming-date comparison.

Facts below derive from the unchanged 147-movie source catalog plus the 123
homepage additions captured on 2026-09-07. Input catalog SHA256 values:
aa04c6ac5acbaf76da631f120e82fad4d8f97eb7fa2e6b238b88c939f8f822e8
76e9ee372f85d08812cc0561e454c69e39e2fc803881adc7c98a78b2492160ca
The public task selects the Netflix Subscription Platform. Its eight source
records all have streaming dates; the generic missing-date rule remains in force.
A missing streaming date remains None and is excluded from the calendar maximum.
Only frozen harness snapshots and screenshot-bound UI observations are read.
No live database, catalog loading, search API, or runner answer is a fact source.
"""
from __future__ import annotations

import argparse
from datetime import date
import html
import json
from pathlib import Path
import re
import sqlite3
import sys
import unicodedata
from urllib.parse import parse_qs, urlsplit

from contracts import CONTRACTS
from verify_lib import Run, Snapshot, VerificationError, heading, main_dom, movie_links, norm, require


TASK_ID = "RottenTomatoes--0"
CANDIDATES = [{'slug': 'war_machine',
  'title': 'War Machine',
  'date': '2026-03-06',
  'writers': ['Patrick Hughes', 'James Beaufort']},
 {'slug': 'bugonia', 'title': 'Bugonia', 'date': '2025-11-25', 'writers': ['Will Tracy']},
 {'slug': 'frankenstein_2025',
  'title': 'Frankenstein',
  'date': '2025-11-07',
  'writers': ['Guillermo del Toro']},
 {'slug': 'jurassic_world_rebirth',
  'title': 'Jurassic World Rebirth',
  'date': '2025-08-05',
  'writers': ['David Koepp']},
 {'slug': 'godzilla_minus_one',
  'title': 'Godzilla Minus One',
  'date': '2024-06-01',
  'writers': ['Takashi Yamazaki']},
 {'slug': 'the_hunger_games_the_ballad_of_songbirds_and_snakes',
  'title': 'The Hunger Games: The Ballad of Songbirds & Snakes',
  'date': '2023-12-19',
  'writers': ['Michael Arndt', 'Michael Lesslie']},
 {'slug': 'the_hunger_games',
  'title': 'The Hunger Games',
  'date': '2016-09-09',
  'writers': ['Gary Ross', 'Suzanne Collins', 'Billy Ray']},
 {'slug': 'the_hunger_games_catching_fire',
  'title': 'The Hunger Games: Catching Fire',
  'date': '2016-08-26',
  'writers': ['Simon Beaufoy', 'Michael Arndt']}]


def clean(text):
    text = html.unescape(unicodedata.normalize("NFKC", str(text)))
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.replace("’", "'").replace("–", "-").replace("—", "-")


MONTHS = {name: i for i, names in enumerate((
    ("jan", "january"), ("feb", "february"), ("mar", "march"),
    ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
    ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"),
    ("nov", "november"), ("dec", "december")), 1) for name in names}
MONTH_PATTERN = "(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"


def date_spans(text):
    """Unambiguous English, ISO and Chinese calendar dates, with their spans."""
    patterns = (
        (r"(?<!\d)(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?(?!\d)", "ymd"),
        (rf"\b({MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s+(\d{{4}})\b", "mdy"),
        (rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH_PATTERN})\.?\s*,?\s+(\d{{4}})\b", "dmy"),
    )
    result = []
    for pattern, order in patterns:
        for match in re.finditer(pattern, clean(text), re.I):
            a, b, c = match.groups()
            if order == "ymd":
                value = date(int(a), int(b), int(c))
            elif order == "mdy":
                value = date(int(c), MONTHS[a.lower()], int(b))
            else:
                value = date(int(c), MONTHS[b.lower()], int(a))
            result.append((match.start(), match.end(), value.isoformat()))
    return sorted(result)


def dates(text):
    return {d for _, _, d in date_spans(text)}


def name_key(text):
    return re.sub(r"[^\w]+", " ", clean(text).casefold()).strip()


def split_names(value):
    if isinstance(value, list):
        return {name_key(x) for x in value if norm(x)}
    return {name_key(x) for x in re.split(r"\s*(?:<br\s*/?>|,|;|、|，|；|\band\b|&|和|与|及| / |\n)\s*", clean(value)) if norm(x)}


def unchanged(before, after, candidates):
    require(before.schema == after.schema, "database schema changed during information task")
    require(before.columns == after.columns, "database columns changed during information task")
    for table in before.rows:
        require(before.bag(table) == after.bag(table), f"information task changed {table}")
    genre = before.one("genres", name="Sci-Fi")
    genre_ids = {r["movie_id"] for r in before.select("movie_genres", genre_id=genre["id"])}
    actual = {m["slug"]: m for m in before.rows["movies"] if m["id"] in genre_ids and m.get("available_at_home") == 1
              and "Netflix" in [value.strip() for value in (m.get("streaming_platform") or "").split(",")]}
    require(set(actual) == {m["slug"] for m in candidates}, "frozen Netflix at-home Sci-Fi candidate set differs from source contract")
    for movie in candidates:
        row = actual[movie["slug"]]
        require(row["title"] == movie["title"], "snapshot movie identity differs from source contract")
        value = row.get("release_date_streaming")
        require(not norm(value) if movie["date"] is None else dates(value) == {movie["date"]},
                "snapshot streaming date differs from source contract")
        require(split_names(row.get("screenwriter") or "") == {name_key(x) for x in movie["writers"]}, "snapshot screenwriters differ from source contract")


def info_field(dom, label):
    """Read a labeled Movie Info value, never a review or unrelated page date."""
    main = main_dom(dom)
    start = re.search(r'heading ["\']Movie Info["\']', main, re.I)
    if not start:
        return ""
    block = re.split(r"(?m)^\s*- heading ", main[start.end():], maxsplit=1)[0]
    labels = ("Director", "Producer", "Screenwriter", "Distributor", "Production Co", "Rating", "Genre",
              "Original Language", "Release Date (Theaters)", "Release Date (Streaming)", "Runtime", "Box Office")
    values = []
    active = False
    for line in block.splitlines():
        item = re.match(r"\s*- (?:generic|text|term|definition):\s*(.*?)\s*$", line)
        link = re.match(r'\s*- link ["\'](.*?)["\']:', line)
        if not item and not link:
            continue
        text = (item or link)[1].strip('"')
        if text == label:
            active = True
        elif active and text in labels:
            break
        elif active:
            values.append(text)
    return norm(" ".join(values))



def missing_streaming_date_evidence(dom, title):
    """Prove absence from a bounded Movie Info section, not an unloaded page."""
    main = main_dom(dom)
    if not heading(main, title):
        return False
    start = re.search(r'heading ["\']Movie Info["\']', main, re.I)
    if not start:
        return False
    remaining = main[start.end():]
    end = re.search(r"(?m)^\s*- heading ", remaining)
    if not end:
        return False
    section = remaining[:end.start()]
    # Empty/loading headings do not establish that a metadata section was read.
    if sum(bool(info_field(dom, label)) for label in
           ("Director", "Producer", "Screenwriter", "Genre", "Runtime", "Rating")) < 2:
        return False
    if "Release Date (Streaming)" not in section:
        return True
    # An explicit empty-value marker is another honest rendering of a null.
    return norm(info_field(dom, "Release Date (Streaming)")).casefold() in {
        "--", "—", "n/a", "not listed", "not provided", "not available", "未列出", "未提供"}


def streaming_date_evidence(dom, movie):
    if movie["date"] is None:
        return missing_streaming_date_evidence(dom, movie["title"])
    return (heading(main_dom(dom), movie["title"])
            and dates(info_field(dom, "Release Date (Streaming)")) == {movie["date"]})


def browse_scope(dom):
    main = main_dom(dom)
    return (heading(main, "Streaming at Home")
            and bool(re.search(r'option ["\']Sci-Fi["\']\s*\[selected\]', main))
            and bool(re.search(r'option ["\']Netflix["\']\s*\[selected\]', main)))


def record_evidence(run, frame, label):
    run.evidence.append({"check": label, "step": frame.position // 2, "path": frame.path,
                         "source": "synchronous_dom" if frame.dom is not None else "anchored_screenshot"})


def comparison_ui(run, candidates):
    wanted = {m["slug"] for m in candidates}
    listed = set()
    scope_frames = []
    for frame in run.frames:
        if frame.path != "/browse/movies_at_home":
            continue
        query = parse_qs(urlsplit(frame.url).query)
        if (query.get("genre") != ["sci-fi"] or query.get("platform") != ["Netflix"]
                or any(query.get(k, [""])[0] for k in ("rating", "certified_fresh"))):
            continue
        if not run.supports(frame, browse_scope, "The Streaming at Home browse page has Sci-Fi and the Netflix Subscription Platform selected, with no additional rating or Certified Fresh restriction."):
            continue
        scope_frames.append(frame)
        if frame.dom is not None:
            cards = set(movie_links(frame.dom))
            require(not cards - wanted, "Netflix Sci-Fi at-home browse evidence contains an unexpected movie")
            listed.update(cards)
        else:
            for movie in candidates:
                if run.supports(frame, lambda d: False, f"The Netflix Sci-Fi Streaming at Home results visibly show a movie card titled {movie['title']}."):
                    listed.add(movie["slug"])
    require(scope_frames and listed == wanted, "complete Netflix at-home Sci-Fi candidate collection was not observed")
    record_evidence(run, scope_frames[0], "at_home_sci_fi_netflix_scope")
    run.evidence.append({"check": "candidate_collection", "count": len(listed)})
    for movie in candidates:
        found = None
        for frame in run.frames:
            if frame.path == "/m/" + movie["slug"] and run.supports(frame,
                    lambda d, m=movie: streaming_date_evidence(d, m),
                    (f"The complete {movie['title']} Movie Info section is visible through its ending and contains no Release Date (Streaming), or explicitly marks it as not listed. An unloaded or cropped section is insufficient."
                     if movie["date"] is None else
                     f"The {movie['title']} Movie Info section visibly labels Release Date (Streaming) as {movie['date']}; it is not a theater date or the movie year.")):
                found = frame
                break
            # A future legitimate browse layout may present labeled dates on
            # individual cards. Merely listing a year or ordering cards is not enough.
            if movie["date"] is not None and frame in scope_frames and frame.dom is not None:
                marker = re.search(r"/url:\s*/m/" + re.escape(movie["slug"]) + r"(?:\s|$)", main_dom(frame.dom))
                if marker:
                    block = main_dom(frame.dom)[marker.end():]
                    block = re.split(r'(?m)^\s*- link ["\']', block, maxsplit=1)[0]
                    if "Release Date (Streaming)" in block and dates(block) == {movie["date"]}:
                        found = frame
                        break
        require(found is not None, f"streaming date or explicit absence comparison missing for {movie['title']}")
        record_evidence(run, found, ("streaming_date_absent:" if movie["date"] is None else "compared_streaming_date:") + movie["slug"])
    dated = [m for m in candidates if m["date"] is not None]
    require(dated, "no listed streaming date in the source candidate set")
    latest = max(date.fromisoformat(m["date"]) for m in dated)
    winners = [m for m in dated if date.fromisoformat(m["date"]) == latest]
    for movie in winners:
        run.prove("all_screenwriters:" + movie["slug"], {"/m/" + movie["slug"]}, 0,
            lambda d, m=movie: heading(main_dom(d), m["title"]) and split_names(info_field(d, "Screenwriter")) == {name_key(w) for w in m["writers"]},
            f"The {movie['title']} Movie Info section shows exactly these Screenwriter names: {', '.join(movie['writers'])}.")
    return winners


def check_records(records, winners):
    require(isinstance(records, list) and len(records) == len(winners), "final answer movie set has missing or extra entries")
    expected = {name_key(m["title"]): m for m in winners}
    reported = set()
    for row in records:
        require(isinstance(row, dict), "final answer movie record is invalid")
        aliases = {"title": "title", "movie": "title", "movie title": "title", "片名": "title", "电影": "title",
                   "date": "date", "release date streaming": "date", "streaming release date": "date", "日期": "date",
                   "screenwriter": "screenwriters", "screenwriters": "screenwriters", "screenwriter s": "screenwriters", "编剧": "screenwriters"}
        fields = {}
        for label, value in row.items():
            label = aliases.get(name_key(label.replace("_", " ")))
            require(label is not None and label not in fields, "final answer record has extra or duplicate fact fields")
            fields[label] = value
        row = fields
        require(set(row) == {"title", "date", "screenwriters"}, "final answer record has missing fact fields")
        title = name_key(row.get("title", row.get("movie", "")))
        require(title in expected and title not in reported, "final answer reports an extra, duplicate, or incorrect movie")
        reported.add(title)
        value = row.get("date", row.get("release_date_streaming", ""))
        require(dates(value) == {expected[title]["date"]}, "final answer streaming date is missing, wrong, or mismatched")
        writers = row.get("screenwriters", row.get("screenwriter", []))
        require(split_names(writers) == {name_key(w) for w in expected[title]["writers"]}, "final answer screenwriter set has missing or extra names")
    require(reported == set(expected), "final answer omits a tied movie")


def answer_records(answer):
    """Accept explicit JSON and Markdown table records without a language model."""
    raw = answer.strip()
    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    require(len(fenced) <= 1, "multiple structured answer blocks")
    if fenced:
        raw = fenced[0].strip()
    if raw.startswith(("[", "{")):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = None
        if value is not None:
            if isinstance(value, dict) and ("movies" in value or "results" in value):
                require(set(value) in ({"movies"}, {"results"}), "final answer wrapper has extra result fields")
                return value.get("movies", value.get("results"))
            return [value] if isinstance(value, dict) else value
    lines = [line.strip().strip("|") for line in raw.splitlines() if "|" in line]
    if len(lines) >= 3:
        headers = [name_key(x) for x in lines[0].split("|")]
        columns = {}
        for index, header in enumerate(headers):
            if header in ("title", "movie", "movie title", "电影", "片名"):
                columns["title"] = index
            elif "date" in header or "日期" in header:
                columns["date"] = index
            elif "writer" in header or "编剧" in header:
                columns["screenwriters"] = index
        if len(columns) == 3:
            require(len(headers) == 3, "answer table has extra or duplicate fact columns")
            rows = []
            for line in lines[1:]:
                if re.fullmatch(r"[\s:|\-]+", line):
                    continue
                values = line.split("|")
                require(len(values) == len(headers), "malformed answer table")
                rows.append({k: values[i].strip().strip("*") for k, i in columns.items()})
            return rows
    return None


def writer_records(segment):
    """Recognize explicit additional writer facts in surrounding commentary."""
    labels = r"(?:screenwriters?|writers?|编剧)\s*[:：]\s*|(?:written|screenplay)\s+by\s+"
    fields = re.findall(r"(?:" + labels + r")([^;；。\n]+?)(?=(?:\.\s|\.$|[;；。\n]|$))", segment, re.I)
    return [split_names(value.strip().strip(".* ")) for value in fields]


def check_answer(answer, winners, movie_titles):
    answer = clean(answer)
    records = answer_records(answer)
    require(records is not None, "the public output contract requires a three-column result table or equivalent JSON records")
    check_records(records, winners)
    # Ordinary introductions and conclusions need no vocabulary whitelist.
    # Additional explicit records or contradictory fact assertions outside the
    # structured result cannot silently enlarge or alter that result set.
    if "```" in answer:
        outside = re.sub(r"```(?:json)?[\s\S]*?```", "", answer, flags=re.I)
    elif answer.lstrip().startswith(("[", "{")):
        outside = ""
    else:
        outside = "\n".join(line for line in answer.splitlines() if "|" not in line)
    expected_dates = {m["date"] for m in winners}
    require(dates(outside) <= expected_dates, "surrounding prose contradicts the reported streaming date")
    writer_fields = writer_records(outside)
    require(not (date_spans(outside) and writer_fields), "an additional explicit movie/date/writer record appears outside the table")
    expected_writers = {name_key(w) for movie in winners for w in movie["writers"]}
    require(all(field <= expected_writers for field in writer_fields), "surrounding prose adds an unreported screenwriter")
    require(not re.search(r"(?:not|isn't|不是|并非)\s+" + "(?:" + "|".join(re.escape(m["title"]) for m in winners) + ")", outside, re.I), "surrounding prose negates the result")


def evaluate(run_dir, initial_db=None, after_db=None, no_llm=False):
    evidence = []
    try:
        run = Run(run_dir, CONTRACTS[TASK_ID], no_llm=no_llm)
        before_path = initial_db or (Path(run_dir) / "before.db" if (Path(run_dir) / "before.db").is_file() else Path(run_dir) / "initial.db")
        before, after = Snapshot(before_path), Snapshot(after_db or Path(run_dir) / "after.db")
        unchanged(before, after, CANDIDATES)
        evidence.append({"check": "read_only_all_tables", "snapshots": [Path(before_path).name, after.path.name]})
        winners = comparison_ui(run, CANDIDATES)
        evidence.extend(run.evidence)
        check_answer(run.data["final_answer"], winners, [m["title"] for m in before.rows["movies"]])
        evidence.append({"check": "calendar_maximum_and_exact_result_records", "compared": len(CANDIDATES), "tied_results": len(winners)})
        return {"task_id": TASK_ID, "pass": True, "reason": "The complete at-home Sci-Fi date comparison and exact result facts are evidenced; all database tables are unchanged.", "evidence": evidence}
    except (VerificationError, OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, OverflowError, sqlite3.Error) as exc:
        return {"task_id": TASK_ID, "pass": False, "reason": str(exc), "evidence": evidence}


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--initial_db")
    parser.add_argument("--after_db")
    parser.add_argument("--no_llm", nargs="?", const="true", default="false", choices=("true", "false", "True", "False"))
    args = parser.parse_args()
    result = evaluate(args.run_dir, args.initial_db, args.after_db, args.no_llm.lower() == "true")
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["pass"] else 1)



if __name__ == "__main__":
    cli()
