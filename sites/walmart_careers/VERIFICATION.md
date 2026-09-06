# walmart_careers — verification record

Everything below was executed against this working tree on 2026-09-06. Commands that
say "container" ran against `webharbor:dev` started as

```bash
docker run -d --rm --name wh-test -p 8201:8101 -p 41000-41017:40000-40017 webharbor:dev
```

The dev-only drivers used here live in `sites/walmart_careers/scripts_dev/`
(`walkthrough.py`, `leak_audit.py`, `robustness.py`, `shots.py`, `serve.py`).
That directory is gitignored **and** dockerignored, so the answer keys those
scripts contain never ship with the site or the image.

---

## 1. Byte-identical reset

### Seed build reproducibility (two consecutive freezer runs)

```
$ PYTHONHASHSEED=0 python seed_data.py   # run 1
$ md5 -q instance_seed/walmart_careers.db
faf1c03a780314e71f9586d5b0edc69b
$ PYTHONHASHSEED=0 python seed_data.py   # run 2
$ md5 -q instance_seed/walmart_careers.db
faf1c03a780314e71f9586d5b0edc69b
```

### Container: after `POST /reset/walmart_careers`

```
$ curl -X POST http://localhost:8201/reset/walmart_careers
{"pid":2506,"ready":true,"site":"walmart_careers"}

$ docker exec wh-test md5sum \
    /opt/WebSyn/walmart_careers/instance/walmart_careers.db \
    /opt/WebSyn/walmart_careers/instance_seed/walmart_careers.db
faf1c03a780314e71f9586d5b0edc69b  /opt/WebSyn/walmart_careers/instance/walmart_careers.db
faf1c03a780314e71f9586d5b0edc69b  /opt/WebSyn/walmart_careers/instance_seed/walmart_careers.db
```

### Container: after `docker restart wh-test`

```
$ docker restart wh-test
$ docker exec wh-test md5sum \
    /opt/WebSyn/walmart_careers/instance/walmart_careers.db \
    /opt/WebSyn/walmart_careers/instance_seed/walmart_careers.db
faf1c03a780314e71f9586d5b0edc69b  /opt/WebSyn/walmart_careers/instance/walmart_careers.db
faf1c03a780314e71f9586d5b0edc69b  /opt/WebSyn/walmart_careers/instance_seed/walmart_careers.db
```

Both md5s match in both directions. Bootstrap seeding is gated per whole function
(`seed_database()` on `Job.query.count() > 0`, `seed_benchmark_users()` on the
presence of `alice.j@test.com`), so a populated DB triggers no commit at all.

### All 18 sites still serve

```
$ for p in $(seq 41000 41017); do curl -so /dev/null -w "$p %{http_code}\n" http://localhost:$p/; done
41000 200 … 41017 200        # all eighteen returned 200
$ curl -s http://localhost:8201/health   # 18 sites, alive: true for every one
$ curl -s http://localhost:41017/_health
{"areas":7,"categories":33,"jobs":200,"ok":true,"site":"walmart_careers","stores":44,"users":4}
```

---

## 2. Seeded rows per model

| model | rows |
|---|---|
| `Area` | 7 (6 filterable career areas + Military) |
| `Category` | 33 |
| `Store` | 44 (6 offices + 38 field locations, 13 states/territories) |
| `Job` | 200 |
| `User` | 4 benchmark users, password `TestPass123!` |
| `SavedJob` | 10 (alice 3, bob 3, carol 2, david 2) |
| `Application` | 4 (`WMC-000001` … `WMC-000004`) |

Job distribution:

| dimension | breakdown |
|---|---|
| population | hourly 140 / salaried 60 |
| brand | Walmart 160 / Sam's Club 34 / Vizio 6 |
| employment type | Full time 120 / Part time 68 / Intern 12 |
| career area | Stores and Clubs 72, Supply Chain and Transportation 42, Technology 30, Corporate 24, Healthcare 20, Students 12 |
| distinct titles | 66 |
| shifts | every one of the 7 values appears on ≥24 postings |

`_assert_distractors()` (freezer-only) also enforces: ≥4 jobs per category, ≥3 per
store, ≥8 per state, unique hashtags per hourly title family, unique minimum
qualification texts per salaried posting, and no trending role that is a task target.

