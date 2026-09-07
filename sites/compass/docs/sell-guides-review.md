# Compass Sell and regional-guide reconstruction

The previous Sell introduction and property-list substitutes did not reproduce the source page structure. This follow-up restores the Sell marketing sections and **24 regional guide landings with 401 community cards**, including their original media/order and responsive layouts. Original contribution: [#25](https://github.com/aiming-lab/WebHarbor/pull/25), **sarendis56 (Peichun Hua)**; reviewer takeover: [Draft #84](https://github.com/aiming-lab/WebHarbor/pull/84).

**Application `7f6dc008603182c6ace79ad52e52f2f8b804ae4b` · HF `d86ec0bfcbb98f92efbe6b6b4440f9dcc6cceb69` · Compass `40019` in the 20-site registry.** Human visual/scope acceptance and the refreshed independent task17 verdict remain pending. This is a repaired candidate, not a claim of complete Compass service parity or Ready status.

## Source / before / after

Reference pages: [Compass Sell](https://www.compass.com/sell/) and [New York City guides](https://www.compass.com/neighborhood-guides/nyc/), captured September 7, 2026. “Before” is `25b8b3375aeb5a3b2c5823f8ed6d52a05eddeccf` with HF `b09ad95`. Candidate captures use the application above except the unchanged form states captured at `c25326d` and card-shading state at `83658f0`; each image retains its actual checkpoint in the manifest.

All **36 images** are unaltered browser captures. [Validation, URLs, UTC timestamps, viewport/scroll state, pixel dimensions and SHA-256](sell-guides-validation.json) accompany them. Browser viewport sizes are 1440×900, 815×900 and 390×844 at default zoom. Fonts were loaded, no document overflow was observed, and top captures independently confirmed scroll zero before/after. Full-page dimensions differ from viewport height. Source videos can show a different frame; no dynamic regions were masked.

Click a screenshot to inspect its full resolution. The long-page rows show the complete structural difference, not just the hero.

| Page / state | Original | Before | After |
|---|---|---|---|
| sell · 1440px · top | ![source-sell-top-1440](visual-review/sell-guides/source-sell-top-1440.jpg) | ![before-sell-top-1440](visual-review/sell-guides/before-sell-top-1440.jpg) | ![final-sell-top-1440](visual-review/sell-guides/final-sell-top-1440.jpg) |
| sell · 815px · top | ![source-sell-top-815](visual-review/sell-guides/source-sell-top-815.jpg) | ![before-sell-top-815](visual-review/sell-guides/before-sell-top-815.jpg) | ![final-sell-top-815](visual-review/sell-guides/final-sell-top-815.jpg) |
| sell · 390px · top | ![source-sell-top-390](visual-review/sell-guides/source-sell-top-390.jpg) | ![before-sell-top-390](visual-review/sell-guides/before-sell-top-390.jpg) | ![final-sell-top-390](visual-review/sell-guides/final-sell-top-390.jpg) |
| region-nyc · 1440px · top | ![source-region-nyc-top-1440](visual-review/sell-guides/source-region-nyc-top-1440.jpg) | ![before-region-nyc-top-1440](visual-review/sell-guides/before-region-nyc-top-1440.jpg) | ![final-region-nyc-top-1440](visual-review/sell-guides/final-region-nyc-top-1440.jpg) |
| region-nyc · 815px · top | ![source-region-nyc-top-815](visual-review/sell-guides/source-region-nyc-top-815.jpg) | ![before-region-nyc-top-815](visual-review/sell-guides/before-region-nyc-top-815.jpg) | ![final-region-nyc-top-815](visual-review/sell-guides/final-region-nyc-top-815.jpg) |
| region-nyc · 390px · top | ![source-region-nyc-top-390](visual-review/sell-guides/source-region-nyc-top-390.jpg) | ![before-region-nyc-top-390](visual-review/sell-guides/before-region-nyc-top-390.jpg) | ![final-region-nyc-top-390](visual-review/sell-guides/final-region-nyc-top-390.jpg) |
| sell · 1440px · full page | ![source-sell-full-1440](visual-review/sell-guides/source-sell-full-1440.jpg) | ![before-sell-full-1440](visual-review/sell-guides/before-sell-full-1440.jpg) | ![final-sell-full-1440](visual-review/sell-guides/final-sell-full-1440.jpg) |
| region-nyc · 1440px · full page | ![source-region-nyc-full-1440](visual-review/sell-guides/source-region-nyc-full-1440.jpg) | ![before-region-nyc-full-1440](visual-review/sell-guides/before-region-nyc-full-1440.jpg) | ![final-region-nyc-full-1440](visual-review/sell-guides/final-region-nyc-full-1440.jpg) |
| Sell · 390px · full page | ![source-sell-full-390](visual-review/sell-guides/source-sell-full-390.jpg) | Not present in the previous implementation | ![final-sell-full-390](visual-review/sell-guides/final-sell-full-390.jpg) |
| Sell advantage · item 2 · 390px | ![source-sell-advantage-2-390](visual-review/sell-guides/source-sell-advantage-2-390.jpg) | Not present in the previous implementation | ![final-source-shading-advantage-2-390](visual-review/sell-guides/final-source-shading-advantage-2-390.jpg) |
| Sell comparison · item 6 · 390px | ![source-sell-comparison-6-390](visual-review/sell-guides/source-sell-comparison-6-390.jpg) | Not present in the previous implementation | ![final-sell-comparison-6-390](visual-review/sell-guides/final-sell-comparison-6-390.jpg) |
| NYC nearby · expanded · 1440px | ![source-region-nearby-expanded-1440](visual-review/sell-guides/source-region-nearby-expanded-1440.jpg) | Not present in the previous implementation | ![final-region-nearby-expanded-1440](visual-review/sell-guides/final-region-nearby-expanded-1440.jpg) |

## What changed and what was measured

| Area | Original / previous problem | Repair and evidence |
|---|---|---|
| Sell page skeleton | Previous page was a short introduction; source has two lead forms and a long marketing sequence. | Restored 13 sections: hero, lead form, advantage, strategy, choices, benefits, results, listing comparison, film, selling terms, second film, footer lead form and methodology. Original source media and resolved source CSS variables are local. |
| Sell interaction | Missing three-card advantage stack and six-state listing comparison. | Both controls work forward/backward and wrap; accessible current-state text and inactive-card visibility are updated. Desktop/mobile card proportions, static navigation and inactive RGB17/RGB67 overlays match observed source states. |
| Sell geometry | Typography, content width, imagery and section spacing diverged. | At 1440px, measured source/candidate marketing-section heights align: hero 659.33, advantage 1429.13, strategy 1376.38, choices 691, benefits 2377.55, results 908.19, comparison 1280, each film 1048.13 and terms 1509px. The local form is intentionally shorter because its notice describes local storage, not real-agent consent. |
| Regional guide landings | Six local regions showed property snapshots; the other 18 directory entries left the mirror. | All 24 directory links now lead to local source-derived regional landings; 401 community names/images/links preserve source order. Runtime HTTP reads these records from SQLite. |
| NYC desktop and mobile | Missing regional hero, community-card grid, source breakpoint behavior and nearby-home groups. | Source header/breadcrumb, 502.5px desktop hero, four-column card grid, 194px image height and mobile single-column layout reproduced. The original hides the hero below 648px; the candidate does too. |
| Nearby homes | An intermediate implementation incorrectly used three columns and compressed the page by about 600px. | Source groups are vertically stacked at every width. Source and candidate now both start at y=4978.43 and measure 1007.59px high at 1440px. Each group is 281.40px high initially; Show more expands five links to fifteen in the first NYC group. The extra local external-link notice accounts for about 32px of full-page height difference. |

`neighborhood_guides.json` records the original page URL, retrieval time and HTML hash for each region. `visual_sources.json` records source media provenance. The JSON is an initialization input; request handlers read the seeded `neighborhood_guides` SQLite table. No source script or iframe is embedded.

## Real form and reset checks

The two Sell forms submit to the same local POST handler. Valid requests persist a `seller_inquiries` row and redirect to a session-bound confirmation; refresh does not duplicate the write. Name/email/phone/ZIP validation, CSRF and escaped retained input are covered. Invalid submissions return 422 without a partial row. The page explicitly says no email, call or text is sent to Compass.

The browser submitted a synthetic inquiry in both the isolated host preview and the full Docker environment. The host row-level comparison found exactly one new seller inquiry and no other table changes. The Docker submission was captured before reset; Compass reset removed that row and restored the seed byte-for-byte in **0.75s**. Reset-all completed in **2.58s**, restored **23/23 seed files**, and left all **20 sites healthy**. These are UI QA executions, not new benchmark task runs.

| Empty form | Persisted confirmation | After official reset |
|---|---|---|
| ![empty](visual-review/sell-guides/final-sell-form-empty-390.jpg) | ![saved](visual-review/sell-guides/final-sell-form-saved-390.jpg) | ![reset](visual-review/sell-guides/final-sell-form-reset-390.jpg) |

[Mobile nearby-links expansion](visual-review/sell-guides/final-region-nearby-expanded-390.jpg) is also recorded.

## Engineering, assets and task impact

- **178 tests passed**: 54 application/source cases and 124 verifier cases. Meaningful new cases cover seller validation/CSRF/persistence and SQLite-backed regional reads. Subsequent isolated CSS/markup/shading refinements were checked in the browser and by final file hashes; they did not change the POST handler, task data or verifier code.
- A fresh full-20-site container from the incremental candidate returned **200 for all 20 homepages and 470 local routes/media URLs**. The final prepared image and QA/owner runtimes match all **455** payload hashes. Full startup/reset checks ran on image `bff69b1e…`; the final image `fc194126…` adds the isolated card shading and nearby-layout refinements, with fresh browser checks. This is an incremental build, not a fresh clean fetch/build of every site.
- [HF #53](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/53) contains a **210,301,426-byte** Compass archive, SHA-256 `077cfb2334cb40bf191b2e557c0becd6e28a1901e7ea80183216c1e9db1544aa`. It preserves **2,467 previous files**, adds **442 public media files**, and replaces the seed with an additive migration: the original **nine table rowsets are unchanged**, plus 24 guide rows and an empty seller-inquiry table. Total: 2,910 files. The other **19 archives are unchanged**. Remote immutable revision/size/hash were verified.
- New seed SHA-256: `86c648f437651974e169ab2ed4921b85b15bd2116008fdbb66dbf118d41b663d`. Repeated initialization and canonical boot preserve its bytes. Updating the owner runtime preserved the existing nine benchmark tables; the final layout-only update preserved all eleven current tables and left the other nineteen site processes untouched.
- The **16 task/rubric/verifier contracts remain unchanged**. The existing task handlers and benchmark rowsets are unchanged; detailed answer facts were not added to result cards. All **932 original execution files**, **39 refreshed task17 packet inputs** and the prior frozen Claude verdict were rehashed unchanged. Earlier runs retain their own code/asset versions; they are not relabeled as executions of this candidate. The [main report](review-report.md#task-and-grading-audit) contains the task-quality and negative-verifier audit.
- The earlier independent verdict was 16/16 PASS but visually sampled only four screenshots. The refreshed task17 packet requires all sixteen screenshots and still awaits its independent verdict. Neither verdict substitutes for source fidelity or human visual acceptance of these new pages.

## Remaining boundaries and delivery status

All 24 **regional landing pages** are local; individual community long-form articles and nearby property searches open their explicit Compass URLs. Sell films use local posters and external YouTube links, so autoplay/embedded frames differ. Seller inquiries remain local. Shared navigation glyph/link spacing and the benchmark footer are not pixel-identical. Concierge financing/contact services, live maps and other disclosed service limits in the earlier reports remain outside this implementation.

Those service limits are separate from necessary benchmark differences: synthetic accounts, local state, stable catalog recommendations and withholding detailed answers from search cards remain in place. No missing service or visual defect is classified as an answer-leak safeguard.

The source-led structural repairs and local validation are complete for this scope. **Human experience/scope acceptance and the refreshed independent execution verdict are still required; the PR stays Draft.** Maintainers perform the eventual code and asset merges.
