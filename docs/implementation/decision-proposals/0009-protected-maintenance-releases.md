# Decision 0009 proposal: Protected maintenance-line releases

Status: **accepted** on 2026-10-30 as [ADR 0009](../../decisions/0009-protected-maintenance-releases.md).
Founding maintainer John Agbekponou accepted this decision and authorized bounded, one-time
independent-review exceptions for its main-controls and v0.2.1 implementation PRs in
[RFC #54](https://github.com/DigiTrans-App/provable-agent-reference/issues/54). All required CI,
exact-head checks, protection restoration and release verification remain mandatory. Automated
technical validation does not count as human approval. This proposal is retained as the design
record; acceptance does not change the status of proposals 0001 through 0007.

Related: `SECURITY.md` (supported versions), `docs/maintainer-review-setup.md`,
`scripts/verify_release.py`, `.github/workflows/release.yml`.

## 1. Problem and motivation

`SECURITY.md` promises security fixes for "the latest released minor version and the `main`
branch". The latest released minor is 0.2 (`v0.2.0`, annotated tag `fdce5a8` ->
`106b91ea790bf96b059d5d60c07f79f16c02eeea`). `main` (`31ab2e1`) is 26 commits ahead of it,
still reports package version `0.2.0`, and contains unreleased features. A fix for 0.2.x
therefore cannot ship from `main` without also shipping unreleased changes.

The release workflow cannot currently publish a patch on the 0.2 line:

1. `verify_release.py` accepts a tag only if its commit is an ancestor of
   `refs/remotes/origin/main`, and the workflow fetches only `main`. A backport on a branch
   cut from `v0.2.0` is not an ancestor of `main` and is rejected.
2. A pushed tag runs `release.yml` **as it exists in the tagged commit**. A branch cut from
   `v0.2.0` contains the original `release.yml`: no ancestry check, no attestations, no
   `pip-audit`, a single `contents: write` token.
3. Pull requests into a maintenance branch would run only `validate (3.11/3.12)`, because
   `codeql.yml` and `dependency-review.yml` filter `pull_request` to `branches: [main]`.
4. No ruleset covers any `release/*` branch. The legacy `origin/release/v0.2.0` (`86a7b85`)
   has the same tree as the tag but different, pre-squash history and no protection.
5. `gh release create` is called without `--latest`/`--prerelease`, so GitHub selects the
   "Latest" label automatically. A maintenance patch published after a newer minor would be
   mislabeled "Latest".

The naive fix, accepting any branch, removes the control the ancestry gate provides. This
proposal defines a narrow, explicitly approved maintenance path instead.

## 2. Trust-boundary impact and threat model

**Boundary.** The only publication authority is a push of a `v*.*.*` tag. Tag creation is
restricted to repository admins by ruleset "Protect release tags" (creation, update, deletion,
non-fast-forward; admin bypass `always`). The ancestry gate in the workflow is the second
control: it ensures a tag, even from an admin, points to content that arrived through the
reviewed, protected branch for that version line. After this proposal the trusted set is
{`main`, each branch named in the reviewed allow-list} rather than only `main`.

**Actors.** (A) a collaborator with write access (can push unprotected branches, open PRs);
(B) an admin acting in error or with a compromised session (can create tags and bypass the tag
ruleset); (C) a compromised third-party action or dependency; (D) an outside contributor.

