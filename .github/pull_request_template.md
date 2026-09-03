## Summary

## Change classification

- [ ] Standard change
- [ ] Security-critical change

Security-critical areas changed (check all that apply):

- [ ] Authentication, authorization, approvals, or verification
- [ ] Canonicalization, audit evidence, or binding schemas
- [ ] Dependencies, GitHub Actions, or release automation
- [ ] Security policy, governance, or ownership
- [ ] None of the above

## Trust-boundary impact

- [ ] No change
- [ ] Model-authored contract changed
- [ ] Trusted compilation changed
- [ ] Verification, approval, authorization, or audit behavior changed

Explain any checked change and its failure modes:

## Review plan

- Requested reviewers:
- Relevant expertise:
- [ ] One independent approval is required for this standard change
- [ ] Two independent approvals, including relevant expertise, are required for this security-critical change
- [ ] The author is not counted as an approving reviewer

## Validation

- [ ] Unit tests pass
- [ ] `python scripts/validate_repo.py` passes
- [ ] Local evaluation suite passes
- [ ] `ruff check .` passes
- [ ] Tests cover each behavior change and failure mode, or this is documentation-only
- [ ] No credentials, customer data, private evidence, or proprietary DigiTrust code included
- [ ] Material AI assistance is disclosed below

## AI assistance

Describe material use of Codex or other AI tools, if any.

## Maintainer merge gate

- [ ] Required approvals apply to the current head commit
- [ ] Required checks pass for the current head commit
- [ ] Review conversations are resolved
- [ ] No unresolved security or privacy concern remains
