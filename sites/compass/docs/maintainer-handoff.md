# Compass maintainer handoff

[Review PR #84](https://github.com/aiming-lab/WebHarbor/pull/84) remains **Ready for maintainer review**, as requested by Zexu Jin after accepting the Compass experience and disclosed scope on September7,2026. Original contribution: [#25](https://github.com/aiming-lab/WebHarbor/pull/25), **sarendis56 (Peichun Hua)**; original commits and attribution are retained.

The September8 update resolves conflicts with the newly merged TED/OSU environments. It changes shared integration, Compass task entry ports and bounded TED/OSU compatibility checks. Compass UI and grading semantics remain unchanged. **The refreshed task17 independent verdict is still outstanding and is not counted as PASS.**

| Item | Current candidate |
|---|---|
| Application checkpoint | `4574f245573b0fa9c70497661984065b9db819c9` |
| Test-only follow-up | `208863df54f615dd88851fe5b91803c208d3d8d5` |
| Integrated upstream main | `7269134e9db9d10b1a6ac321797be51c72bb1a36` |
| Registry |22 sites; TED40019, OSU40020, Compass40021; control8101 |
| Asset PR |[HF #53](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/53), OPEN; maintainers coordinate merging |
| Immutable combined asset revision |`8ade6b3a80d376c801f88e2409b72e8909444927` |
| Compass archive |210,301,426 bytes; SHA256 `077cfb2334cb40bf191b2e557c0becd6e28a1901e7ea80183216c1e9db1544aa`, unchanged |
| Rebuilt Compass runtime seed |`3180c49546acb487370e9cad212544b32be35f9b61b7a7869cfe9c1abc199087`; all11 tables equal the accepted asset seed |
| Prepared image |`sha256:1b679ef882490eb40fffc4c15b7288f2b4aca7d679fab045b92b24f148a7d0f4`; incremental build |
| Mechanical checks |230 tests pass;22 homepages and470 Compass URLs200;1123 runtime files match build manifest |
| Real UI and reset |1 synthetic inquiry, refresh without duplicate; Compass reset0.74s; reset-all3.57s;26/26 seed files equal |
| Owner runtime |Compass40021;23 data files from the previous20 sites preserved byte-for-byte |

[Current integration report](integration-review.md) and [machine-readable validation](integration-validation.json) explain all changes, failed checks repaired, image reuse and exact evidence boundaries. A new clean all-site build is not claimed. [September7 Ready-transition checks](maintainer-validation.json) remain a historical record.

## Review evidence and scope

- [Environment/source,16-task quality matrix, verifier negative cases and independent reconciliation](review-report.md).
- [Sell and24 regional guides:36 source/before/after and interaction captures](sell-guides-review.md), with [validation and hashes](sell-guides-validation.json).
- [Homepage/navigation52 captures](homepage-review.md) and [Concierge/directory26 captures](landing-review.md).

The original independent review judged16 frozen guided/source-aware executions PASS and visually sampled4 of268 screenshots. The refreshed task17 execution at `9741284` / HF `e063074` has8 steps and16 screenshots, deterministic PASS, and unchanged before/after state; its independent result has not arrived. All932 original files and39 refreshed inputs remain unchanged. Older verdicts do not certify subsequent UI changes, and no full rerun of16 tasks on the current integration is claimed.

Human acceptance covers the Compass experience and disclosed scope, not individual inspection of every image. Individual community articles and nearby searches remain explicit external links. Sell films use local posters/external video links; inquiry forms save only local synthetic state. Live maps and real-agent communications remain outside scope. Benchmark accounts, stable snapshots and withholding detail answers from search cards remain intentional.

## Remaining maintainer actions

1. Receive and reconcile the refreshed task17 independent result, or explicitly decide how to accept that outstanding coverage. It stays separate from the completed original16-task review.
2. Review and merge/resolve HF #53. If the selected revision changes, update `.assets-revision` and verify all archive hashes against the tested candidate. Different asset bytes require affected validation.
3. Confirm current GitHub base/head and asset pin, perform final build/integration and code review, then merge #84 and coordinate closure/supersession of original #25.

`directly_mergeable_now: false`. Public Ready makes the contribution available for maintainer review while the outstanding follow-up remains visible. Reviewer agents have not merged either public PR.