| # | Threat | Control after this proposal |
|---|---|---|
| T1 | A pushes an arbitrary branch and an admin (or B) tags it | Ancestry must be against the allow-listed, ruleset-protected branch for the tag's line; arbitrary branches are not fetched or consulted |
| T2 | Tag on an unprotected maintenance branch created before protection exists | Rollout orders protection before any push; `base_commit` pin; tip == base verified before the first PR merges |
| T3 | Workflow-at-tag downgrade: tag a commit whose `release.yml` is the old v0.2.0 workflow | Branch is created at `106b91e` and the first reviewed PR ports the hardened `release.yml` and `verify_release.py` before any tag; PRs to the branch need two approvals under a bypass-free ruleset; a repository test asserts the workflow calls the verifier (W01). Not enforceable from inside the workflow (it is self-referential), so review plus ruleset is the real control. v0.2.0's workflow is never used for a release |
| T4 | Line/version mismatch: `v0.2.1` tagged on `main`, `v0.3.0` tagged on `release/0.2.x` | Branch is derived from the tag's own MAJOR.MINOR through the allow-list; the other branch is never accepted for that tag (S03, S04) |
| T5 | Reuse of legacy `release/v0.2.0` or a branch recreated from unrelated history | Branch name must match `release/<MAJOR>.<MINOR>.x`; allow-list pins `base_commit` = `106b91e`; a tagged commit must descend from it (S06, S07); legacy history does not |
| T6 | Allow-list tampered on a branch to approve a new line/branch | Authority is the copy on `main` (two-approval protected path); the tagged tree must agree on `main_line` and the selected entry (S09-S11) |
| T7 | Tag moved or re-pointed | Tag ruleset blocks update/delete for non-admins; `gh release create` fails if a release already exists; checked-out HEAD must equal `GITHUB_SHA`; recommend enabling immutable releases (see 9) |
| T8 | Rollback via old patch number (`v0.2.1` again, or `v0.2.0` over `v0.2.3`) | Patch must be greater than every existing tag in the line (S19, S20) |
| T9 | Unpinned/compromised actions (C) | Unchanged: full-SHA pins, `persist-credentials: false`, `validate_repo.py` workflow checks, Dependabot, `pip-audit` in release and validate |
| T10 | Over-broad token | Unchanged: top-level `contents: read`; `contents/id-token/attestations/artifact-metadata: write` only on the publish job |
| T11 | Release PRs merge without CodeQL/dependency review because the checks never report | `pull_request.branches` extended to `release/*.*.x`; ruleset requires all four checks; a required check that never reports blocks merge (fail closed) |
| T12 | Release mislabeled "Latest" or prerelease after creation | Flags computed by the verifier from tag state and passed explicitly at `gh release create`; no later `gh release edit` step |
| T13 | Admin edits the ruleset to bypass review | Out of scope for in-repo controls; requires audit-log review. Branch ruleset has no bypass actors, so a non-urgent bypass requires a visible ruleset edit |

**Non-goals.** This does not authenticate human identity, replace independent review, protect
against a compromised admin who also controls two reviewers, or add signing keys. Attestations
remain GitHub build-provenance only.

## 3. Proposed normative requirements

### 3.1 Allow-list file

R1. `.github/release-lines.json` (schema_version 1) MUST exist on `main` and be changed only by
security-critical PR (two approvals; add `.github/release-lines.json` to the security-critical
list in the PR template):

```json
{
  "schema_version": 1,
  "main_line": "0.3",
  "maintenance_lines": [
    {
      "line": "0.2",
      "branch": "release/0.2.x",
      "base_commit": "106b91ea790bf96b059d5d60c07f79f16c02eeea"
    }
  ]
}
```

R2. `line` is `MAJOR.MINOR` (no leading zeros except `0`); `branch` MUST equal
`release/<line>.x` exactly; `base_commit` MUST be a 40-hex SHA. `main_line` MUST NOT also appear
as a maintenance line. Unknown keys, a wrong `schema_version`, duplicate lines or malformed JSON
MUST fail closed. `main_line` is `0.3` because `main` is already ahead of `0.2.0`; patches on
`0.2` come only from the maintenance branch. Changing it to another value is a reviewed
decision of the next main release.

R3. The verifier MUST read the authoritative allow-list from `refs/remotes/origin/main`
(`git show`) and the copy in the tagged tree. The entry for the tag's line (and `main_line`) MUST
be present and identical in both. A tag whose line is in neither, or only one, MUST be rejected.

### 3.2 Tag validation

R4. Tags MUST match `^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)((a|b|rc)(0|[1-9]\d*))?$`. Any
other tag form MUST be rejected before it is used in a ref or path. Existing checks remain:
`tag == "v" + pyproject version` and `docs/releases/<tag>.md` exists.

R5. Routing is by the tag's own `MAJOR.MINOR`:

- equals `main_line`: the tagged commit MUST be contained in `refs/remotes/origin/main`
  (today's behavior);
- equals an approved maintenance `line`: `base_commit` MUST be an ancestor of the tagged commit
  AND the tagged commit MUST be contained in `refs/remotes/origin/<branch>`;
- otherwise: reject.

No other branch is fetched, consulted or accepted. A commit contained in `main` is not accepted
for a maintenance tag, and a commit contained in a maintenance branch is not accepted for a
`main_line` tag.

R6. The workflow MUST fetch only `+refs/heads/main:refs/remotes/origin/main` and the single
branch selected by R5, whose name was validated against `release/<line>.x` and the allow-list
(the verifier performs this second fetch; the branch name is never taken from the tag push
event or an input). A missing ref MUST fail closed.

R7. The checked-out `HEAD` MUST equal the `--commit` value (`GITHUB_SHA`).

R8. For a stable tag, its PATCH MUST be strictly greater than the PATCH of every existing
stable tag in the same line. Prerelease tags (R9) are exempt from monotonicity against other
prereleases but MUST be for a version not already tagged.

### 3.3 Release classification

R9. The verifier computes and emits (`$GITHUB_OUTPUT`) two booleans and the workflow passes
them explicitly:

- `prerelease` is `true` iff the tag has an `a`/`b`/`rc` segment;
- `latest` is `true` iff the tag is stable and strictly greater (by numeric
  MAJOR.MINOR.PATCH) than every other stable `v*.*.*` tag in the repository.

The publish step is `gh release create ... --latest=<latest> [--prerelease]`; there is no
post-creation relabelling. Every release line MUST use the same repository-wide
`release-publication` concurrency group with `cancel-in-progress: false`; a per-tag group
allows an older build to publish after a newer release and overwrite its Latest label.
GitHub may replace a pending run when another tag arrives; schedule one release tag at a
time and inspect cancelled or superseded runs before rerunning them. This lock coordinates
these workflows, not manual release publication or historical workflows. No other release
publisher may run during an authorized release. Decision for `v0.2.1`: it is the highest stable version, so
`latest=true`. If `v0.3.0` is released first, `v0.2.x` patches publish with `latest=false`.

### 3.4 Workflow-at-tag semantics

R10. The maintenance branch MUST carry a `release.yml`, `verify_release.py`, `validate_repo.py`,
`validate_dist.py`, `.github/release-lines.json` and `docs/releases/<tag>.md` at the tagged
commit. The v0.2.1 PR ports `release.yml` and `verify_release.py` from reviewed `main` (as
modified by this proposal) and `validate.yml`, `codeql.yml`, `dependency-review.yml` so required
checks report. Bytes are identical to `main` where the 0.2 tree allows; deviations are listed in
the PR. The release job keeps every existing step: SHA-pinned actions, `pip-audit`, test and
`validate_repo.py` gates, `validate_dist.py`, `SHA256SUMS`, `actions/attest`.

R11. A repository test MUST fail if `release.yml` stops invoking `verify_release.py` with
`--release-lines`, if any `uses:` is not SHA-pinned, or if the publish step omits explicit
`--latest`.

### 3.5 CI and rulesets

R12. `codeql.yml` and `dependency-review.yml` `pull_request.branches` become
`[main, "release/*.*.x"]`; `validate.yml` and `codeql.yml` `push.branches` become
`[main, "release/*.*.x"]`. The pattern `release/*.*.x` does not match `release/v0.2.0`.
This change MUST be on `main` and on the maintenance branch.

R13. Before any commit is pushed to `release/0.2.x` the rulesets in section 8 are active. The
branch ruleset has no bypass actors, requires two approvals, and requires the four status checks.

## 4. Alternatives considered

- **Tag the unprotected branch and let v0.2.0's workflow run.** Rejected: no ancestry,
  attestations or pip-audit; the downgrade is the threat (T3).
- **Drop the ancestry check.** Rejected: any admin mistake or compromised session could publish
  arbitrary content with a valid attestation.
- **Generic "ancestor of any `refs/heads/release/*`" check.** Rejected: any write-access user
  could create a conforming branch (T1, T5), and legacy `release/v0.2.0` would qualify.
- **Hard-code `release/0.2.x` in `verify_release.py`.** Rejected: each future line needs a code
  change in a script that is itself copied to old branches; an allow-list on `main` with a
  matching tree copy gives one reviewed place to open and retire lines.
- **Tag allow-list in GitHub repository variables.** Rejected: not reviewed through PR, not
  versioned with the code.
- **Cherry-pick the fix to `main` and release 0.2.1 from `main`.** Rejected: ships 26
  unreviewed-for-release commits in a patch and may change behavior.
- **Publish `0.3.0a1` from `main` instead.** Rejected for this fix: leaves the supported 0.2
  users without a patch and a prerelease is not "latest released minor". Remains available
  later.
- **Use legacy `release/v0.2.0` as base.** Rejected: different history from the signed-off
  tag, unprotected.
- **Release environment with required reviewers.** Not adopted yet: no environments exist and
  required-reviewer environments need the same two-person pool. Listed in section 9.

## 5. Compatibility and migration

- `main` releases: behavior unchanged except for R4 formats, R7, R8 monotonicity and explicit
  flags. `v0.2.0` is immutable and unaffected (already published; rule R8 counts it as the
  line's baseline).
- `main` gains `.github/release-lines.json` and R12 filter changes before the maintenance
  branch is created.
- Existing tests keep their signatures: `validate_release_metadata(root, tag)` and
  `validate_release_ancestry(repo, commit, ref)` stay; new functions are added.
- Users: no package or API change.
- Retiring a line: remove it from `main`'s allow-list; later tags on that line are rejected.
- `SECURITY.md` wording ("latest released minor version and `main`") is unchanged and becomes
  achievable; the release bullet is extended to mention the maintenance path.

## 6. Privacy and security considerations

No new data is collected. The allow-list holds only public ref names and a commit SHA. Branch
names and tags are validated by regex and never interpolated into shell commands or paths;
`RELEASE_TAG` and `RELEASE_COMMIT` are passed as environment variables, as today. Token
permissions are unchanged. `require_code_owner_review` is `false` on the new ruleset because
`CODEOWNERS` has only the repository owner (`* @DigiTrans-App`) as a fallback, so the setting
would add no independent review and could deadlock owner-authored PRs; the second approval is
enforced by the count. After bootstrap, the branch ruleset has **no bypass actors**, unlike `main` (admin,
`pull_request` mode), because this branch is a direct publication path. An urgent fix follows
the `GOVERNANCE.md` exception: a visible, recorded ruleset change and retrospective review, not
a silent bypass. Residual risk: an admin can edit rulesets; mitigate with audit-log review.
Approvals count toward the ruleset only from users with write access on this account-owned
repo, so two approvers with write access are needed for the branch ruleset to be satisfiable.
If not available the release waits (consistent with `maintainer-review-setup.md`).

## 7. Test vectors and failure cases

The full set is implemented in `tests/test_release_lines.py` (scenarios S01-S30 against
temporary git repositories, static workflow checks W01-W07). Summary:

| Tag | Commit | Expected |
|---|---|---|
| `v0.2.1` | tip of `release/0.2.x` (descends from `106b91e`) | accept, `latest=true` |
| `v0.3.0` | `main` | accept, `latest=true` |
| `v0.2.1` | `main` tip | reject (not in maintenance branch) |
| `v0.3.0` | `release/0.2.x` tip | reject (not in `main`) |
| `v0.2.1` | unmerged side branch | reject |
| `v0.2.1` | legacy `release/v0.2.0` history | reject (base commit) |
| `v0.4.0`, `v1.0.0` | any | reject (not approved line) |
| `v0.2.1` | allow-list missing/different on `main` or tree | reject |
| `v0.2.1` again / `v0.2.2` below `v0.2.3` | any | reject (monotonic) |
| `v0.2.2` while `v0.3.0` exists | maintenance tip | accept, `latest=false` |
| `v0.3.0rc1` | `main` | accept, `prerelease=true`, `latest=false` |
| `v0.2.1.post1`, `v0.2`, injected characters | any | reject (format) |
| `release/0.2.x` ref not fetched | any | reject (fail closed) |

## 8. Implementation and rollout plan

Implementation in this change: `.github/release-lines.json`, `scripts/verify_release.py`,
`.github/workflows/release.yml`, the branch filters of `codeql.yml`, `dependency-review.yml` and
`validate.yml`, and `tests/test_release_lines.py`. Ruleset bodies (`release-0.2.x-branch.json`,
`release-branches-creation.json`) are supplied to maintainers with the PR and are not applied by
it. The existing tag ruleset is kept as is: tag creation
by admin only, no new bypass, no delta required. Optionally enable the repository's immutable
releases setting before step 4 (a setting change by a maintainer, not part of the PR).

Ruleset choices:

- Branch ruleset targets exactly `refs/heads/release/0.2.x`. Each new line adds a reviewed
  ruleset; wildcards are avoided so new lines do not become protected by accident.
- Rules: deletion, non_fast_forward, required_linear_history, `pull_request`
  (`required_approving_review_count: 2` as a floor equal to the governance minimum for
  security-critical changes, dismiss stale reviews, last-push approval, thread resolution,
  squash only), required status checks strict with `integration_id` 15368 (GitHub Actions) for
  `validate (3.11)`, `validate (3.12)`, `Analyze (Python)`, `Review dependency changes`.
- Approval count is 2 (main uses 1) because every change to this branch is release automation or
  a security fix, so every PR is security-critical; this removes the reliance on classification.
- Fields `require_extra_approval_for_unattributed_changes` (`true` on main, read from the API)
  is not in the POST body because it is not documented for create calls; verify after creation
  and set it in the UI if offered.
- `release-branches-creation.json` (`refs/heads/release/**`, rule `creation`, admin bypass
  `always`) means only an admin can create `release/*` branches. It does not restrict updates,
  so it never blocks the PR merge flow. Existing branches (including legacy `release/v0.2.0`)
  are unaffected; retire legacy by deleting after review.

**NOT EXECUTED.** The reviewed handoff includes the exact JSON bodies. Apply settings only
with maintainer authorization, and retain each API response and ruleset ID.

Rollout order:

1. Accept decision 0009 through its RFC and ADR, and merge the main-controls PR with required
   review and checks. The experimental proposal must not silently become an accepted decision.
2. Confirm `release/0.2.x` does not exist. Apply the admin-only release-branch creation guard
   and the temporary `release-0.2.x-bootstrap.json` ruleset. The bootstrap ruleset targets
   only this branch, restricts creation/update/deletion and force pushes, and allows only
   repository admins to bypass it. Verify both are active before creating the branch.
3. Create `release/0.2.x` at exactly `106b91ea790bf96b059d5d60c07f79f16c02eeea` under that
   bootstrap lock. Verify the ref and apply the permanent two-approval, strict-status-check,
   squash-only ruleset. Verify the effective rules and the base SHA before removing only the
   temporary bootstrap ruleset. Keep the creation guard and permanent protection active.
   If any call fails, leave the bootstrap lock active and diagnose it. Never disable the
   permanent ruleset to create the branch. A matching final SHA alone cannot establish that
   no intervening ref update occurred; retain the operation responses and audit evidence.
4. Open the v0.2.1 PR into `release/0.2.x`. Confirm all four required checks actually report,
   including CodeQL and dependency review. Require the approved review policy and passing
   checks for the exact head before squash merging. No direct push to the protected branch.
5. After separate release authorization, an admin creates `v0.2.1` on the verified squash
   commit. Confirm no other publisher is active. The hardened workflow runs from that commit.
6. Verify assets against `SHA256SUMS` and `gh attestation verify`; verify version, tag SHA,
   prerelease=false and the Latest decision against the other stable tags.
7. Publish the security advisory only after artifact verification and maintainer approval.

## 9. Unresolved questions and explicit non-goals

- Bootstrap and permanent ruleset API operations remain untested on GitHub. The temporary
  admin-only lock avoids creating the branch under PR/status rules and leaves it restricted
  if setup fails. Confirm effective protection before removing that lock.
- Does `Review dependency changes` report on a PR into a branch that has no dependency graph
  baseline, and does `Analyze (Python)` for non-default-branch PRs run under default-vs-advanced
  CodeQL setup? Verify on the first release PR; if a required check never reports, the ruleset
  fails closed and the check list must be reviewed rather than dropped silently.
- Whether to enable immutable releases and a `release` environment with required reviewers.
- The GitHub CLI documents `--latest=false` and supports it in release creation. Confirm
  the runner CLI supports it and verify actual release flags after publication.
- Whether the repo should move to an organization so teams can own `CODEOWNERS` paths.
- Non-goals: signing keys, SLSA level claims beyond GitHub provenance, retroactive changes to
  `v0.2.0`, PyPI publication.
