<div align="center">

<h1>⚓ WebHarbor</h1>
<h3>Docking Real Websites for Evolving GUI Agent Environments</h3>

<p>
  <a href="https://huggingface.co/datasets/ChilleD/WebHarbor">
    <img src="https://img.shields.io/badge/🤗-Dataset-yellow.svg" alt="HuggingFace Dataset" />
  </a>
  <a href="https://docs.google.com/spreadsheets/d/1vZsrQjy9nJKze58fx4kbQtFi85NjVXIWCFyu3ShD7gk/edit?gid=0#gid=0">
    <img src="https://img.shields.io/badge/📊-Track%20Sheet-blue.svg" alt="Contribution Track Sheet" />
  </a>
  <a href="https://forms.gle/ngcD1rzAfUEphNmRA">
    <img src="https://img.shields.io/badge/📝-Request%20Form-green.svg" alt="Contribution Request Form" />
  </a>
  <a href="https://aiming-lab.github.io/webharbor.github.io/">
    <img src="https://img.shields.io/badge/🏠-Project%20Page-orange.svg" alt="WebHarbor Project Page" />
  </a>
  <a href="https://github.com/aiming-lab/WebHarbor">
    <img src="https://img.shields.io/badge/💻-Code%20Repo-black.svg" alt="WebHarbor GitHub" />
  </a>
</p>

</div>

WebHarbor docks popular websites into local, stable, Docker-based mirrors with full auth, database, and multimodal image content. Environments evolve with agent capability.


## 💡 Motivation

Live websites are noisy: reCAPTCHA, geo-blocks, network flakiness, content drift. Their most useful features sit behind login walls that benchmarks can't touch. Existing offline web environments either freeze the web into toy synthetic sites or fall back to static traces with no real interaction, which limits large-scale RL training.

WebHarbor takes a different approach. We leverage coding agent (e.g., Claude Code/CodeX) to mirror real sites into local Docker images that:

- **Stable & reproducible** — no network noise, no content drift, no geo-blocks
- **Deep features unlocked** — carts, checkouts, accounts, all fully testable
- **Evolving** — harder tasks drive richer mirrors; the environment grows with agents
- **RL-ready** — sub-second database resets between rollouts
- **Community-driven** — 23 sites today, scaling to 100+ together

## 🚀 Quickstart

One command to run all web environments:

```bash
docker run -p 8101:8101 -p 40000-40022:40000-40022 battalion7244/webharbor:latest
```

Then point your agent at `http://localhost:40000` through `http://localhost:40022` to explore 23 local mirrors of WebVoyager sites: `Allrecipes, Amazon, Apple, ArXiv, BBC News, Booking, GitHub, Google Flights, Google Maps, Google Search, Hugging Face, Wolfram Alpha, Cambridge Dictionary, Coursera, ESPN, Merriam-Webster, IKEA, Phys.org, Target, TED, Ohio State University, Rotten Tomatoes, and Compass`.

For sub-second reset between rollouts, expose the control plane and call `/reset/<site>`:

```bash
curl -X POST http://localhost:8101/reset/amazon          # one site
curl -X POST http://localhost:8101/reset-all             # all sites in parallel
```

If you prefer to build the image yourself:

```bash
git clone https://github.com/aiming-lab/WebHarbor && cd WebHarbor
./scripts/fetch_assets.sh                          # pulls static assets from ChilleD/WebHarbor on HF
./scripts/build.sh                                 # docker build -t webharbor:dev .
```

### Local NVIDIA review candidate

This local review branch registers **24 sites**: the 23 entries listed above,
followed by NVIDIA. The published-image quickstart above is not a claim that
this review candidate has been published or accepted.

| Site | Registry position | Container port | Local review host port |
| --- | --- | --- | --- |
| NVIDIA | 24 | 40023 | 48023 |

After preparing the candidate assets and building `webharbor:dev`, the local
review deployment uses:

```bash
docker run -p 127.0.0.1:48080:8101 -p 127.0.0.1:48000-48023:40000-40023 webharbor:dev
```

