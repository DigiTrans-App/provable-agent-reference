# Property-based security testing

The property suite generates bounded synthetic records to exercise canonicalization,
integrity bindings, replay resistance, and audit-chain reconstruction. It complements the
fixed regression tests in `tests/`; it is not a formal proof, cryptographic analysis, or
substitute for independent review.

## Run the standard profile

Install the development dependencies and run the property modules through the repository's
standard `unittest` runner:

```bash
python -m pip install -e '.[dev]'
HYPOTHESIS_PROFILE=ci python -m unittest discover \
  -s tests -p 'test_property*.py' -v
```

The `ci` profile runs at least 100 generated examples per property, has no per-example
deadline, and prints a reproduction blob when Hypothesis finds a failure. The full test suite
uses this profile in validation and release workflows.

On PowerShell:

```powershell
$env:HYPOTHESIS_PROFILE = "ci"
python -m unittest discover -s tests -p "test_property*.py" -v
```

## Run the extended profile

Use the 1,000-example profile before changing canonicalization, record hashes, authorization,
audit relationships, or runtime adapters:

```bash
HYPOTHESIS_PROFILE=extended python -m unittest discover \
  -s tests -p 'test_property*.py' -v
```

Both profiles use deterministic assertions over generated inputs. Hypothesis may explore those
inputs in a different order between runs unless a specific failure is pinned.

## Reproduce and preserve a failure

1. Re-run the exact failing test with the printed `@reproduce_failure(...)` decorator.
2. Confirm the minimized example fails without relying on local `.hypothesis/` state.
3. Convert the minimized input into an explicit `@example(...)` or a small fixed regression
   test, then remove the temporary reproduction decorator.
4. Record the security invariant and expected fail-closed behavior in the test name or comment.

The local `.hypothesis/` database is ignored and must not be treated as the regression corpus.
Checked-in `@example` cases and fixed tests are the portable corpus used by CI and reviewers.

## Data and resource bounds

Strategies deliberately use short identifiers, bounded recursive JSON, shallow record bundles,
and synthetic `synthetic://` sources. Do not add credentials, customer data, production traces,
private prompts, or proprietary evidence to strategies or regression examples.

When adding a property, keep generated structures bounded, avoid network and wall-clock
dependencies, and assert an externally meaningful invariant rather than mirroring the
implementation line by line.
