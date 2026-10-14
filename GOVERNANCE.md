# Governance

## Project stewardship

DigiTrans LLC is the initial steward. John Agbekponou is the founding maintainer and release manager.

## Decision model

- Routine fixes and documentation changes use maintainer review.
- Contract, security, governance, and compatibility changes require an issue or design note before implementation.
- Releases require passing CI, updated changelog notes, and review of public claims and trust-boundary documentation.
- Maintainer access may be granted to contributors with a sustained record of high-quality, security-conscious participation.

## Pull request review policy

Every change to `main` should arrive through a pull request. The author must classify the change in the pull request template and identify any trust-boundary impact.

A **standard change** requires:

- one approval from a named human reviewer other than the author;
- all required checks passing for the exact head commit;
- all review conversations resolved; and
- no unresolved security or privacy concern.

A **security-critical change** requires two named human approvals, including at least one reviewer with relevant security or domain expertise. A change is security-critical when it modifies authentication or authorization, approvals, verification, canonicalization, audit evidence, schemas that bind those records, dependency or workflow trust, release automation, `SECURITY.md`, `GOVERNANCE.md`, or `CODEOWNERS`.

The author may not approve their own change or act as the only independent reviewer. A shared account, automation identity, or repository-owner fallback is not an independent reviewer. Material changes after approval require re-review; typo-only or merge-conflict changes may retain approval only when the reviewer confirms that the reviewed behavior is unchanged.

Independent validation evidence is encouraged, but it supplements rather than replaces source review and CI. Reviewers should record limitations and unresolved risks instead of treating a passing workflow as certification.

## Reviewer ownership

`CODEOWNERS` should name active individual reviewers only after they have accepted repository access and agreed to review the assigned paths. The repository-owner entry remains a routing fallback until that roster is established; it does not satisfy the independent-approval requirement.

Maintainers should review collaborator access quarterly and promptly remove access that is no longer needed. Repository write access must not be granted to a shared or group account.

The recommended GitHub settings and reviewer-onboarding procedure are documented in [Maintainer review setup](docs/maintainer-review-setup.md).

## Urgent security fixes

Embargoed vulnerabilities should use GitHub's private security-advisory workflow. When an urgent fix cannot follow the normal public review path, preserve two-person control whenever practical, record the exception privately, and complete a retrospective review within two business days after disclosure or deployment. Urgency does not authorize publishing secrets, exploit details, or private evidence.

## Independence of the open-source project

The framework is maintained as a public, provider-neutral project. Commercial DigiTrust services may use or extend the framework, but proprietary product requirements do not automatically define the public roadmap.

## Conflicts of interest

Maintainers and reviewers should disclose material commercial interests when proposing or approving changes that advantage one provider, vendor, or deployment model. Provider-specific functionality belongs in optional adapters unless it represents a portable core contract.