NVIDIA inherits the site contribution from @KaKituken
([#55](https://github.com/aiming-lab/WebHarbor/pull/55)) and the verifier/rubric
contribution from @DEM1TASSE
([#58](https://github.com/aiming-lab/WebHarbor/pull/58)). This is file-level
integration, not a claim that either PR was merged or that the NVIDIA review has
passed.

### Asset delivery status (blocker)

`.assets-revision` is pinned to the resolved commit of HF dataset PR
[#75](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/75),
`fbf6b9f4f735116ae0e4194db2b160e9a4207fc1`. That revision is the only candidate
that carries an archive for every registered site (28 `*.tar.gz`, including
`nvidia.tar.gz`, sha256
`acafd81955a1491406e41bac886c1903b11fa370913162df0adcdc43fb40ddb0`, 6,706,510
bytes).

Two blockers remain on the asset side; neither can be cleared from this
repository:

1. **HF PR #75 is a draft and is not merged.** The pinned commit is not on the
dataset's `main`, so a clone that pins the dataset default branch still has no
`nvidia.tar.gz`, and `hf download --revision main` cannot resolve the pin until
the PR merges. Clearing condition: merge HF PR #75 and, if the tree still
contains archives for unregistered sites (`drugs_com`, `fedex`,
`walmart_careers`, `webmd_doctor`), tighten `fetch_assets.sh` to match archive
names against the registered site list instead of comparing counts.
2. **`nvidia.tar.gz` at that revision contains bare parent-directory members**
(`nvidia/`, `nvidia/static/`), so the repo-side validator rejects it:

   ```
   $ python3 scripts/validate_asset_archive.py nvidia.tar.gz nvidia
   ValueError: unexpected managed path: 'nvidia/static'
   ```

   Clearing condition and the exact repair are in "Asset archive conformity"
   below.

The previously pinned revision `070123d74c01a8b29808201be85462fd7d0ec3c4` has 26
entries and no `nvidia.tar.gz`, so it cannot prepare this candidate either. The
older candidate archive from HF PR #38 (`2707761e4041a492379ea227f09b3bd9ea838a02`,
sha256 `89e0d0d21000bb94acaeaa329fd28a1264afa05f40834c0f3e3cee5c3a2ae9a1`) does
pass the validator but was rejected as a pin: its seed is stale (the Jetson
descriptions lost the kit/module identity text, the RTX 5060 Ti is named without
`16GB` and its `recommended_psu_watts` is 550 while the page's own source note
says 600 W, and the RTX 5070 tagline loses the memory mention), and that revision
carries archives for only 17 of the 24 registered sites.

### Asset archive conformity

`nvidia.tar.gz` at the pinned revision must be re-packed before the pinned
revision can be fetched. The archive in HF PR #75 carries two bare
directory members, `nvidia/` and `nvidia/static/`, and
`scripts/validate_asset_archive.py` rejects the second one:

```
$ python3 scripts/validate_asset_archive.py nvidia.tar.gz nvidia
ValueError: unexpected managed path: 'nvidia/static'
```

Re-packing with the canonical command from `scripts/extract_assets.sh` removes
them without touching any content member (verified: only those two entries differ,
and the extracted trees are byte-identical, seed sha256
`2143c954def96cc921760ab2bea79fe119de3d73212d1b01daf6c61792c2b38d`):

```bash
# member list exactly as scripts/extract_assets.sh builds it
mkdir -p /tmp/nvidia-pack/sites && tar -xzf nvidia.tar.gz -C /tmp/nvidia-pack \
  nvidia/instance_seed nvidia/static/images
mv /tmp/nvidia-pack/nvidia /tmp/nvidia-pack/sites/
cd /tmp/nvidia-pack && tar --exclude='._*' -czf nvidia.tar.gz -C sites \
  nvidia/instance_seed nvidia/static/images
```

Resulting artifacts (both pass `validate_asset_archive.py`):

| Artifact | Members | Bytes | SHA-256 |
| --- | --- | --- | --- |
| exact re-pack of HF PR #75 content | 40 | 6,704,337 | `987c6ed102f7165e8131c6bcddaae62554f613cd89175a39cd40242ac65a5843` |
| re-pack without the unreferenced `static/images/series/geforce-rtx-40-super-family.png` | 38 | 6,521,457 | `c3f82009d18270c91889b8f6e1a59f310e41951311aca0fd09a759b51be28229` |

The second artifact is the recommended upload: that series image is rendered by
no route (`grep -rn 40-super-family sites/nvidia/` returns nothing), and the
23 image files the templates do reference are all present. After replacing the
archive, the repo-side steps of `fetch_assets.sh` run clean end to end
(`validate_asset_archive.py` → `extract_asset_archive.py` → site boot), which is
what `_wh_review_tools/pr107-fixes/fixes/B2/after.txt` records. The replacement
itself is an HF write and therefore a blocker for this repository.

## 🤝 Contribute

We have built 23 high-quality mirrors covering the [WebVoyager](https://github.com/MinorJerry/WebVoyager) benchmark. The next goal is **100+ sites**, covering everything in [Online-Mind2Web](https://huggingface.co/datasets/osunlp/Online-Mind2Web). We are inviting the community to build this together.

There are two ways to join the author list:

### 🛠️ Track A — Contribute a new website

Use a coding agent to build a new mirror (frontend + backend + database + tasks). Contributing **one website** qualifies you for consideration on the final paper's author list.

1. Browse the [Contribution Track Sheet](https://docs.google.com/spreadsheets/d/1vZsrQjy9nJKze58fx4kbQtFi85NjVXIWCFyu3ShD7gk/edit?gid=0#gid=0) and pick an unclaimed site.
2. Submit the [Contribution Request Form](https://forms.gle/ngcD1rzAfUEphNmRA) to claim it. We lock the site to prevent duplicate work.
3. Follow the [Website Contribution Guide](https://aiming-lab.github.io/webharbor.github.io/guide-create.html) and [CONTRIBUTING.md](CONTRIBUTING.md) to build and open a PR. 

### 🔍 Track B — Review environments

Review submitted mirrors for visual fidelity, functional correctness, and task grounding. **Reviewing 5 environments** earns a spot on the author list.

1. Browse open [Pull Requests](https://github.com/aiming-lab/WebHarbor/pulls).
2. Check whether the submitted environment supports its proposed tasks, and whether those tasks are meaningful and challenging.
3. Follow the [Review Pipeline](https://aiming-lab.github.io/webharbor.github.io/guide-review.html) for systematic verification.

### Acknowledgement

Any other improvement — bug fixes, UI polish, data enrichment, task suggestions, or even feedback, qualifies for the paper's acknowledgement section.

## 🤗 Resources

| Name | Link |
| --- | --- |
| 🏠 WebHarbor Project Page | [WebHarbor](https://aiming-lab.github.io/webharbor.github.io/) |
| 🤗 HuggingFace Dataset | [ChilleD/WebHarbor](https://huggingface.co/datasets/ChilleD/WebHarbor) |
| 💻 WebHarbor GitHub | [Code Repo](https://github.com/aiming-lab/WebHarbor) |
| 📊 Contribution Track Sheet | [Google Sheet](https://docs.google.com/spreadsheets/d/1vZsrQjy9nJKze58fx4kbQtFi85NjVXIWCFyu3ShD7gk/edit?gid=0#gid=0) |
| 📝 Contribution Request Form | [Google Form](https://forms.gle/ngcD1rzAfUEphNmRA) |

## Citation

WebHarbor is initiated by UNC-Chapel Hill and Microsoft, with contributions from the broader community. If you have any questions, please contact us via `webharborcomm at gmail dot com` or `zhaoyang at cs dot unc dot edu`. 

```bibtex
@misc{webharbor2026,
  title        = {WebHarbor: Docking Real Websites for Evolving GUI Agent Environments},
  author       = {{WebHarbor Team and Contributors}},
  year         = {2026},
  url          = {https://aiming-lab.github.io/webharbor.github.io},
  note         = {Project website.}
}
```
