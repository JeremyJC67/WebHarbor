# Amtrak asset candidate

The original contributor published `amtrak.tar.gz` at the immutable dataset
revision `lxr-max/WebHarbor@eac108f14be667b7e78972b0805d116ddea931d2`.
The reviewed archive SHA-256 is
`22f0132a5f9bfee45a641e8172050a94bb4fc0de4ad45f1d9e52deb50eb37f34`.
It has 308 validated managed members. Its SQLite seed SHA-256 is
`b245928c8b03741d17aa7c27f863a499e44034af607902cfa9c8d099c93591b4`.

`.assets-revision` temporarily scopes this site's repository, revision and
archive digest; `scripts/fetch_assets.sh amtrak` verifies the digest before
extraction. Other sites retain their existing pins. There are no seed or image
changes in this fix, so the original bundle can be published unchanged.

Required integration gate: merge this archive into `ChilleD/WebHarbor`, replace
the contributor-repository override with the immutable merged central revision,
and revalidate a clean fetch, full Docker build and reset before merging code.
The contributor pin is not a claim that central HF publication has occurred.

The seed's schedules/fares and generated SVG illustrations are deterministic
benchmark fixtures, not verified live Amtrak facts or source photographs.