---

## 3. Task walkthroughs — 20/20

`scripts_dev/walkthrough.py` drives every task through Chromium (header search box,
Filters popover checkboxes, the Location popover, real login/apply/save/unsave form
submissions). Run against the container with a control-plane reset before each task,
so every task starts from the frozen seed state:

```
$ python scripts_dev/walkthrough.py http://localhost:41017 \
        http://localhost:8201/reset/walmart_careers
```

| task | what the walkthrough read off the page |
|---|---|
| 0 | `CP-5991-11240` / `2441 S Rock Rd` |
| 1 | `Option 2: 6 years' experience in software engineering or related area.` |
| 2 | `Shift may start between 6:00pm - 3:00am` / 3 open positions |
| 3 | `#pharmacytechjobs` / 2 open positions |
| 4 | `CP-4750-11184` / 3 open positions |
| 5 | `R-2411668` / Option 1 degree field |
| 6 | `10000 Brookpark Rd` / 2 open positions |
| 7 | `Intern (Fixed Term)` / `2101 SE Simple Savings Dr` |
| 8 | store `#1230` with 5 open positions |
| 9 | `CP-6038-10642` / `Shift may start between 3:00pm - 7:30pm` |
| 10 | `R-2451180` / 7 years |
| 11 | `CP-6088-10488` saved to alice's saved roles |
| 12 | the Neighborhood Market saved role removed from bob's list |
| 13 | `WMC-000005` |
| 14 | new account registered + `CP-9046-11101` saved |
| 15 | david's phone/city updated and persisted |
| 16 | `CP-2503-10726` / 5 open positions |
| 17 | `Shift may start between 6:00am - 11:00am` / `WMC-000005` |
| 18 | `CP-6014-12091` / `Shift may start between 5:00am - 10:00am` / 4 open positions |
| 19 | `CP-1179-11268` / `1301 SW Wanamaker Rd` |

**Note for the reviewer — confirmation numbers collide across tasks 13 and 17.**
The seed holds four applications, so the first application submitted against a freshly
reset database is always id 5 → `WMC-000005`. Tasks 13 and 17 therefore both produce
`WMC-000005` when each is run from a fresh reset (as above). This is by design: the
numbering scheme is `"WMC-" + zero-padded application id` and was left unchanged. A
verifier must not treat the confirmation number as a task-unique value — it should
match the `applications` row by `job_id` + `email` and then compare
`confirmation_no`. If both tasks run in the same session without a reset in between,
task 17 yields `WMC-000006`.

---

## 4. Answer-leak audit (task × page matrix)

Produced by `scripts_dev/leak_audit.py` against the **running container's rendered
HTML** (raw HTML, so `display:none` blocks and HTML comments are included).
`clean` = the answer token appears nowhere in the page. `n/a (stateful)` = the task's
deliverable is a database change, not a string read off a page.

Requisition IDs are part of every posting URL by design; `href`, `action` and hidden
`value` attributes are therefore stripped before a token is judged readable, which is
exactly why no task in this set answers with a requisition ID alone.

| task | home | results (natural query) | career area page | /resources/location | results URL audited |
|---|---|---|---|---|---|
| 0 | clean | clean | clean | clean | /results?q=optician |
| 1 | clean | clean | clean | clean | /results?q=staff+software+engineer |
| 2 | clean | clean | clean | clean | /results?q=freight+handler |
| 3 | clean | clean | clean | clean | /results?q=pharmacy+technician |
| 4 | clean | clean | clean | clean | /results?brand=Sam's+Club&type=Part+time&shift=Weekend+Overnight |
| 5 | clean | clean | clean | clean | /results?area=technology&type=Full+time&loc=Hoboken,+NJ&radius=25 |
| 6 | clean | clean | clean | clean | /results?loc=Cleveland,+OH&radius=25&type=Full+time&shift=Weekday+Day |
| 7 | clean | clean | clean | clean | /results?area=students&type=Intern&brand=Sam's+Club |
| 8 | clean | clean | clean | clean | /results?q=auto+care+center+technician |
| 9 | clean | clean | clean | clean | /results?q=freight+handler |
| 10 | clean | clean | clean | clean | /results?q=delivery+search+arrival+matching |
| 11 | n/a (stateful) | n/a (stateful) | n/a (stateful) | n/a (stateful) | /results?q=yard+driver |
| 12 | n/a (stateful) | n/a (stateful) | n/a (stateful) | n/a (stateful) | /results?q=asset+protection |
| 13 | clean | clean | clean | clean | /results?q=pharmacy+technician |
| 14 | n/a (stateful) | n/a (stateful) | n/a (stateful) | n/a (stateful) | /results?q=ecom+warehouse+worker |
| 15 | clean | clean | clean | clean | /results?q= |
| 16 | clean | clean | clean | clean | /results?q=cashier&loc=Puerto+Rico |
| 17 | clean | clean | clean | clean | /candidate-home/saved-roles |
| 18 | clean | clean | clean | clean | /results?area=supply-chain-and-transportation&category=drivers |
| 19 | clean | clean | clean | clean | /results?area=stores-and-clubs&category=digital-pickup-and-delivery&type=Full+time |

