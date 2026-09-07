"""Task identity and publicly specified inputs. Answers belong in per-task verifiers."""

CONTRACTS = {'RottenTomatoes--0': {'task_id': 'RottenTomatoes--0',
                       'prompt': 'Browse the Sci-Fi movies in Streaming at Home with Subscription Platform set to Netflix. Among movies whose Movie Info section has a Release Date (Streaming), identify the movie with the latest such date. Report its title, that date, and all names listed under Screenwriter. If several movies share the latest date, report each of them. Ignore movies without this date. Return the results as a table with columns Movie, Release Date (Streaming), and Screenwriter(s), one row per movie. JSON records with equivalent fields are also acceptable.',
                       'kind': 'information',
                       'judge_rubric': "Use the actual Streaming at Home and Sci-Fi candidate set with Subscription Platform set to Netflix. The requested date is Movie Info's Release Date (Streaming), not a date when the movie was added to Netflix. Compare the displayed streaming-release dates as calendar dates, not movie years or alphabetical date strings. Report every movie tied for the maximum date, with its correctly paired date and all displayed screenwriter names. Evidence must establish the comparison and the selected movie facts through normal UI browsing. A guessed answer or relying only on a Newest/year sort fails; no extra fixed route or unrelated detail visits are required. Return one complete record per movie in the requested three-column table or equivalent JSON. Introductory or concluding prose is allowed; it must not contradict or add to the reported result set."},
 'RottenTomatoes--3': {'task_id': 'RottenTomatoes--3',
                       'prompt': 'Search for Christopher Nolan and compare the Movie Info sections of '
                                 'Oppenheimer and The Dark Knight. List every producer credited on both '
                                 'pages, and report the Release Date (Streaming) shown for each movie.',
                       'kind': 'information'},
 'RottenTomatoes--8': {'task_id': 'RottenTomatoes--8',
                       'prompt': "Register a new account with email testreviewer@test.com, name 'Test "
                                 "Reviewer', and password ReviewPass456!. After registering, verify you can "
                                 'access the account page.',
                       'kind': 'register',
                       'email': 'testreviewer@test.com',
                       'password': 'ReviewPass456!',
                       'name': 'Test Reviewer',
                       'movies': [],
                       'movie_titles': {},
                       'search': [],
                       'changes': [],
                       'count': False},
 'RottenTomatoes--9': {'task_id': 'RottenTomatoes--9',
                       'prompt': 'Log in as bob.c@test.com (password: TestPass123!), go to the account '
                                 "settings, and change the display name to 'Robert Clark'. Verify the name "
                                 'was updated on the account page.',
                       'kind': 'rename',
                       'email': 'bob.c@test.com',
                       'password': 'TestPass123!',
                       'name': 'Robert Clark',
                       'movies': [],
                       'movie_titles': {},
                       'search': [],
                       'changes': [],
                       'count': False},
 'RottenTomatoes--11': {'task_id': 'RottenTomatoes--11',
                        'prompt': 'Log in as david.k@test.com (password: TestPass123!), go to the watchlist '
                                  "page, and remove 'Deadpool & Wolverine' from the watchlist. How many "
                                  "movies remain in David's watchlist after removal?",
                        'kind': 'watch_remove',
                        'email': 'david.k@test.com',
                        'password': 'TestPass123!',
                        'name': None,
                        'movies': [{'id': 20,
                                    'title': 'Deadpool & Wolverine',
                                    'slug': 'deadpool_and_wolverine'}],
                        'movie_titles': {'deadpool_and_wolverine': 'Deadpool & Wolverine'},
                        'search': [],
                        'changes': [{'table': 'watchlist_items',
                                     'slug': 'deadpool_and_wolverine',
                                     'op': 'remove'}],
                        'count': True},
 'RottenTomatoes--14': {'task_id': 'RottenTomatoes--14',
                        'prompt': 'Log in as carol.d@test.com (password: TestPass123!). Compare My Ratings '
                                  'with My Watchlist. Which rated movies are not in the watchlist, and what '
                                  'score did Carol give each of them?',
                        'kind': 'information',
                        'email': 'carol.d@test.com',
                        'password': 'TestPass123!'},
 'RottenTomatoes--18': {'task_id': 'RottenTomatoes--18',
                        'prompt': "Using this site's browsing or search features, find the movie with the "
                                  'highest audience score among movies whose Movie Info credits Kevin Feige '
                                  'as a producer. Report its title, audience score, and Release Date '
                                  '(Streaming). Include every tied movie. If Movie Info does not list a '
                                  'Release Date (Streaming), explicitly report that it is not listed; do not '
                                  'exclude that movie.',
                        'kind': 'information',
                        'judge_rubric': 'Match the complete credited producer name and the Producer role, '
                                        "compare the eligible movies' displayed audience scores, and report "
                                        'every tied maximum with the correct title, score, and '
                                        'streaming-release date. Missing audience scores are not numeric '
                                        'scores. A movie associated with another Kevin or with a different '
                                        'credit role does not qualify. Both examining eligible candidates '
                                        'and a correct descending-score exclusion argument over the catalog '
                                        'are valid UI paths. Do not require the former anchor movie, every '
                                        'lower-scoring eligible movie, or one exact search string as hidden '
                                        'navigation conditions. Claims and recalled movie facts without '
                                        'relevant UI comparison do not pass. A highest-scoring eligible '
                                        'movie without a listed streaming-release date remains a result: '
                                        'report the title and score and explicitly state that the date is '
                                        'not listed. Evidence must show the complete Movie Info section '
                                        'lacks that field or explicitly marks it unavailable. Never infer a '
                                        'date from the theatrical release or exclude the winner because its '
                                        'streaming date is absent.'}}
