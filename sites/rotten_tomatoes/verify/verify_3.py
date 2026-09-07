"""R3 informed verifier development. Constructed tests are not real UI runs."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit

from contracts import CONTRACTS
from verify_lib import Run, Snapshot, VerificationError, heading, key, main_dom, norm, require

TASK_ID = 'RottenTomatoes--3'
MOVIES = (
    {'slug': 'oppenheimer_2023', 'title': 'Oppenheimer',
     'producers': ('Emma Thomas', 'Charles Roven', 'Christopher Nolan'), 'date': '2023-11-21'},
    {'slug': 'the_dark_knight', 'title': 'The Dark Knight',
     'producers': ('Emma Thomas', 'Charles Roven'), 'date': '2010-06-14'},
)
SHARED = {'emma thomas', 'charles roven'}
MONTHS = {name: i for i, names in enumerate((
    ('jan', 'january'), ('feb', 'february'), ('mar', 'march'), ('apr', 'april'),
    ('may',), ('jun', 'june'), ('jul', 'july'), ('aug', 'august'),
    ('sep', 'sept', 'september'), ('oct', 'october'), ('nov', 'november'), ('dec', 'december')), 1) for name in names}
MONTH = '(?:' + '|'.join(sorted(MONTHS, key=len, reverse=True)) + r')\.?'
DATE_PATTERNS = (
    (re.compile(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b'), 'ymd'),
    (re.compile(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日?'), 'ymd'),
    (re.compile(r'\b(' + MONTH + r')\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})\b', re.I), 'mdy'),
    (re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + MONTH + r')\s*,?\s*(\d{4})\b', re.I), 'dmy'),
    (re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b'), 'numeric_mdy'),
)


def dates(text):
    """Calendar values with spans; invalid dates remain invalid, never substrings."""
    result = []
    for pattern, order in DATE_PATTERNS:
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end, _ in result):
                continue
            parts = match.groups()
            try:
                if order == 'ymd':
                    year, month, day = map(int, parts)
                elif order == 'mdy':
                    month, day, year = MONTHS[parts[0].rstrip('.').casefold()], int(parts[1]), int(parts[2])
                elif order == 'dmy':
                    day, month, year = int(parts[0]), MONTHS[parts[1].rstrip('.').casefold()], int(parts[2])
                else:
                    month, day, year = map(int, parts)
                    if month > 12 and day <= 12:  # Unambiguous day/month/year.
                        month, day = day, month
                value = date(year, month, day).isoformat()
            except (ValueError, KeyError):
                value = 'INVALID'
            result.append((match.start(), match.end(), value))
    return sorted(result)


def leaf_texts(dom):
    result = []
    for line in dom.splitlines():
        match = re.match(r'\s*- (?:generic|text|paragraph):\s*(.+?)\s*$', line)
        if match:
            result.append(norm(match[1]).strip('"\''))
        else:
            match = re.match(r'\s*- (?:link|img) ["\'](.*?)["\'](?:\s*\[[^\]]*\])?\s*:?\s*$', line)
            if match:
                result.append(norm(match[1]))
    return result


INFO_LABELS = {'Director', 'Producer', 'Screenwriter', 'Distributor', 'Production Co',
               'Rating', 'Genre', 'Original Language', 'Release Date (Theaters)',
               'Release Date (Streaming)', 'Box Office (Gross USA)', 'Runtime', 'Studio'}


def info_field(dom, label):
    main = main_dom(dom)
    start = re.search(r'heading ["\']Movie Info["\']', main, re.I)
    if not start:
        return None
    section = re.split(r'\n\s*- heading ', main[start.end():], maxsplit=1)[0]
    leaves = leaf_texts(section)
    positions = [i for i, value in enumerate(leaves) if key(value) == key(label)]
    if len(positions) != 1:
        return None
    values = []
    for value in leaves[positions[0] + 1:]:
        if value in INFO_LABELS:
            break
        values.append(value)
    return norm(' '.join(values)) or None


def producer_names(value):
    return {key(name) for name in (value or '').split(',') if key(name)}


def detail_producers(dom, movie):
    return heading(main_dom(dom), 'Movie Info') and producer_names(info_field(dom, 'Producer')) == {key(name) for name in movie['producers']}


def detail_date(dom, expected):
    value = info_field(dom, 'Release Date (Streaming)')
    return bool(value) and [item[2] for item in dates(value)] == [expected]


def read_only(before, after):
    require('movies' in before.rows and 'users' in before.rows, 'frozen business snapshots are incomplete')
    require(before.schema == after.schema, 'database schema changed during read-only task')
    for table in before.rows:
        require(before.bag(table) == after.bag(table), 'business state changed during read-only task: ' + table)


def title_sections(answer, movies):
    matches = []
    for movie in movies:
        pattern = r'(?<!\w)' + re.escape(movie['title']) + r'(?!\w)'
        for match in re.finditer(pattern, answer, re.I):
            matches.append((match.start(), match.end(), movie['slug']))
    matches.sort()
    sections = []
    for i, (start, end, slug) in enumerate(matches):
        sections.append((slug, answer[end:matches[i + 1][0] if i + 1 < len(matches) else len(answer)]))
    return sections


def paired_movie_dates(answer, movies):
    expected = {movie['slug']: movie['date'] for movie in movies}
    positions = sorted((match.start(), match.end(), movie['slug']) for movie in movies
                       for match in re.finditer(r'(?<!\w)' + re.escape(movie['title']) + r'(?!\w)', answer, re.I))
    if {slug for _, _, slug in positions} != set(expected):
        return False
    for direction in ('after', 'before'):
        seen = {slug: [] for slug in expected}
        for index, (start, end, slug) in enumerate(positions):
            section = answer[end:positions[index + 1][0] if index + 1 < len(positions) else len(answer)] if direction == 'after' else answer[positions[index - 1][1] if index else 0:start]
            seen[slug].extend(value for _, _, value in dates(section))
        if all(values and set(values) == {expected[slug]} for slug, values in seen.items()):
            return True
    return False


PRODUCER_LABEL = (
    r'(?:(?:the|all)\s+)?(?:(?:shared|common|additional|extra)\s+)?producers?'
    r'(?:\s+(?:in\s+common|(?:credited|listed)\s+(?:on|in)\s+both\s+(?:pages|films|movies)))?'
    r'|共同制片人|共有制片人|制片人'
)


def producer_label(value):
    return bool(re.fullmatch(PRODUCER_LABEL, key(value).replace('_', ' ').strip(' :：*`')))


def asserted_names(value):
    """Parse a name-list slot, never remove arbitrary narrative vocabulary.

    Slots come from labelled records or an explicit producer predicate. Every
    positive item must be a complete expected name; unknown names remain items.
    """
    if isinstance(value, list):
        result = set()
        for item in value:
            require(isinstance(item, str), 'producer list items must be names')
            result.update(asserted_names(item))
        return result
    require(isinstance(value, str), 'producer assertion must be a name list')
    value = norm(value).strip(' .:：')
    contrast = re.split(r',?\s+(?:(?:but|and)\s+)?not\s+', value, maxsplit=1, flags=re.I)
    if len(contrast) == 2:
        require(not any(name in key(contrast[1]) for name in SHARED),
                'answer negates a required shared producer')
        value = contrast[0]
    items = re.split(r'\s*(?:[,;&、]|\band\b|以及|和|与)\s*', value, flags=re.I)
    names = {key(item.strip(' \"\'`*.')) for item in items if item.strip(' \"\'`*.')}
    require(names and names <= SHARED, 'producer assertion contains an extra or unrecognized credited name')
    return names


def record_producers(answer):
    """Extract explicit JSON or Markdown producer fields plus remaining prose."""
    stripped = re.sub(r'^```(?:json)?\s*|\s*```$', '', answer.strip(), flags=re.I)
    if stripped.startswith(('{', '[')):
        def unique_record(pairs):
            record = {}
            for field, value in pairs:
                require(field not in record, 'duplicate JSON answer field')
                record[field] = value
            return record

        try:
            document = json.loads(stripped, object_pairs_hook=unique_record)
        except json.JSONDecodeError:
            document = None
        if document is not None:
            records = document if isinstance(document, list) else [document]
            names = set()
            for record in records:
                require(isinstance(record, dict), 'JSON answer requires named records')
                for field, value in record.items():
                    if producer_label(field):
                        names.update(asserted_names(value))
            require(names, 'JSON answer has no shared producer field')
            return names, ''

    names, prose, group = set(), [], []

    def consume_table(rows):
        if not rows:
            return
        separator = lambda row: all(re.fullmatch(r':?-+:?', cell.replace(' ', '')) for cell in row)
        if len(rows) > 1 and separator(rows[1]):
            columns = [i for i, cell in enumerate(rows[0]) if producer_label(cell)]
            if columns:
                for row in rows[2:]:
                    for column in columns:
                        require(column < len(row), 'missing table producer cell')
                        names.update(asserted_names(row[column]))
                return
        for row in rows:
            if row and producer_label(row[0]):
                require(len(row) == 2, 'producer field table requires a name-list value')
                names.update(asserted_names(row[1]))

    for line in answer.splitlines():
        if line.strip().startswith('|'):
            group.append([cell.strip() for cell in line.strip().strip('|').split('|')])
        else:
            consume_table(group)
            group = []
            prose.append(line)
    consume_table(group)
    return names, '\n'.join(prose)


def prose_producers(answer, movies):
    names, pending_list = set(), False
    # Remove list markers before sentence splitting: "1. Emma Thomas" is one
    # list item, not the narrative sentence "1" followed by another clause.
    answer = re.sub(r'(?m)^[ \t]*(?:[-*]|\d+[.)])[ \t]+', '', answer)
    clauses = re.split(r'[;；。\n]|\.(?=\s+[A-Z]|\s*$)', answer)
    for clause in clauses:
        clause = re.sub(r'^\s*(?:[-*]|\d+[.)])\s*', '', clause).strip().strip('*`')
        if not clause:
            continue
        # This is the other explicitly requested answer field, not a name-list
        # item. Its heading closes a multiline producer list.
        if key(clause).strip(' :：*`') == 'release date (streaming)':
            pending_list = False
            continue
        if (any(key(movie['title']) in key(clause) for movie in movies) and dates(clause)
                and not re.search(r'\bproducers?\b|制片人', clause, re.I)):
            pending_list = False
            continue
        has_required_name = any(name in key(clause) for name in SHARED)
        if has_required_name and re.search(r'\b(?:are\s+not|is\s+not|aren.t|isn.t|neither)\b|不是|并非|(?:没有|并无|无|非)\s*(?:共同|共有)?制片人', clause, re.I):
            require(False, 'answer negates a required shared producer')

        # Match a labelled value or a subject/predicate assertion. Introductory
        # clauses are outside the name slot; there is no ordinary-word whitelist.
        # Chinese narrative can directly precede 制片人; a Unicode word
        # boundary would wrongly treat that narrative as part of a name slot.
        label = re.search(r'(?<![A-Za-z0-9_])(?:' + PRODUCER_LABEL + r')\s*(?:(?:also\s+)?(?:are|is|include|includes)\b|[:：—-]|(?:也|还)?(?:是|为|包括|包含))\s*(.*)$', clause, re.I)
        if label:
            value = label.group(1)
        else:
            subject = re.fullmatch(
                r'(.+?)\s+(?:is|are|was|were)\s+(?:also\s+)?(?:(?:the|a|an|another)\s+)?(?:(?:shared|common|additional|extra)\s+)?producers?'
                r'(?:\s+(?:(?:credited|listed|shown)\s+)?(?:on|in|for)\s+(?:both|the two|these two)\s+(?:pages|movies|films|Movie Info sections))?\.?',
                clause, re.I)
            if not subject:
                subject = re.fullmatch(r'(.+?)\s*(?:也|还)?(?:是|为)\s*(?:共同|共有)?制片人', clause)
            if subject:
                value = subject.group(1)
                value = re.sub(r'^(?:after|before|when|while|having|from|based on|upon|according to)\b[^,]*,\s*', '', value, flags=re.I)
                value = re.sub(r'^I\s+(?:found|confirmed|observed)\s+that\s+', '', value, flags=re.I)
            elif producer_label(clause):
                pending_list = True
                continue
            else:
                additional = re.fullmatch(r'(?:also|additionally)[,:\s]+(.+)', clause, re.I)
                if additional:
                    value = additional.group(1)
                elif pending_list or has_required_name:
                    value = clause
                else:
                    continue
        if value.strip():
            names.update(asserted_names(value))
        pending_list = True
    return names


def check_answer(answer, movies=MOVIES):
    require(norm(answer), 'empty answer')
    require(paired_movie_dates(answer, movies),
            'missing, incorrect, contradictory or swapped movie/date pairing')
    names, prose = record_producers(answer)
    names.update(prose_producers(prose, movies))
    require(names == SHARED, 'complete shared producer intersection is missing')


def check_ui(run, movies=MOVIES):
    searches = []
    for frame in run.frames:
        if frame.path != '/search':
            continue
        params = parse_qs(urlsplit(frame.url).query)
        query = (params.get('q') or params.get('search') or [''])[0]
        if key(query) != 'christopher nolan':
            continue
        if run.supports(frame, lambda dom: heading(main_dom(dom), 'Search Results for')
                        and 'christopher nolan' in key(main_dom(dom)),
                        'The actual search results page visibly identifies the query Christopher Nolan. No particular result card must be opened.'):
            searches.append(frame.position)
    require(searches, 'the requested Christopher Nolan search was not observed')
    since = min(searches)
    run.evidence.append({'check': 'Christopher_Nolan_search', 'step': since // 2, 'path': '/search'})
    for movie in movies:
        run.prove('complete_producer_field_' + movie['slug'], {'/m/' + movie['slug']}, since,
                  lambda dom, movie=movie: detail_producers(dom, movie),
                  'The Movie Info Producer field lists exactly: ' + ', '.join(movie['producers']) + '.')
        run.prove('streaming_date_' + movie['slug'], {'/m/' + movie['slug']}, since,
                  lambda dom, movie=movie: detail_date(dom, movie['date']),
                  'The Movie Info Release Date (Streaming) is ' + movie['date'] + '.')


def evaluate(run_dir, initial_db=None, after_db=None, no_llm=False):
    run = None
    try:
        run = Run(run_dir, CONTRACTS[TASK_ID], no_llm=no_llm)
        before_path = initial_db or (Path(run_dir) / 'before.db' if (Path(run_dir) / 'before.db').is_file() else Path(run_dir) / 'initial.db')
        before, after = Snapshot(before_path), Snapshot(after_db or Path(run_dir) / 'after.db')
        read_only(before, after)
        for movie in MOVIES:
            row = before.one('movies', slug=movie['slug'])
            require(row['title'] == movie['title'], 'source movie identity mismatch')
        check_answer(run.data['final_answer'])
        check_ui(run)
        return {'task_id': TASK_ID, 'pass': True, 'reason': 'Search, both Movie Info pages, complete intersection and paired dates are evidenced; business state is unchanged.', 'evidence': run.evidence}
    except (VerificationError, OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, sqlite3.Error) as error:
        return {'task_id': TASK_ID, 'pass': False, 'reason': str(error), 'evidence': run.evidence if run else []}


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_dir', required=True)
    parser.add_argument('--initial_db')
    parser.add_argument('--after_db')
    parser.add_argument('--no_llm', nargs='?', const='true', default='false', choices=('true', 'false', 'True', 'False'))
    args = parser.parse_args()
    result = evaluate(args.run_dir, args.initial_db, args.after_db, args.no_llm.lower() == 'true')
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    cli()
