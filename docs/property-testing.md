# Property-based security testing

The property suite generates bounded synthetic records to exercise canonicalization,
integrity bindings, replay resistance, and audit-chain reconstruction. It complements the
fixed regression tests in `tests/`; it is not a formal proof, cryptographic analysis, or
substitute for independent review.

## What the suite covers

| Area | Module | Approach |
|---|---|---|
| Canonical JSON round trip, fixed point, and digest input | `test_property_canonicalization.py` | Generated JSON values |
| Mapping order invariance at every depth; list order sensitivity | `test_property_canonicalization.py` | Generated values and permutations |
| Scalar type distinctness, numeric boundaries, Unicode, escaping | `test_property_canonicalization.py` | Generated scalars plus explicit boundary examples |
| Non-finite, unsupported, and unencodable values | `test_property_canonicalization.py` | Every rejected value at several nesting positions |
| Non-string object keys | `test_property_canonicalization.py` | Every formerly coerced key type at generated depths, containers, and insertion positions |
| Store canonicalization and write boundary | `test_store_canonicalization.py` | Fixed invalid-key/non-finite cases, unchanged valid legacy hashes, and a synthetic connection that records attempted writes |
| Candidate and lifecycle-record field mutation | `test_property_replay.py` | Every hash-bound field, enumerated in each example |
| Evidence insertion, removal, substitution, duplication, reordering | `test_property_replay.py` | Every variant, checked by the bundle and the verifier |
| Tenant, case, and run reuse | `test_property_replay.py` | Bundle, compiler, approval, and authorization boundaries |
| Exact-use purpose, audience, and output replay | `test_property_replay.py` | Every replay dimension in each example |
| Rehashed linked-record and manifest substitution | `test_property_replay.py` | Candidate, verification, approval-link, scope, authorized-output, reason, and manifest bindings with recomputed record hashes |
| Assurance Packet authorized-output substitution | `test_property_replay.py` | Rehashed authorization and packet |
| Runtime-adapter context binding | `test_property_replay.py` | Every trusted `AdapterContext` field |

Security-relevant fields and replay dimensions are enumerated inside each generated example,
so coverage does not depend on random selection. Each property first checks a valid baseline,
so a rejection is attributable to the intended mutation. Field-enumeration guards fail when a
record gains a field that the suite does not yet mutate.

The canonicalization properties test the current Python contract in
`provable_agent_reference.canonical`: string-keyed mappings (other key types raise `TypeError`
instead of being converted), sorted keys, compact separators,
UTF-8 output without ASCII escaping, and rejection of non-finite numbers. Integers outside
JavaScript's safe range are accepted by this contract but are not cross-language
interoperable; the DSSE profile rejects them separately.

## Run the standard profile

Install the development dependencies and run the property modules through the repository's
standard `unittest` runner:

```bash
python -m pip install -e '.[dev]'
HYPOTHESIS_PROFILE=ci python -m unittest discover \
  -s tests -p 'test_property*.py' -v
```

On PowerShell:

```powershell
$env:HYPOTHESIS_PROFILE = "ci"
python -m unittest discover -s tests -p "test_property*.py" -v
```

The `ci` profile allows up to 100 generated examples per property, has no per-example
deadline, and prints a reproduction blob when Hypothesis finds a failure. The full test suite
uses this profile in validation and release workflows. `tests/test_hypothesis_setup.py`
fails if either profile drops below its documented floor; an unknown `HYPOTHESIS_PROFILE`
value fails instead of falling back to a smaller profile.

## Run the extended profile

Use the 1,000-example profile before changing canonicalization, record hashes, authorization,
audit relationships, or runtime adapters:

```bash
HYPOTHESIS_PROFILE=extended python -m unittest discover \
  -s tests -p 'test_property*.py' -v
```

Both profiles use deterministic assertions over generated inputs. Hypothesis may explore those
inputs in a different order between runs unless a specific failure is pinned.

## Report example counts honestly

`max_examples` is an upper bound. Hypothesis stops early when a strategy's input space is
exhausted, and it can discard examples rejected by `assume`. To measure what actually ran,
enable Hypothesis observability and count test-case records per property:

```bash
HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY=1 HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_NOCOVER=1 \
  HYPOTHESIS_PROFILE=extended \
  python -m unittest discover -s tests -p 'test_property*.py'
```

Records are written under the ignored `.hypothesis/observed/` directory. Report the counts
together with the Python and Hypothesis versions, and do not treat configured maximums as
executed counts.

## Reproduce and preserve a failure

1. Record `python --version` and `python -m pip show hypothesis`. The printed
   `@reproduce_failure(...)` decorator embeds the Hypothesis version; a blob only replays
   under that version.
2. Re-run the exact failing test with the printed decorator, for example
   `python -m unittest tests.test_property_replay.ReplayResistancePropertyTests.<name> -v`
   from the repository root with `tests` on `PYTHONPATH`.
3. Confirm the minimized example fails without relying on local `.hypothesis/` state, for
   example by deleting that directory first.
4. After security review, convert the minimized input into an explicit `@example(...)` or a
   small fixed regression test, then remove the temporary reproduction decorator.
5. Record the security invariant and expected fail-closed behavior in the test name or
   comment. Report suspected vulnerabilities privately as described in `SECURITY.md` before
   committing a public reproduction.

The local `.hypothesis/` database is ignored and must not be treated as the regression corpus.
Checked-in `@example` cases and fixed tests are the portable corpus used by CI and reviewers.

## Data and resource bounds

Strategies deliberately use short identifiers, bounded text, bounded recursive JSON
(`max_leaves=20`, at most five items per collection), shallow record bundles, and synthetic
`synthetic://` sources. The suite makes no network or model calls and needs no credentials.
Do not add credentials, customer data, production traces, private prompts, or proprietary
evidence to strategies or regression examples.

When adding a property, keep generated structures bounded, avoid network and wall-clock
dependencies, and assert an externally meaningful invariant rather than mirroring the
implementation line by line. Inside `@given` tests, label enumerated dimensions with
`case_label(...)` rather than `subTest`, which Hypothesis disables for generated tests.
