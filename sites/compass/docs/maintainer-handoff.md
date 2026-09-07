# Compass maintainer handoff

Human experience and the disclosed implementation scope were accepted by **Zexu Jin on September 7, 2026**, with an explicit request to mark [Review PR #84](https://github.com/aiming-lab/WebHarbor/pull/84) Ready for review. Original contribution: [#25](https://github.com/aiming-lab/WebHarbor/pull/25), **sarendis56 (Peichun Hua)**. This transition changes documentation only.

**Ready for maintainer review does not mean ready for immediate merge.** The original 16-task independent verdict is complete and reconciled; the refreshed task17 verdict remains outstanding. It is disclosed here and is not counted as PASS. The earlier execution versions and verdict are unchanged.

## Candidate and checks

| Item | Verified identity / result |
|---|---|
| Application | `7f6dc008603182c6ace79ad52e52f2f8b804ae4b` |
| Pre-handoff documentation | `4a80f3819f0c3b443a11663c5ec79a8862c3a234`; this document is the subsequent status-only update |
| Integration base | `90afddb6d4af382935ded9a385f2eead604188cf` |
| Registry | 20 sites; Compass40019, Target40018; control8101 |
| Asset PR | [HF #53](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/53), OPEN, no conflicts |
| Immutable HF revision | `d86ec0bfcbb98f92efbe6b6b4440f9dcc6cceb69` |
| Compass archive | 210,301,426 bytes; SHA-256 `077cfb2334cb40bf191b2e557c0becd6e28a1901e7ea80183216c1e9db1544aa` |
| Runtime seed | `86c648f437651974e169ab2ed4921b85b15bd2116008fdbb66dbf118d41b663d` |
| Final prepared image | `sha256:fc19412657658928bc3fc49ec46e9d610d9877872bae778060d2f84d4d32a3cf` (incremental build) |
| Fresh transition checks | 455 runtime payload hashes match; 20/20 site homepages200; 16 task/rubric/verifier contracts; 932 original execution files,39 task17 inputs and36 published images rehashed unchanged |
| Reused application checks | 178 tests PASS; 470 local route/media URLs200; real UI inquiry and byte-identical Compass reset0.75s; reset-all2.58s with23/23 seed files equal |
| Remote mergeability | GitHub MERGEABLE before this status-only update; no CI checks were reported. That is not a CI PASS or merge approval. |

[Machine-readable transition checks](maintainer-validation.json) record exact identities and reuse boundaries. The previous full startup/reset checks ran on the `bff69b1e…` incremental image, followed by isolated shading/nearby-layout refinements with fresh browser and final payload checks. No new clean build of all20 sites is claimed. Owner experience data was not reset during this transition.

## Review evidence

- [Environment, source,16-task quality matrix, verifier negative cases and independent-review reconciliation](review-report.md).
- [Sell and24 regional guides:36 source/before/after and interaction captures](sell-guides-review.md), [validation and hashes](sell-guides-validation.json).
- [Homepage/navigation52 captures](homepage-review.md) and [Concierge/directory26 captures](landing-review.md), retaining their historical checkpoints.

The existing independent review judged16 frozen guided/source-aware executions PASS and visually sampled4 of268 screenshots. The newer task17 execution at `9741284` / HF `e063074` has8 steps and16 screenshots, deterministic PASS, and unchanged before/after state; its independent result has not been received. No claim is made that the older verdict certifies subsequent UI changes or that the16 tasks were all rerun on the latest UI.

Human acceptance applies to the current candidate and disclosed scope; it does not attest that every published image was individually inspected. Specific community articles and nearby searches open the source site; Sell films use local posters/external video links, and inquiry forms save only local state. The live map, real-agent communications and other stated service limits remain. Benchmark accounts, stable snapshots and withholding detail answers from search cards remain intentional.

## Remaining maintainer actions

1. Receive and reconcile the refreshed task17 independent result, or make an explicit acceptance decision on that outstanding coverage. It remains separate from the completed original16-task review.
2. Review and merge/resolve HF #53. If the merge changes the selected revision, update `.assets-revision` and verify all asset hashes against the tested candidate; any different asset bytes require affected validation.
3. Confirm the final GitHub base/head and asset pin, run the final integration build/asset/reset checks, and complete maintainer code review before merging #84. Then coordinate closure/supersession of original #25.

`directly_mergeable_now: false`. Reviewer agents have not merged either PR. The public PR is opened for maintainer review at the owner's request while the outstanding independent follow-up stays visible.
