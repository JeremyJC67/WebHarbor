"""Synthetic contract fixtures only; these are NOT original or revised UI runs."""
import base64
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

# Copy this file beside verify_0.py and run: python test_date_contracts.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_0 as r0
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/Y9sAAAAASUVORK5CYII=')
ORIGIN = 'http://r0-fixture.localhost:40019'
def table(title='War Machine', date='Mar 6, 2026', writers='Patrick Hughes and James Beaufort'):
    return f'| Movie | Release Date (Streaming) | Screenwriter(s) |\n|---|---|---|\n| {title} | {date} | {writers} |'

ANSWER = table()


def listing():
    return '- main:\n  - heading "Streaming at Home" [level=1]\n  - combobox "Genre:":\n    - option "Sci-Fi" [selected]\n  - combobox "Subscription Platform:":\n    - option "Netflix" [selected]\n' + ''.join(f'  - link "{m["title"]}":\n    - /url: /m/{m["slug"]}\n' for m in r0.CANDIDATES)


def detail(movie):
    date_field = f'  - generic: Release Date (Streaming)\n  - generic: {movie["date"]}\n' if movie['date'] is not None else ''
    return f'- main:\n  - heading "{movie["title"]}" [level=1]\n  - heading "Movie Info" [level=3]\n  - generic: Screenwriter\n  - generic: {", ".join(movie["writers"])}\n{date_field}  - generic: Runtime\n  - generic: 2h\n  - heading "Cast & Crew" [level=2]\n'


def fixture(directory, visited=None, answer=ANSWER, reverse=False, bad_field=None, entry_method="click", has_scope=True):
    directory = Path(directory)
    (directory / 'screenshots').mkdir()
    (directory / 'observations').mkdir()
    with sqlite3.connect(directory / 'before.db') as db:
        db.executescript('CREATE TABLE movies(id INTEGER PRIMARY KEY,slug TEXT,title TEXT,release_date_streaming TEXT,screenwriter TEXT,available_at_home BOOLEAN,streaming_platform TEXT); CREATE TABLE genres(id INTEGER PRIMARY KEY,name TEXT); CREATE TABLE movie_genres(movie_id INTEGER,genre_id INTEGER); CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT); INSERT INTO genres VALUES(1,"Sci-Fi"); INSERT INTO users VALUES(1,"unchanged fixture user");')
        for i, m in enumerate(r0.CANDIDATES, 1):
            db.execute('INSERT INTO movies VALUES(?,?,?,?,?,?,?)', (i,m['slug'],m['title'],m['date'],', '.join(m['writers']),1,'Netflix'))
            db.execute('INSERT INTO movie_genres VALUES(?,1)', (i,))
    shutil.copy2(directory / 'before.db', directory / 'after.db')
    home = '- main:\n  - heading "Rotten Tomatoes" [level=1]\n  - link "Streaming at Home":\n    - /url: /browse/movies_at_home/\n'
    current = (ORIGIN+'/',home)
    steps=[]
    def step(action, params, destination):
        nonlocal current
        i=len(steps)
        row={'step':i,'action':action,'params':params,'action_result':{'success':True},'url':current[0],'url_after':destination[0]}
        for side,item,n in [('before',current,2*i),('after',destination,2*i+1)]:
            name=f'step_{n:03d}'
            row['screenshot_'+side]='screenshots/'+name+'.png'
            (directory/'screenshots'/f'{name}.png').write_bytes(PNG)
            (directory/'observations'/f'{name}.txt').write_text(item[1])
        steps.append(row);current=destination
    step('goto',{'url':ORIGIN+'/'},current)
    browse=(ORIGIN+'/browse/movies_at_home/?genre=sci-fi&platform=Netflix',listing()) if has_scope else (
        ORIGIN+'/browse/movies/',listing().replace('Streaming at Home','All Movies').replace('[selected]',''))
    step('click',{'label':'Streaming at Home' if has_scope else 'All Movies'},(ORIGIN+'/browse/movies_at_home/' if has_scope else ORIGIN+'/browse/movies/',listing().replace('[selected]','').replace('Streaming at Home','Streaming at Home' if has_scope else 'All Movies')))
    step('select',{'label':'Genre','value':'sci-fi'},browse)
    movies=list(r0.CANDIDATES if visited is None else visited)
    if reverse:movies.reverse()
    for m in movies:
        dom=detail(m)
        if bad_field == m['slug']:
            dom=dom.replace('Release Date (Streaming)','Release Date (Theaters)')
        destination=ORIGIN+'/m/'+m['slug']
        params={'url':destination} if entry_method in ('goto','navigate') else (
            {'key':'Enter','label':m['title']} if entry_method in ('press','keypress') else {'label':m['title']})
        step(entry_method,params,(destination,dom))
        step('back',{},browse)
    step('done',{'text':answer,'success':True},current)
    (directory/'trajectory.json').write_text(json.dumps({'task_id':r0.TASK_ID,'task':r0.CONTRACTS[r0.TASK_ID]['prompt'],'start_url':ORIGIN+'/','final_answer':answer,'steps':steps}))
    (directory/'FIXTURE-NOT-A-REAL-RUN.txt').write_text('Synthetic fixture built from the public task contract and source facts. No browser was run. Never include in UI outcome counts.\n')


