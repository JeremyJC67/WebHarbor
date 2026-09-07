> This historical 25b8b33 report covers Concierge and the directory index. The later Sell and all24regional-landing implementation is documented in [sell-guides-review.md](sell-guides-review.md).

# Concierge and neighborhood directory follow-up

Original contribution: [#25](https://github.com/aiming-lab/WebHarbor/pull/25), **sarendis56 (Peichun Hua)**. Companion review: [#84](https://github.com/aiming-lab/WebHarbor/pull/84).

Application `25b8b3375aeb5a3b2c5823f8ed6d52a05eddeccf` replaces the one-panel Concierge placeholder and six equal-image directory with source-referenced landing pages. It follows the earlier [homepage/navigation reconstruction](homepage-review.md). **Human acceptance and the refreshed independent task17 verdict remain pending; this is still Draft.**

## Changes and source evidence

- [Concierge](https://www.compass.com/concierge/): original local MP4 hero, wordmark, measured typography and breakpoints; three marketing phases; four service pillars; all eight source cases with working previous/next controls; original paired before/after photographs; covered services, source-attributed statistics, process, film poster and FAQs. The reading chapter bar replaces the main navigation and its anchors leave the source-measured 120px space.
- [Neighborhood Guides](https://www.compass.com/neighborhood-guides/): all 24 source regions, original photographs/coordinates and city illustration, source ordering and unequal grid spans. The 1170px desktop layout uses a 549×262.5px first tile and 262.5px adjacent tiles with 24px gaps; the 815px view uses two columns, and 390px uses one. The source semibold serif face is now local.
- Fonts, computed styles, section dimensions and responsive behavior were read from the public pages on September 7, 2026. CSS is scoped to the relevant pages; no source scripts or tracking are imported. Media provenance/hashes are in [visual_sources.json](../visual_sources.json).

At 1440×900 with the Jo Ann case selected, the source/candidate section heights were 630/630px for the hero, 514/514px for the marketing phases, 184.25/184.25px for the pillars, 738.06/738.16px for stories, 569.25/569.25px for covered services and 284/284px for statistics. FAQ text differs where the source contact form is replaced with the explicit service choices below. These measurements and screenshot review are not a claim of complete Compass parity or a human-approved baseline.

## Original / before / after

Before is application `82b5915` with HF `5b66b75`; after is `25b8b33` with HF `b09ad95`. All top comparisons use scroll 0, matching viewports and loaded fonts. The official hero is an autoplay video, so its frame varies. Source and after directory captures move the pointer to the heading, away from zoom-on-hover tiles.

| Page / viewport | Original | Before | After |
|---|---|---|---|
| Concierge · 1440px | ![source-screen-concierge-top-1440](visual-review/landing/source-screen-concierge-top-1440.jpg) | ![before-concierge-top-1440](visual-review/landing/before-concierge-top-1440.jpg) | ![verified-concierge-top-1440](visual-review/landing/verified-concierge-top-1440.jpg) |
| Concierge · 815px | ![source-screen-concierge-top-815](visual-review/landing/source-screen-concierge-top-815.jpg) | ![before-concierge-top-815](visual-review/landing/before-concierge-top-815.jpg) | ![verified-concierge-top-815](visual-review/landing/verified-concierge-top-815.jpg) |
| Concierge · 390px | ![source-screen-concierge-top-390](visual-review/landing/source-screen-concierge-top-390.jpg) | ![before-concierge-top-390](visual-review/landing/before-concierge-top-390.jpg) | ![verified-concierge-top-390](visual-review/landing/verified-concierge-top-390.jpg) |
| Guides · 1440px | ![source-verified-guides-top-1440](visual-review/landing/source-verified-guides-top-1440.jpg) | ![before-guides-top-1440](visual-review/landing/before-guides-top-1440.jpg) | ![verified-guides-top-1440](visual-review/landing/verified-guides-top-1440.jpg) |
| Guides · 815px | ![source-verified-guides-top-815](visual-review/landing/source-verified-guides-top-815.jpg) | ![before-guides-top-815](visual-review/landing/before-guides-top-815.jpg) | ![verified-guides-top-815](visual-review/landing/verified-guides-top-815.jpg) |
| Guides · 390px | ![source-verified-guides-top-390](visual-review/landing/source-verified-guides-top-390.jpg) | ![before-guides-top-390](visual-review/landing/before-guides-top-390.jpg) | ![verified-guides-top-390](visual-review/landing/verified-guides-top-390.jpg) |

## Additional section and interaction comparisons

These sections were absent from the previous one-panel page. The same Jo Ann case is selected in the source and candidate. Chapter-scroll offsets match within 0.5px: stories 1780/1780, services 2578/2578, video 4490.5/4491, FAQ 5664.5/5665. UI QA screenshots are separate from benchmark task executions.

| Section | Original | After |
|---|---|---|
| Stories | ![source-final-concierge-stories-1440](visual-review/landing/source-final-concierge-stories-1440.jpg) | ![verified-concierge-stories-1440](visual-review/landing/verified-concierge-stories-1440.jpg) |
| Services | ![source-final-concierge-services-1440](visual-review/landing/source-final-concierge-services-1440.jpg) | ![verified-concierge-services-1440](visual-review/landing/verified-concierge-services-1440.jpg) |
| Video | ![source-final-concierge-video-1440](visual-review/landing/source-final-concierge-video-1440.jpg) | ![verified-concierge-video-1440](visual-review/landing/verified-concierge-video-1440.jpg) |
| Faq | ![source-final-concierge-faq-1440](visual-review/landing/source-final-concierge-faq-1440.jpg) | ![verified-concierge-faq-1440](visual-review/landing/verified-concierge-faq-1440.jpg) |

## Intentional boundaries and remaining work

Concierge's lead/financing form is replaced by **Find an Agent** (the existing local directory) and **Contact Compass online ↗**. No contact details are collected locally and no fake success message is shown. Three case videos and the main film have explicit YouTube links; paired case photographs and the hero MP4 work locally. The YouTube case cards therefore differ from the online embedded previews.

The directory index is reproduced, but full regional/neighborhood editorial pages are not. The six existing regional links still show local listing snapshots with a link to the original guide; the other 18 links explicitly open Compass. Previously disclosed Sell, live-map, agent-service and external workflow limits remain. These functional boundaries are not answer-leak safeguards.

Benchmark differences are preserved separately: no detail answers are added to search cards, no external facts are invented, authentication/accounts stay local and the seed remains unchanged.

## Validation and evidence reuse

- 168 application/source/verifier tests passed during this repair (44 application/source, 124 verifier). Subsequent typography, chapter positioning and explicit-link refinements were checked in the browser and by the local URL sweep. Tests alone do not establish visual quality.
- A fresh container from `wh-review025:25b8b33` (`sha256:00e81abe6ab152954199d338ca65b42b60c8457a2e866b3941b2a1bef63712aa`) matched all 47 changed file hashes. All 20 site homepages and 69 local routes/media URLs returned 200. Compass reset took 0.722s and restored the runtime seed byte-for-byte. This is an incremental image on the verified prior image; no new full clean-fetch/reset-all claim is made.
- The final browser run visited all eight case states, verified one visible case at a time and wrap to Julia, exercised mobile next/previous, and opened the local agent CTA. Desktop, tablet and mobile screenshots showed loaded fonts and no horizontal overflow. The existing NYC local guide destination was also opened during the preview.
- HF [PR #53](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/53) now pins `b09ad95ac9428d5f98e1dc6206f1fa5f87aec671`. Archive: **192,209,798 bytes**, SHA-256 `ced1411f5d86992ee07a55b98c3b8660ec548f204e0602c1a90d0fe0436f4b98`. It adds 38 original media/font/SVG files; all 2,430 prior files including seed and the other 19 site archives are unchanged. Neither public PR was merged.
- 63 protected files are byte-identical to `82b5915`; AST comparison found only the `neighborhoods` handler changed (loading the directory data). Existing task handlers, templates, facts, tasks, core JS and verifiers are unchanged. The base-template changes apply only to Concierge and neighborhood pages.
- The original 16 frozen trajectories and the `9741284` task17 packet retain their original code/assets and verdict identities. This change does not add a new benchmark run or claim their independent verdict covers the new pages. The fresh task17 independent verdict remains pending.

[Machine-readable validation](landing-validation.json) includes all 26 unaltered viewport images' hashes, timestamps, URLs, dimensions, scroll positions, source/asset identities, runtime checks and the reuse inventory. Deep after images were captured in a preview overlay whose 47 files were independently hash-matched to the final image; final top images came from the rebuilt image. Private workflow documents and raw databases are not included.
