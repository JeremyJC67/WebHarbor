"""Carol's private rated-minus-watchlisted set, from frozen read-only evidence."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys

from contracts import CONTRACTS
from verify_lib import (Run, Snapshot, VerificationError, auth_step, authenticated,
                        check_state, heading, main_dom, movie_card, movie_links,
                        norm, require)

TASK_ID = "RottenTomatoes--14"
# Benchmark fixture invariants, deliberately kept out of task/rubric inputs.
EXPECTED_RATINGS = {"the_substance": 4, "nosferatu_2024": 4, "oddity": 5}
EXPECTED_WATCHLIST = {"barbie", "everything_everywhere_all_at_once", "the_substance", "nosferatu_2024"}


def scores(text):
    text = text.casefold()
    for word,value in {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5}.items():
        text = re.sub(r"\b" + word + r"\b",str(value),text)
    for word,value in {"零":0,"一":1,"二":2,"两":2,"三":3,"四":4,"五":5}.items():
        text = re.sub(word+r"(?=(?:颗)?星|分)",str(value),text)
    text = re.sub(r"(?<=\d)(?=[分星颗])"," ",text)
    found=[]
    def fraction(match):
        value,denominator = float(match[1]),float(match[2])
        require(denominator == 5 and 0 <= value <= 5,"final score uses the wrong scale")
        found.append(value)
        return " " * len(match[0])
    text = re.sub(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:/|out\s+of)\s*(\d+(?:\.\d+)?)",fraction,text)
    for match in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\w|\.\d)",text):
        value = float(match[1])
        if 1900 <= value <= 2100 and value.is_integer():
            continue
        require(0 <= value <= 5,"final personal score is outside the five-star scale")
        found.append(value)
    return found


def answer_pairs(answer, all_movies, expected):
    # Newlines are useful list boundaries, so preserve them for the parser.
    raw = str(answer)
    claims = re.split(r"[\n;；,，]|(?<!\d)[.!?。](?=\s|$)",raw)
    titles = sorted({m["title"] for m in all_movies},key=len,reverse=True)
    result={}
    pending=None
    for claim in claims:
        lower=claim.casefold()
        if not norm(claim):
            continue
        excluded = re.search(r"(?:already|also)\s+(?:in|on)\s+(?:(?:her|the|my)\s+)?watchlist|in\s+both|not\s+(?:missing|absent|the answer)|已在.*(?:收藏|watchlist)|两(?:个|张).*都有",lower)
        matches=[]
        for title in titles:
            for match in re.finditer(r"(?<!\w)"+re.escape(title)+r"(?!\w)",claim,re.I):
                if not any(a < match.end() and match.start() < b for a,b,_ in matches):
                    matches.append((match.start(),match.end(),title))
        matches.sort()
        if excluded:
            continue
        if not matches:
            values=scores(claim)
            if values:
                if pending and re.search(r"\b(?:it|its|this film|that movie)\b|它|该片",lower):
                    result.setdefault(pending,[]).extend(values)
                else:
                    require(False,"a score is not paired with a recognized result movie")
            continue
        for i,(start,end,title) in enumerate(matches):
            require(title in expected,"final answer includes an extra movie in the difference set")
            segment=claim[end:matches[i+1][0] if i+1<len(matches) else len(claim)]
            require(not re.search(r"\b(?:is not|isn't|was not)\s+(?:rated|missing|the answer)\b|并非答案|不是答案",segment,re.I),"final answer negates a required result")
            result.setdefault(title,[]).extend(scores(segment))
            pending=title
    require(set(result) == set(expected),"final rated-minus-watchlisted title set is missing or incorrect")
    for title,score in expected.items():
        require(result[title] and set(result[title]) == {float(score)},"final movie and personal-score pairing is missing, wrong, or contradictory")
    return {title:score for title,score in expected.items()}


def evaluate(task_id,run_dir,initial_db=None,after_db=None,no_llm=False):
    evidence=[]
    try:
        require(task_id == TASK_ID,"wrong information-task entrypoint")
        spec=CONTRACTS[TASK_ID]
        run=Run(run_dir,spec,no_llm=no_llm)
        directory=Path(run_dir)
        before_path=initial_db or (directory/"before.db" if (directory/"before.db").is_file() else directory/"initial.db")
        before=Snapshot(before_path)
        after=Snapshot(after_db or directory/"after.db")
        state=check_state(spec,before,after)
        evidence.append({"check":"read_only_snapshot_equality","snapshots":[Path(before_path).name,after.path.name]})
        user=state["user"]
        movies={m["id"]:m for m in before.rows["movies"]}
        ratings={movies[r["movie_id"]]["slug"]:r["score"] for r in before.select("user_ratings",user_id=user["id"])}
        watchlist={movies[r["movie_id"]]["slug"] for r in before.select("watchlist_items",user_id=user["id"])}
        require(ratings == EXPECTED_RATINGS and watchlist == EXPECTED_WATCHLIST,"initial private benchmark collections do not match the task contract")
        auth=auth_step(run,state)
        name=user["name"]
        run.prove("my_ratings_private_collection",{"/user/ratings"},auth,
            lambda d: authenticated(d,name) and heading(main_dom(d),"My Ratings")
            and set(movie_links(d)) == set(ratings)
            and all(re.search(r"(?<!\d)"+re.escape(f"{score:g}")+r"(?:\.0)?\s*/\s*5",movie_card(d,slug)) for slug,score in ratings.items()),
            "The signed-in My Ratings page shows these movie/personal-score pairs: "+json.dumps({next(m["title"]for m in movies.values()if m["slug"]==slug):score for slug,score in ratings.items()})+". Read the personal ratings, not public audience percentages.")
        run.prove("my_watchlist_private_collection",{"/user/watchlist"},auth,
            lambda d: authenticated(d,name) and heading(main_dom(d),"My Watchlist") and set(movie_links(d)) == watchlist,
            "The signed-in My Watchlist page shows these four movies: "+json.dumps([m["title"]for m in movies.values()if m["slug"]in watchlist])+".")
        expected={m["title"]:ratings[m["slug"]] for m in movies.values()if m["slug"] in ratings and m["slug"] not in watchlist}
        pairs=answer_pairs(run.data["final_answer"],before.rows["movies"],expected)
        evidence.extend(run.evidence)
        evidence.append({"check":"private_set_difference_and_score_pairing","result_count":len(pairs)})
        return {"task_id":TASK_ID,"pass":True,"reason":"Read-only private collections, authenticated UI comparison and final title/score pairs are evidenced.","evidence":evidence}
    except (VerificationError,OSError,ValueError,KeyError,TypeError,AttributeError,IndexError,sqlite3.Error) as exc:
        return {"task_id":TASK_ID,"pass":False,"reason":str(exc),"evidence":evidence}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--run_dir",required=True)
    parser.add_argument("--initial_db")
    parser.add_argument("--after_db")
    parser.add_argument("--no_llm",nargs="?",const="true",default="false",choices=("true","false","True","False"))
    args=parser.parse_args()
    result=evaluate(TASK_ID,args.run_dir,args.initial_db,args.after_db,args.no_llm.lower()=="true")
    print(json.dumps(result,ensure_ascii=False))
    sys.exit(0 if result["pass"] else 1)