**0 leaks.** Tokens audited are the detail-only fields each task asks for: street
addresses, open-position counts, shift start windows, hashtags, worker-type chips,
qualification texts, years of experience and confirmation numbers.

### The 13 leak archetypes

| # | archetype | status |
|---|---|---|
| 1 | numeric difference pre-computed | tasks 8/10/18/19 make the agent open both postings and compare; no page states the delta |
| 2 | count the agent should count | task 16 requires visiting each PR cashier posting; the results heading counts roles, never open positions |
| 3 | verbatim task framing echoed | the results `<h1>`/`<title>` are `N open roles` — the query is no longer echoed |
| 4 | pre-bundled answer sentence | body copy is generated from per-family templates with store/shift/pay slots; no sentence restates a task answer |
| 5 | pinned/highlighted answer callout | no callouts; the fact column is identical for every posting |
| 6 | spoon-fed list endings with count | the "What you'll bring" list has no trailing count |
| 7 | wiki paragraph matching the question | n/a — no article pages |
| 8 | operand-only fuzzy match in the backend | search scores over title+category+area+banner+city+state+brand; `description` is deliberately excluded from the blob |
| 9 | bare-anchor → answer-bucket flood | the map is a deterministic SVG of the current result set; it carries city names and counts, never postings |
| 10 | algorithm-revealing UI text | the sort control says "Relevance"/"Most recent" only |
| 11 | sort order putting the answer first | the freezer asserts the target is not rank 1 for its natural query (tasks 0/2/13); relevance ties break on a seeded shuffle |
| 12 | pre-curated lookup table | none; every fact comes from SQLAlchemy |
| 13 | constraint values in item names | titles carry no shift, state, brand or pay words; the freezer's per-task locator check keeps each title+city pair unique |

---

## 5. Near-miss distractors and catalog breadth

`_assert_distractors()` enforces, per task, ≥6 results on the task's natural query or
facet set with ≤50 % of them satisfying *every* stated constraint. Measured on the
frozen seed:

| task | result set | size | full matches |
|---|---|---|---|
| 0 | `q=optician` | 6 | 1 |
| 2 | `q=freight handler` | 6 | 1 |
| 3 | Pharmacy Services category | 6 | 1 |
| 4 | Sam's Club · Part time · Weekend Overnight | 8 | 1 (3 are ≤ $20/hr, only one of those is in TX) |
| 5 | Full time Technology within 25 mi of Hoboken | 6 | 1 |
| 6 | within 25 mi of Cleveland, OH | 8 (4 after Full time + Weekday Day) | 1 |
| 7 | Students · Intern | 12 | 1 |
| 11 | `q=yard driver` | 8 | 1 |
| 13 | `q=pharmacy technician` | 60 | 1 |
| 14 | `q=ecom warehouse worker` | 19 | 1 |
| 16 | PR hourly cashier postings | 5 (4 list Weekday Day) | 1 |
| 18 | Drivers category | 8 | 2 |
| 19 | Digital Pickup and Delivery | 8 (4 Full time) | 1 |