class R0Tests(unittest.TestCase):
    def run_fixture(self, expected, **kwargs):
        with tempfile.TemporaryDirectory(prefix='r0-fixture-') as d:
            fixture(d,**kwargs)
            result=r0.evaluate(d,no_llm=True)
            self.assertEqual(result['pass'],expected,result)
            return result

    def test_full_comparison_in_either_order_and_date_formats(self):
        self.run_fixture(True)
        self.run_fixture(True,reverse=True,answer=table(date='6 March 2026'))
        self.run_fixture(True,answer=table(date='2026年3月6日'))
        self.run_fixture(True,answer=table(date='2026-03-06'))
        value=[{'title':'War Machine','date':'Mar 6, 2026','screenwriters':['James Beaufort','Patrick Hughes']}]
        self.run_fixture(True,answer=json.dumps(value))
        self.run_fixture(True,answer='After reviewing all 8 Netflix Sci-Fi movies in Streaming at Home, this is the latest result.\n'+ANSWER+'\nI compared the calendar dates shown in Movie Info.')
        self.run_fixture(True,answer='After comparing the streaming dates, here is the result.\n```json\n'+json.dumps(value)+'\n```\nAll listed screenwriters are included.')

    def test_correct_answer_without_complete_comparison_fails(self):
        self.run_fixture(False,visited=[])
        self.run_fixture(False,visited=r0.CANDIDATES[:1])
        self.run_fixture(False,visited=r0.CANDIDATES[:-1])

    def test_labeled_streaming_field_is_required(self):
        self.run_fixture(False,bad_field=next(m['slug'] for m in reversed(r0.CANDIDATES) if m['date'] is not None))

    def test_equivalent_same_origin_navigation_is_valid(self):
        # Earlier scoring incorrectly rejected these routes although the public
        # task specifies scope/comparison evidence, not mouse-only discovery.
        for method in ['goto', 'navigate', 'press', 'keypress']:
            with self.subTest(method=method):
                self.run_fixture(True,entry_method=method,reverse=True)

    def test_navigation_does_not_substitute_for_scope_or_comparison(self):
        self.run_fixture(False,entry_method='goto',has_scope=False)
        self.run_fixture(False,entry_method='navigate',visited=r0.CANDIDATES[:1])
        self.run_fixture(False,entry_method='press',visited=[])

    def test_cross_origin_frames_remain_invalid(self):
        with tempfile.TemporaryDirectory(prefix='r0-fixture-') as d:
            fixture(d,entry_method='goto')
            p=Path(d)/'trajectory.json';data=json.loads(p.read_text())
            data['steps'][3]['url_after']='http://other-fixture.localhost:40019/m/'+r0.CANDIDATES[0]['slug']
            p.write_text(json.dumps(data))
            result=r0.evaluate(d,no_llm=True)
            self.assertFalse(result['pass'])
            self.assertIn('cross-origin',result['reason'])

    def test_wrong_dates_missing_and_extra_facts(self):
        for answer in [table(date='May 21, 2026'),
                       table(writers=''), table(writers='Patrick Hughes and Jane Doe'),
                       ANSWER+'\nScreenwriter: Jane Doe.',
                       ANSWER+'\n| Touch Me | Apr 7, 2026 | Addison Heimann |',
                       ANSWER+'\n| Alien | May 12, 2026 | Dan O Bannon |',
                       table(title='Project Hail Mary and Alien'),
                       'Project Hail Mary and Alien — May 12, 2026 — Drew Goddard.',
                       'Not War Machine.\n'+ANSWER,
                       ANSWER+'\nIts date is June 1, 2026.']:

            with self.subTest(answer=answer):self.run_fixture(False,answer=answer)

    def test_schema_and_all_table_state_unchanged(self):
        with tempfile.TemporaryDirectory(prefix='r0-fixture-') as d:
            fixture(d)
            with sqlite3.connect(Path(d)/'after.db') as db:db.execute('UPDATE users SET name="changed"')
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_all_ties_all_writers_and_date_pairing(self):
        tied=[{'title':'One Film','date':'2026-05-12','writers':['Alpha Writer','Beta Writer']}, {'title':'Second Film','date':'2026-05-12','writers':['Gamma Writer']}]
        good=[{'title':'One Film','date':'May 12, 2026','screenwriters':['Beta Writer','Alpha Writer']},{'title':'Second Film','date':'12 May 2026','screenwriters':['Gamma Writer']}]
        r0.check_records(good,tied)
        for join in [', ', ' and ', ' & ', '; ', ' / ', '、', '和', '<br>']:
            answer=table(title='One Film',date='May 12, 2026',writers=join.join(['Beta Writer','Alpha Writer']))+'\n| Second Film | 12 May 2026 | Gamma Writer |'
            r0.check_answer(answer,tied,[m['title'] for m in tied])
        for wrong in [good[:1],good+[good[0]],[dict(good[0],screenwriters=['Alpha Writer']),good[1]],[dict(good[0],date='June 1, 2026'),good[1]],[dict(good[0],screenwriters=['Gamma Writer']),dict(good[1],screenwriters=['Alpha Writer','Beta Writer'])]]:
            with self.assertRaises(r0.VerificationError):r0.check_records(wrong,tied)

    def test_calendar_maximum_ties_are_computed_not_position_or_text_sort(self):
        toy = [
            {'slug':'older','title':'Older Movie','date':'2025-12-31','writers':['Older Writer']},
            {'slug':'one_film','title':'One Film','date':'2026-06-01','writers':['Alpha Writer','Beta Writer']},
            {'slug':'second_film','title':'Second Film','date':'2026-06-01','writers':['Gamma Writer']},
            {'slug':'third','title':'Third Movie','date':'2026-05-12','writers':['Third Writer']},
        ]
        answer=json.dumps([{'title':m['title'],'date':m['date'],'screenwriters':m['writers']} for m in toy[1:3]])
        with patch.object(r0,'CANDIDATES',toy):
            self.run_fixture(True,reverse=True,answer=answer)
            self.run_fixture(False,answer=json.dumps([{'title':'Third Movie','date':'2026-05-12','screenwriters':['Third Writer']}]))

    def test_empty_browser_and_missing_screenshot_fail(self):
        with tempfile.TemporaryDirectory(prefix='r0-fixture-') as d:
            fixture(d)
            path=Path(d)/'screenshots/step_007.png'
            path.unlink()
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])
        with tempfile.TemporaryDirectory(prefix='r0-fixture-') as d:
            fixture(d)
            p=Path(d)/'trajectory.json';data=json.loads(p.read_text());data['steps']=[];p.write_text(json.dumps(data))
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_explicit_records_cannot_hide_unknown_movies_or_alias_fields(self):
        movie=r0.CANDIDATES[0]
        for rows in [
            [{'title':'Project Hail Mary and Alien','date':movie['date'],'screenwriters':movie['writers']}],
            [{'title':movie['title'],'date':movie['date'],'screenwriters':movie['writers']}, {'title':'Alien','date':movie['date'],'screenwriters':movie['writers']}],
            [{'title':movie['title'],'movie':'Alien','date':movie['date'],'screenwriters':movie['writers']}],
            [{'title':movie['title'],'date':movie['date'],'release_date_streaming':'2000-01-01','screenwriters':movie['writers']}],
        ]:
            with self.assertRaises(r0.VerificationError):r0.check_records(rows,[movie])


if __name__=='__main__':unittest.main(verbosity=2)
