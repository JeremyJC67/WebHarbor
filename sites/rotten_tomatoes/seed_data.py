"""Build the offline movie database from one captured public source catalog.

Movie facts are in data/source_catalog.json. The separate benchmark constants
below are synthetic local users and their state, not Rotten Tomatoes reviews.
Existing databases are never changed at application startup. Refresh an existing
seed only with the explicit offline refresh_seed.py command.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / 'data' / 'source_catalog.json'


def load_catalog(path=CATALOG_PATH):
    catalog = json.loads(Path(path).read_text(encoding='utf-8'))
    if catalog.get('schema_version') != 1:
        raise ValueError('Unsupported source catalog schema')
    ids = [movie['id'] for movie in catalog['movies']]
    slugs = [movie['slug'] for movie in catalog['movies']]
    if len(set(ids)) != len(ids) or len(set(slugs)) != len(slugs):
        raise ValueError('Duplicate movie identity in source catalog')
    person_slugs = [person['slug'] for person in catalog['persons']]
    if len(set(person_slugs)) != len(person_slugs):
        raise ValueError('Duplicate person identity in source catalog')
    for person in catalog['persons']:
        source = person['source_url']
        if source is not None and (source != 'https://www.rottentomatoes.com/celebrity/' + person['slug']
                                   or person['slug'] == 'undefined'):
            raise ValueError('Invalid public person URL; use a local identity with a null source URL')
    credits = [credit for movie in catalog['movies'] for credit in movie['credits']]
    if {credit['person_slug'] for credit in credits} != set(person_slugs):
        raise ValueError('Every catalog person must be referenced by an accepted credit')
    if any(credit['role'] not in ('actor', 'director', 'producer', 'screenwriter') for credit in credits):
        raise ValueError('Unsupported source credit role')
    return catalog


def runtime_display(minutes):
    if minutes is None:
        return ''
    hours, remainder = divmod(minutes, 60)
    return f'{hours}h {remainder}m' if hours else f'{remainder}m'


def joined(values):
    return ', '.join(values) if values else ''


def catalog_rows(catalog):
    """One projection shared by cold seeding and explicit SQLite migration."""
    genre_names = sorted({name for movie in catalog['movies'] for name in movie['genres']})
    genres = [{'id': index, 'name': name, 'slug': name.lower().replace(' & ', '_').replace(' ', '_')}
              for index, name in enumerate(genre_names, 1)]
    genre_ids = {row['name']: row['id'] for row in genres}
    persons = [{'id': person['id'], 'slug': person['slug'], 'name': person['name'],
                'photo': person['photo_path'], 'bio': '', 'birthplace': '', 'birth_date': ''}
               for person in catalog['persons']]
    person_ids = {row['slug']: row['id'] for row in persons}
    movies, movie_genres, movie_cast = [], [], []
    for movie in catalog['movies']:
        offers = movie['watch_offers']
        movies.append({
            'id': movie['id'], 'slug': movie['slug'], 'title': movie['title'],
            'year': movie['year'], 'runtime_minutes': movie['runtime_minutes'],
            'runtime_display': runtime_display(movie['runtime_minutes']),
            'synopsis': movie['synopsis'] or '',
            'poster_image': f'/static/images/posters/{movie["slug"]}.jpg' if movie['poster_url'] else '',
            'tomatometer': movie['tomatometer'], 'audience_score': movie['audience_score'],
            'certified_fresh': movie['certified_fresh'], 'pg_rating': movie['pg_rating'] or '',
            'director_name': joined(movie['directors']), 'producer': joined(movie['producers']),
            'screenwriter': joined(movie['screenwriters']),
            'production_co': joined(movie['production_companies']),
            'studio': movie['distributor'] or '', 'distributor': movie['distributor'] or '',
            'original_language': movie['original_language'] or '',
            'release_date': movie['release_date_theaters'] or '',
            'release_date_streaming': movie['release_date_streaming'] or '',
            'streaming_platform': joined(movie['subscription_platforms']),
            'watch_offers': json.dumps(offers, ensure_ascii=False) if offers is not None else None,
            'watch_description': movie['watch_description'],
            'available_at_home': bool(offers),
            # This is availability in the captured RT listing, not a global claim.
            'in_theaters': movie['has_showtimes'] is True,
            'consensus': '', 'audience_consensus': '', 'box_office': '',
        })
        movie_genres.extend({'movie_id': movie['id'], 'genre_id': genre_ids[name]}
                            for name in movie['genres'])
        for credit in movie['credits']:
            movie_cast.append({'id': len(movie_cast) + 1, 'movie_id': movie['id'],
                               'person_id': person_ids[credit['person_slug']],
                               'role_type': credit['role'], 'character_name': credit['character'] or '',
                               'billing_order': credit['order']})
    return {'movies': movies, 'genres': genres, 'persons': persons,
            'movie_genres': movie_genres, 'movie_cast': movie_cast}


def seed_all(db, Genre, Movie, Person, MovieCast, CriticReview, AudienceReview,
             User, UserRating, WatchlistItem):
    """Create only an empty database; a populated database is a read-only no-op."""
    if Movie.query.first() is not None:
        return
    if any(model.query.first() is not None for model in (Genre, Person, User)):
        raise ValueError('Partial database: use the explicit offline migration command')
    from flask_bcrypt import Bcrypt
    from sqlalchemy import null

    rows = catalog_rows(load_catalog())
    model_tables = [('genres', Genre), ('persons', Person), ('movies', Movie), ('movie_cast', MovieCast)]
    objects = {}
    for table, model in model_tables:
        created = []
        for row in rows[table]:
            # SQLAlchemy Python-side defaults would otherwise turn explicit None
            # scores into zero. SQL NULL preserves the captured unknown value.
            instance = model(**{key: null() if value is None else value for key, value in row.items()})
            db.session.add(instance)
            created.append(instance)
        db.session.flush()
        objects[table] = created
    movie_map = {movie.slug: movie for movie in objects['movies']}
    genre_map = {genre.id: genre for genre in objects['genres']}
    movies_by_id = {movie.id: movie for movie in objects['movies']}
    for relation in rows['movie_genres']:
        movies_by_id[relation['movie_id']].genres.append(genre_map[relation['genre_id']])

    bcrypt = Bcrypt()
    user_map = {}
    for index, user in enumerate(USERS, 1):
        instance = User(id=index, email=user['email'], name=user['username'],
                        password_hash=bcrypt.generate_password_hash(user['password']).decode('utf-8'))
        db.session.add(instance)
        user_map[user['username']] = instance
    db.session.flush()
    for review in AUDIENCE_REVIEWS:
        db.session.add(AudienceReview(id=review['id'], movie_id=movie_map[review['movie_slug']].id,
                                      user_id=user_map['alice_jones'].id,
                                      score=review['rating'], text=review['text']))
    for index, rating in enumerate(USER_RATINGS, 1):
        db.session.add(UserRating(id=index, user_id=user_map[rating['username']].id,
                                  movie_id=movie_map[rating['movie_slug']].id, score=rating['score']))
    for index, item in enumerate(WATCHLIST_ITEMS, 1):
        db.session.add(WatchlistItem(id=index, user_id=user_map[item['username']].id,
                                     movie_id=movie_map[item['movie_slug']].id))
    db.session.commit()


# BENCHMARK_FIXTURE: explicitly synthetic local account/review state.

USERS = [{'username': 'alice_jones', 'email': 'alice.j@test.com', 'password': 'TestPass123!'},
 {'username': 'bob_clark', 'email': 'bob.c@test.com', 'password': 'TestPass123!'},
 {'username': 'carol_davis', 'email': 'carol.d@test.com', 'password': 'TestPass123!'},
 {'username': 'david_kim', 'email': 'david.k@test.com', 'password': 'TestPass123!'}]

WATCHLIST_ITEMS = [{'username': 'alice_jones', 'movie_slug': 'dune_part_two'},
 {'username': 'alice_jones', 'movie_slug': 'the_wild_robot'},
 {'username': 'alice_jones', 'movie_slug': 'wicked_2024'},
 {'username': 'alice_jones', 'movie_slug': 'inside_out_2'},
 {'username': 'bob_clark', 'movie_slug': 'the_dark_knight'},
 {'username': 'bob_clark', 'movie_slug': 'interstellar_2014'},
 {'username': 'bob_clark', 'movie_slug': 'oppenheimer_2023'},
 {'username': 'bob_clark', 'movie_slug': 'sinners_2025'},
 {'username': 'carol_davis', 'movie_slug': 'barbie'},
 {'username': 'carol_davis', 'movie_slug': 'everything_everywhere_all_at_once'},
 {'username': 'carol_davis', 'movie_slug': 'the_substance'},
 {'username': 'carol_davis', 'movie_slug': 'nosferatu_2024'},
 {'username': 'david_kim', 'movie_slug': 'avengers_endgame'},
 {'username': 'david_kim', 'movie_slug': 'deadpool_and_wolverine'},
 {'username': 'david_kim', 'movie_slug': 'superman_2025'},
 {'username': 'david_kim', 'movie_slug': 'the_fantastic_four_first_steps'}]

USER_RATINGS = [{'username': 'alice_jones', 'movie_slug': 'parasite_2019', 'score': 5},
 {'username': 'alice_jones', 'movie_slug': 'everything_everywhere_all_at_once', 'score': 5},
 {'username': 'alice_jones', 'movie_slug': 'barbie', 'score': 4},
 {'username': 'bob_clark', 'movie_slug': 'the_dark_knight', 'score': 5},
 {'username': 'bob_clark', 'movie_slug': 'top_gun_maverick', 'score': 5},
 {'username': 'bob_clark', 'movie_slug': 'interstellar_2014', 'score': 5},
 {'username': 'carol_davis', 'movie_slug': 'the_substance', 'score': 4},
 {'username': 'carol_davis', 'movie_slug': 'nosferatu_2024', 'score': 4},
 {'username': 'carol_davis', 'movie_slug': 'oddity', 'score': 5},
 {'username': 'david_kim', 'movie_slug': 'avengers_endgame', 'score': 5},
 {'username': 'david_kim', 'movie_slug': 'godzilla_minus_one', 'score': 5},
 {'username': 'david_kim', 'movie_slug': 'deadpool_and_wolverine', 'score': 4}]

AUDIENCE_REVIEWS = [{'movie_slug': 'avengers_endgame',
  'user': 'Angel G',
  'text': 'Absolute cinema! 🙏🏼',
  'rating': 5,
  'id': 2},
 {'movie_slug': 'godzilla_minus_one',
  'user': 'Patrick V',
  'text': 'Best Godzilla movie ever made. Earned the special effects Oscar, and also has an '
          'excellent human story.',
  'rating': 5,
  'id': 3},
 {'movie_slug': 'top_gun_maverick',
  'user': 'Patricia P',
  'text': 'Probably the best sequel ever made or a close second. Everything about this movie is '
          'amazing.',
  'rating': 5,
  'id': 5},
 {'movie_slug': 'the_dark_knight',
  'user': 'Ricardo',
  'text': 'Absolute cinema, Heath Ledger is the best joker and Christian Bale is the best Batman '
          'there is.',
  'rating': 5,
  'id': 7},
 {'movie_slug': 'oppenheimer_2023',
  'user': 'Jesus',
  'text': "Watched it for the 5th time. Will watch it more as long as it's re-released in "
          'theaters.',
  'rating': 5,
  'id': 9},
 {'movie_slug': 'barbie',
  'user': 'Luie',
  'text': 'Such a beautiful representation of what it is to be a woman!!!',
  'rating': 5,
  'id': 10},
 {'movie_slug': 'parasite_2019',
  'user': 'Brandon',
  'text': 'Perfect Film!!! Simply a Masterpiece!!!!',
  'rating': 5,
  'id': 12},
 {'movie_slug': 'sinners_2025',
  'user': 'Lysah',
  'text': 'life changing omg. saw it 4 times',
  'rating': 5,
  'id': 13},
 {'movie_slug': 'dune_part_two',
  'user': 'Joseph',
  'text': 'Epic!! Visually stunning',
  'rating': 5,
  'id': 14},
 {'movie_slug': 'inside_out_2',
  'user': 'Sergio Z',
  'text': 'Not as great as the first but definitely good.',
  'rating': 4,
  'id': 15},
 {'movie_slug': 'everything_everywhere_all_at_once',
  'user': 'Carlos',
  'text': 'I cried my eyes out, love it!',
  'rating': 5,
  'id': 16},
 {'movie_slug': 'the_substance',
  'user': 'Ryan M',
  'text': "I don't know what I thought this movie would be like, but it exceeded my expectations. "
          'That last act is gonzo!',
  'rating': 5,
  'id': 17},
 {'movie_slug': 'nosferatu_2024',
  'user': 'Lexie B',
  'text': 'Peak immersive, cinematic storytelling. Monsters girlies win',
  'rating': 4,
  'id': 18},
 {'movie_slug': 'deadpool_and_wolverine',
  'user': 'Morgan P',
  'text': 'Best Marvel movie hands down. The only one I revisit semi-annually because of how great '
          'and entertaining it is.',
  'rating': 5,
  'id': 19},
 {'movie_slug': 'wicked_2024',
  'user': 'kassandra',
  'text': 'This movie is my life 🤩',
  'rating': 5,
  'id': 20},
 {'movie_slug': 'interstellar_2014',
  'user': 'Tyler',
  'text': "Interstellar is not just a movie, it's an odyssey. From action to tension, the story "
          'shows the resilience of humanity across time and space.',
  'rating': 5,
  'id': 21},
 {'movie_slug': 'anaconda_2025',
  'user': 'Alanna T',
  'text': 'Jack Black and Paul Rudd match made in heaven.',
  'rating': 4,
  'id': 22},
 {'movie_slug': 'the_wild_robot',
  'user': 'Chad W',
  'text': 'An instant classic animated/digital or otherwise. The uniquely refreshing visuals '
          "complement the story's source material.",
  'rating': 5,
  'id': 23},
 {'movie_slug': 'shrek',
  'user': 'Timothy W',
  'text': "I typically don't care for Dreamworks snarky animation, but this one is snarky with "
          'heart, and it was done well!',
  'rating': 4,
  'id': 24},
 {'movie_slug': 'lilo_and_stitch',
  'user': 'Chris P',
  'text': "Lilo & Stitch might not always be the first title people name when listing Disney's "
          'greats, but it absolutely deserves a spot among them.',
  'rating': 5,
  'id': 25},
 {'movie_slug': 'blackberry',
  'user': 'Del',
  'text': 'Really enlightening film about the rise and fall of the BlackBerry company. '
          'Surprisingly funny as well.',
  'rating': 5,
  'id': 26},
 {'movie_slug': 'superman_2025',
  'user': 'Marie',
  'text': "I don't care what anyone says about this movie it made me cry because I felt like "
          'Superman was finally back!!',
  'rating': 5,
  'id': 27},
 {'movie_slug': 'the_fantastic_four_first_steps',
  'user': 'Hunter',
  'text': "Awesome movie, finally one worthy of the Fantastic Four's storied history",
  'rating': 5,
  'id': 28}]