Deliberate near-misses: Ponce PR has the second-highest open-position count among PR
cashiers but does not list Weekday Day (task 16); the Plano TX Sam's Club has two Part
time Weekend Overnight postings and only one is at or under $20/hr (task 4); Marcy NY
carries two Freight Handler postings at different facilities with different windows
(task 9); the second Merchandising Intern sits at the Walmart home office rather than
the Sam's Club one (task 7).

---

## 6. Interaction robustness — 26/26

`scripts_dev/robustness.py`, against the container:

- partial and loose queries return the right family (`cashi`, `freight hand`,
  `optical` → Optician, `sams club`, `truck driver`)
- an unresolvable location renders "We couldn't find that location", not an empty page
- a wrong password is rejected; `/account`, `/account/edit` and
  `/candidate-home/applications` redirect to `/login`; `/candidate-home/saved-roles`
  renders logged out with a sign-in CTA
- the apply form validates client-side *and* server-side (a raw POST with an empty
  body and one with a malformed email are both rejected with field errors)
- registration rejects a duplicate email, a short password and a password mismatch
- an anonymous save redirects to `/login?next=`; a signed-in save and unsave both
  persist across a reload
- a POST without a CSRF token returns 400
- an unknown job id renders the 404 page

---

## 7. Visual fidelity

Screenshots at 1440 px are in `scraped_data/mirror/`, using the same filenames as
`scraped_data/reference/` (`scripts_dev/shots.py`; `scraped_data/` is gitignored, so
these are local review artefacts).

Fixed in this run:

- **Header** now mirrors the live bar exactly: the full spark + `<>` + "Careers"
  lockup, then `Career areas` (dropdown listing all six areas), `Brands`, `Resources`,
  `About Us`, `Military`, a white search pill with a blue circular search button, and a
  user icon whose popover holds *My account / Saved roles / Login/Signup / EN* (or the
  initials avatar plus *My applications / Log out* when signed in). Nothing wraps at
  1440 px; the header spans the full viewport width like the original.
- **Results page**: heading is `N open roles` with no query echo; the count badge is on
  the `Open roles` tab only; `Add your location` is a link that opens a Location
  popover; `Filters` is a button that opens the facet panel; `Sort by: Relevance` is a
  dropdown. The permanently expanded sidebar panels are gone — the left column is the
  map only. Cards are population-aware: salaried cards show title / `City, ST zip` /
  `shift • $x - $y/yr`; hourly cards add the `banner #store` line above the city. Both
  buttons are styled as the live outlined `Select +` pill.
- **Job detail**: two layouts branched on `job.population`, both matching their
  reference screenshot — the three-photo masthead with the identity card (solid
  ld-blue for salaried, blue-over-navy for hourly), the left `Role Details` rail
  (sub-items only for hourly), the title, the address block with the map card, and the
  three dark navy chips (pay / worker type / Salaried for salaried; pay / employment
  type / shift window for hourly). `Apply now` is ld-blue on both.
- **Home**: centred hero with the inset dark search pill and circular button, plus the
  three-photo strip that overlaps the blue/white boundary; trending roles are three
  across on white.

Remaining differences from `scraped_data/reference/*.png`:

1. **The maps are deterministic SVGs, not Google Maps.** The results cluster map is a
   stylised US+PR outline with bubbles positioned from the seeded store coordinates;
   the detail page shows an SVG map card with a pin instead of a Google tile. This was
   the explicit decision in the build brief (PLAN.md §7.9 rejected). The mirror map is
   also less zoomed than the reference, which frames the whole western hemisphere.
2. **No `Chat` accordion and no `Go back` link** in the results sidebar. The chat panel
   is the site's LLM search assistant, which the mirror deliberately does not
   reproduce; `Go back` is a browser-history control with no server-side meaning.
3. **`Future roles` and `Content` tabs carry no count badge** and open an explicit
   empty-state panel. The brief asked for a badge on `Open roles` only; the live site
   shows counts on all three.
4. **The Filters popover is a four-column panel**, not the live single column. The
   mirror exposes more facets at once (Brand, Shift, Employment Type + Rate, Career
   Area with nested categories); a single column would need scrolling to reach the
   career areas that tasks 5, 7, 18 and 19 depend on.
