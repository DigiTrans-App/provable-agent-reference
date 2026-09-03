# Maintainer review setup

This runbook turns the repository's review policy into GitHub controls. Apply it after this documentation change is accepted.

## Platform constraint

`DigiTrans-App/provable-agent-reference` is currently owned by the GitHub user account `DigiTrans-App`, not a GitHub organization. GitHub teams therefore cannot own paths or receive review requests in this repository. Use named individual accounts. Consider transferring the repository to an organization if durable team-based ownership is required.

## Onboard a reviewer

1. Confirm the reviewer's exact GitHub username and relevant expertise outside a public issue.
2. In **Settings → Collaborators**, invite that individual with the minimum role that GitHub permits for required approvals. For an account-owned repository this may grant write access, so protect `main` before or immediately after the invitation is accepted.
3. Verify that the invitation is accepted and that the intended permission is active.
4. Request the individual on a small, non-sensitive pull request before assigning ownership.
5. After the reviewer confirms availability, add the username to `CODEOWNERS` for the appropriate paths in a separate reviewed pull request.
6. Record no personal email address, phone number, or other contact data in the repository.

Do not invite a shared account or use the repository owner as evidence of independent review.

## Reviewer contingency

Pending or declined invitations do not relax the approval policy. Use the following escalation
path when the initial reviewer pool is unavailable:

1. After three business days, send one concise reminder with the pull-request URL, requested
   review scope, expected effort, and a clear option to decline.
2. Confirm **Settings → Moderation options → Code review limits**. In a public repository,
   GitHub permits any user to submit an approving or changes-requested review by default. If
   review limits are enabled, only users with explicit read access or higher can submit those
   decisions. A qualified reviewer may therefore review the public pull request directly
   without repository write access when the repository settings permit it.
3. After five business days without two available reviewers, expand the candidate pool. Select
   named individuals with relevant public work, no authorship of the change, no shared account,
   and no undisclosed conflict. Ask for availability before assigning paths or granting access.
4. If volunteer coverage is still unavailable after ten business days, commission an
   independent review. Record the reviewer's scope, relevant expertise, compensation and
   conflicts, and require the same exact-head approval and public findings process. Payment
   must not depend on approval.
5. If reviewer scarcity becomes recurring, prepare a separately reviewed migration from the
   account-owned repository to a GitHub organization with team-based ownership and at least two
   administrators. Do not transfer the repository as an ad hoc response to one blocked pull
   request; first inventory URLs, Actions, environments, secrets, packages, rulesets, and
   release integrations.

While escalation is in progress, keep security-critical pull requests open as candidates. CI,
adversarial testing, documentation, and non-release review artifacts may continue, but do not
lower approval counts, count the author or an AI system as an independent reviewer, publish a
stable release, or use an administrative bypass for a non-urgent change.

GitHub's current review behavior is documented in
[Managing pull request reviews](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-pull-request-reviews-in-your-repository)
and [Requesting a pull request review](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/requesting-a-pull-request-review).

## Protect `main`

Create a branch ruleset targeting the default branch and enable:

- require a pull request before merging;
- require at least one approval;
- dismiss stale approvals when new commits are pushed;
- require approval of the most recent reviewable push by someone other than the pusher;
- require review from code owners after named owners are configured;
- require all conversations to be resolved;
- require status checks to pass and require the branch to be up to date;
- block force pushes and branch deletion; and
- prevent bypass except for a narrowly controlled emergency role.

Select required checks from a successful pull request run so the stored check names exactly match GitHub's emitted contexts. The expected gates include the Python 3.11 and 3.12 validation jobs, CodeQL analysis, and Dependency Review when dependency files change.

GitHub's approval count is repository-wide. Until a path-aware policy check is introduced, enforce the second approval required for security-critical changes through the pull request classification and maintainer merge gate. If the reviewer pool can sustain it, setting the repository-wide approval count to two is the stronger alternative.

## Merge settings

In **Settings → General → Pull Requests**:

- allow squash merging only;
- use the pull request title as the squash commit title;
- enable automatic deletion of head branches; and
- enable contributors to update out-of-date branches when available.

Do not enable automatic merging until required approvals and checks are enforced.

## Verification

Open a test pull request and confirm that:

1. direct or force pushes to `main` are rejected;
2. the required checks appear and block merge while pending or failing;
3. an approval is dismissed after a material new commit;
4. unresolved conversations block merge;
5. a security-critical pull request records two approvals; and
6. the final approval and checks correspond to the exact commit that is merged.

Review collaborator access and the `CODEOWNERS` roster at least quarterly.
