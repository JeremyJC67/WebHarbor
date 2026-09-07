"""Offline source/seed regression tests in isolated copies of the real site.

Run: python -m unittest discover -s sites/rotten_tomatoes/tests -p test_source_catalog.py -v
ROTTEN_TOMATOES_SOURCE may point to a candidate site directory.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SourceCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('ROTTEN_TOMATOES_SOURCE', Path(__file__).resolve().parents[1]))
        cls.scratch = tempfile.TemporaryDirectory(prefix='rotten-source-contract-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        for name in ('app.py', 'seed_data.py', 'refresh_seed.py'):
            shutil.copy2(source / name, cls.root / name)
        shutil.copytree(source / 'data', cls.root / 'data')
        previous_seed = sys.modules.get('seed_data')
        cls.seed = load_module('seed_data', cls.root / 'seed_data.py')
        try:
            cls.migration = load_module('_rotten_source_migration', cls.root / 'refresh_seed.py')
            cls.site = load_module('_rotten_source_app', cls.root / 'app.py')
        finally:
            if previous_seed is None:
                sys.modules.pop('seed_data', None)
            else:
                sys.modules['seed_data'] = previous_seed
        cls.addClassCleanup(sys.modules.pop, '_rotten_source_migration', None)
        cls.addClassCleanup(sys.modules.pop, '_rotten_source_app', None)
        cls.catalog_path = cls.root / 'data' / 'source_catalog.json'
        cls.catalog = cls.seed.load_catalog(cls.catalog_path)
        cls.cold_db = cls.root / 'instance' / 'rotten_tomatoes.db'
        with cls.site.app.app_context():
            cls.site.db.session.remove()
            cls.site.db.engine.dispose()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)

    def clone_cold(self, name='legacy.db'):
        target = self.directory / name
        with sqlite3.connect(self.cold_db.as_uri() + '?mode=ro', uri=True) as source:
            with sqlite3.connect(target) as output:
                source.backup(output)
        return target

    def assert_catalog_projection(self, path):
        rows = self.seed.catalog_rows(self.catalog)
        with sqlite3.connect(path) as connection:
            for table, expected in rows.items():
                columns = list(expected[0])
                actual = connection.execute(f'SELECT {",".join(columns)} FROM {table}').fetchall()
                expected_values = [tuple(row[key] for key in columns) for row in expected]
                self.assertEqual(sorted(actual), sorted(expected_values), table)
            self.assertEqual(connection.execute('SELECT count(*) FROM critic_reviews').fetchone()[0], 0)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_cold_seed_is_exact_catalog_projection(self):
        self.assert_catalog_projection(self.cold_db)
        with sqlite3.connect(self.cold_db) as connection:
            missing = sum(movie['audience_score'] is None for movie in self.catalog['movies'])
            self.assertGreater(missing, 0)
            self.assertEqual(connection.execute('SELECT count(*) FROM movies WHERE audience_score IS NULL').fetchone()[0], missing)
            self.assertEqual(connection.execute('SELECT count(*) FROM audience_reviews').fetchone()[0], 23)
            self.assertEqual(connection.execute('SELECT count(*) FROM users').fetchone()[0], 4)
            self.assertEqual(connection.execute('SELECT count(*) FROM watchlist_items').fetchone()[0], 16)
            self.assertEqual(connection.execute('SELECT count(*) FROM user_ratings').fetchone()[0], 12)

    def test_known_source_regressions_and_distinct_watch_semantics(self):
        movies = {movie['slug']: movie for movie in self.catalog['movies']}
        referenced = {credit['person_slug'] for movie in self.catalog['movies'] for credit in movie['credits']}
        self.assertEqual(referenced, {person['slug'] for person in self.catalog['persons']})
        self.assertEqual({credit['role'] for movie in self.catalog['movies'] for credit in movie['credits']},
                         {'actor', 'director', 'producer', 'screenwriter'})
        unknown_producer = next(person for person in self.catalog['persons']
                                if person['slug'] == 'source-credit-m82-producer-1')
        self.assertEqual(unknown_producer['name'], 'Reto Schärli')
        self.assertIsNone(unknown_producer['source_url'])
        self.assertFalse(any(person['slug'] == 'undefined' for person in self.catalog['persons']))
        self.assertEqual((movies['marty_supreme']['year'], movies['marty_supreme']['runtime_minutes']), (2025, 150))
        self.assertEqual((movies['cold_storage_2026']['year'], movies['cold_storage_2026']['runtime_minutes']), (2026, 99))
        self.assertEqual(set(movies['cold_storage_2026']['genres']), {'Horror', 'Sci-Fi', 'Comedy'})
        for movie, forbidden in [('lifehack', {'zendaya','timothee_chalamet'}),
                                 ('cold_storage_2026', {'mark_wahlberg','halle_berry'})]:
            actors = {credit['person_slug'] for credit in movies[movie]['credits'] if credit['role'] == 'actor'}
            self.assertFalse(actors & forbidden)
        self.assertEqual(movies['cold_storage_2026']['subscription_platforms'], [])
        self.assertTrue(movies['cold_storage_2026']['watch_offers'])
        with sqlite3.connect(self.cold_db) as connection:
            self.assertEqual(connection.execute("SELECT streaming_platform, available_at_home FROM movies WHERE slug='cold_storage_2026'").fetchone(), ('', 1))
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM persons WHERE bio<>'' OR birthplace<>'' OR birth_date<>''").fetchone()[0], 0)

    def test_existing_database_seed_returns_without_loading_catalog_or_commit(self):
        before = self.migration.sha256(self.cold_db)
        with self.site.app.app_context():
            with patch.object(self.seed, 'load_catalog', side_effect=AssertionError('Loaded catalog on populated DB')):
                with patch.object(self.site.db.session, 'commit', side_effect=AssertionError('Committed on populated DB')):
                    self.seed.seed_all(self.site.db, self.site.Genre, self.site.Movie, self.site.Person,
                                       self.site.MovieCast, self.site.CriticReview, self.site.AudienceReview,
                                       self.site.User, self.site.UserRating, self.site.WatchlistItem)
            self.site.db.session.remove()
            self.site.db.engine.dispose()
        self.assertEqual(before, self.migration.sha256(self.cold_db))

    def test_migration_preserves_state_and_rebuilds_the_same_facts(self):
        source = self.clone_cold()
        with sqlite3.connect(source) as connection:
            connection.execute("UPDATE movies SET runtime_minutes=7, runtime_display='9h', synopsis='Invented placeholder', streaming_platform='Unverified Provider'")
            review = connection.execute('SELECT movie_id,user_id,score,text FROM audience_reviews WHERE id=2').fetchone()
            # Simulate the legacy schema, which allowed duplicate synthetic reviews.
            connection.execute('ALTER TABLE audience_reviews RENAME TO legacy_audience_reviews')
            connection.execute('CREATE TABLE audience_reviews(id INTEGER PRIMARY KEY,movie_id INTEGER NOT NULL,user_id INTEGER NOT NULL,score FLOAT,text TEXT,review_date DATETIME)')
            connection.execute('INSERT INTO audience_reviews SELECT * FROM legacy_audience_reviews')
            connection.execute('DROP TABLE legacy_audience_reviews')
            connection.execute('INSERT INTO audience_reviews VALUES (?,?,?,?,?,?)', (999, *review, '2000-01-01 00:00:00'))
        before = self.migration.sha256(source)
        output = self.directory / 'migrated.db'
        receipt = self.migration.migrate_copy(source, output, self.catalog_path, deduplicate=True)
        self.assertEqual(receipt['removed_review_ids'], [999])
        self.assertEqual(receipt['state_hashes_before'], receipt['state_hashes_after'])
        self.assertEqual(receipt['audience_reviews_after'], 23)
        self.assertEqual(before, self.migration.sha256(source))
        self.assert_catalog_projection(output)
        output_hash = self.migration.sha256(output)
        repeated = self.migration.migrate_copy(source, output, self.catalog_path, deduplicate=True)
        self.assertEqual(repeated['status'], 'already_migrated')
        self.assertEqual(output_hash, self.migration.sha256(output))

    def test_wrong_movie_identity_fails_without_output_or_source_changes(self):
        source = self.clone_cold()
        catalog = json.loads(self.catalog_path.read_text())
        catalog['movies'][0]['slug'] = 'different-film'
        invalid = self.directory / 'invalid.json'
        invalid.write_text(json.dumps(catalog))
        before = self.migration.sha256(source)
        output = self.directory / 'rejected.db'
        with self.assertRaisesRegex(ValueError, 'every existing movie ID and slug'):
            self.migration.migrate_copy(source, output, invalid)
        self.assertFalse(output.exists())
        self.assertEqual(before, self.migration.sha256(source))


if __name__ == '__main__':
    unittest.main()