5. **The salaried card keeps the ZIP and the shift prefix** (`Sunnyvale, CA 94089-4731`
   / `Multiple shifts • $143,000 - $286,000/yr`). The run instruction said "title /
   City, ST / pay only", but `reference/home.png`'s trending cards show the ZIP and the
   shift prefix on salaried cards, so the reference was followed. The banner line — the
   part that genuinely differs between populations — is dropped for offices.
6. **The salaried detail page keeps the three-photo masthead.** The run instruction
   described the salaried layout as "no hero photos", but `reference/job_detail_corp.png`
   shows the same three-photo masthead as the hourly page (with corporate photography
   rather than store photography), so the reference was followed. The two layouts still
   branch on `job.population` for the identity-card colour, the left rail's sub-items,
   the open-positions pill and the chip set.
7. **`About Us` links to a local `/about-us` page** assembled from the existing CMS
   constants. The live nav item points at an off-domain corporate site, which is out of
   scope for an offline mirror.
8. Minor typography drift: the mirror uses the harvested `EverydaySansUI` variable
   font, so line breaks inside long body paragraphs differ slightly from the reference
   captures.

---

## 8. Files that reference port 40017

| file | reference |
|---|---|
| `websyn_start.sh` | `walmart_careers` is index 17 of `SITES=( … )` → 40000 + 17 |
| `control_server.py` | `'walmart_careers'` is the 18th entry of `SITES` (same order) |
| `Dockerfile` | `EXPOSE 8101 40000-40017` |
| `sites/walmart_careers/tasks.jsonl` | `"web": "http://localhost:40017/"` on all 20 rows |
| `sites/walmart_careers/CLAUDE.md` | "Port **40017** … alt-port **41017**" |
| `README.md` | `-p 40000-40017:40000-40017`, and the 18-mirror list |
| `AGENTS.md` | three `40000-40017` occurrences plus `41000-41017` in the pre-PR block |
| `CONTRIBUTING.md` | TL;DR `-p 40000-40017:40000-40017` |
| `CLAUDE.md` | `:40000-40017` / `:41000-41017` in "Existing containers" |

Reassigning the slot is a single `sed` over `40017`/`41017` plus moving the entry in
the two `SITES` lists. Nothing else hard-codes the port; the dev-only scripts under
`scripts_dev/` take the base URL as an argument.

---

## 9. Needs human judgment

1. **Confirmation numbers repeat across tasks 13 and 17** (`WMC-000005` from a fresh
   reset each). See §3 — the reviewer's verifiers should match the `applications` row,
   not assume a unique string. Flagged rather than changed because the brief fixed the
   numbering scheme.
2. **Two run-instruction deviations, both resolved in favour of the reference
   screenshots**: salaried cards keep ZIP + shift prefix, and the salaried detail page
   keeps its three-photo masthead (§7 items 5 and 6). Say the word and both flip to the
   literal instruction.
3. **Task 2's `upstream_url`** points at `…/jobs/CP-9046-11101`, a real posting URL of
   the right page type, but the same posting task 14 references. Harmless (the field is
   documentation of the upstream page shape) but a reviewer may prefer a distinct URL.
4. **Location search accepts a whole state or territory** ("Puerto Rico", "PR", "Ohio")
   and then ignores the radius. The live site only geocodes cities/ZIPs. This was added
   so task 16 has a reliable route to every Puerto Rico posting; the radius route
   (`loc=Bayamon, PR`, 60 miles) also reaches all five and is asserted at build time.
   Drop it if the reviewer considers it too much of a mirror-only affordance.
5. **`Students` has no career-area index page** (`has_index_page = False`, matching the
   live site), so the "Career areas" menu sends it to `/results?area=students`. Task 7
   reaches it through the Filters panel, which is what its wording asks for.
6. **The Optician family's placement order was reordered** in `catalog_source.py` so the
   task 0 target is not rank 1 for `q=optician`. That shifts the seeded requisition IDs
   for the four Optician postings (the target is now `CP-5991-11240`). Any verifier
   drafted against an earlier build of this DB must be re-derived from the frozen seed.
7. **The mirror's `instance_seed/walmart_careers.db` is HF-managed and gitignored.**
   `faf1c03a780314e71f9586d5b0edc69b` is the md5 to expect in the assets PR; the code
   PR alone will not reproduce it without `scripts/fetch_assets.sh`.
