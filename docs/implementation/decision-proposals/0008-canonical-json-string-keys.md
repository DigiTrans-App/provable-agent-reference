# Decision 0008 proposal: Require string object keys before canonical serialization

Status: **accepted** by maintainer John Agbekponou on 2026-10-30 UTC in
[RFC #51](https://github.com/DigiTrans-App/provable-agent-reference/issues/51).
The [accepted ADR](../../decisions/0008-canonical-json-string-keys.md) records the decision,
compatibility evidence, and one-time independent-review exception for the F-2 implementation
PR. All required GitHub checks remain mandatory. No protocol document changes with it.
Tracking issue: #11 (reference only; closed as completed on 2026-10-30 after PR #53).

## 1. Problem and motivation

`canonical_json` and `sha256_uri` delegate to Python's JSON serializer, which converts some
non-string dictionary keys to strings. Distinct Python inputs therefore produce identical
canonical text and digests:

| Python key | Serialized as | Same bytes as |
|---|---|---|
| `1` (and `int` subclasses) | `"1"` | `{"1": ...}` |
| `True` | `"true"` | `{"true": ...}` |
| `None` | `"null"` | `{"null": ...}` |
| `1.5` | `"1.5"` | `{"1.5": ...}` |

The conversion also applies inside nested dictionaries, lists and tuples. This is an ambiguity
introduced by input conversion before hashing. It is not a SHA-256 collision, and no
authorization bypass has been demonstrated. Property tests for issue #11 require that ambiguous
values fail before entering a trusted hash path.

## 2. Trust-boundary impact

Canonical bytes are inputs to record hashes, the packet hash, and the DSSE payload. The
boundary affected is the in-process Python API between a caller-built value and those hashes.
The JSON wire representation is unaffected: a JSON object member name is always a string, so a
document parsed from valid JSON can only contain string keys. Valid framework-produced records
use string-keyed payloads and finite numbers and are not affected. The control-plane store
currently has a separate serializer; this proposal makes it use the same validated JSON
serializer so persistence and reconstruction cannot retain the coercion through that path.

## 3. Proposed normative requirements

1. Before producing canonical text or a canonical digest, an implementation MUST reject any
   object key that is not a string, at every depth reachable through supported containers.
2. The Python reference MUST raise `TypeError` for such keys and MUST NOT convert, skip or
   coerce them. The error message names the key type only and does not include input values.
3. Canonical text, UTF-8 bytes and digests of inputs whose keys are all strings MUST be
   unchanged, including key sorting, compact separators, Unicode preservation, array order,
   number formatting, tuple-as-array serialization and non-finite rejection.
4. The raw-bytes path of `sha256_uri` is unchanged; `canonical_json(bytes)` remains unsupported.
5. The control-plane store MUST use the shared canonical serializer and reject non-finite
   numbers as well as non-string keys. Its existing JSON-only `sha256_uri` wrapper MUST continue
   rejecting raw bytes rather than inheriting the core helper's separate bytes path.

## 4. Alternatives considered

- **Keep coercion and document it.** Rejected: it leaves distinct inputs with identical hashes.
- **Coerce deliberately with `str()` or `default=str`.** Rejected: it reproduces the ambiguity
  (`str(1) == "1"`) and widens the accepted input set.
- **Encode non-string key types into the canonical form.** Rejected: it introduces a new typed
  representation and compatibility contract instead of enforcing the existing JSON domain.
- **Reject only at the top level.** Rejected: nested values carry the same ambiguity.
- **Replace the JSON encoder.** Rejected for this change: `JSONEncoder.default()` does not
  validate object keys, and replacing encoding internals adds compatibility and maintenance
  work beyond the focused input validation needed here.

## 5. Compatibility and migration

- **Wire and protocol:** unchanged. Valid JSON documents, existing records, packets, hashes,
  DSSE envelopes and committed vectors produce identical bytes. No protocol version change is
  proposed; `0.3.0-candidate.1` stays as is.
- **Python API:** narrower. Calls that previously succeeded with non-string keys now raise
  `TypeError`. This deliberately rejects malformed typed input. The store additionally rejects
  non-finite values with `ValueError`. This PR does not publish a package or change its version;
  the next release must document these narrowed APIs and use a new package version under the
  release policy. Existing release assets must not be overwritten.
- **Behavior of exact-use authorization:** an `output` containing a non-string key now raises
  `TypeError` from `authorize_exact_use` instead of returning an `EXACT_USE_MISMATCH` record.
- **Circular input with a non-string key:** now reports the key `TypeError` before the existing
  circular-reference `ValueError`. Other circular input still raises the same `ValueError`.
- **Migration for callers:** build inputs with deliberately validated string keys. Do not wrap
  keys in `str()` blindly, which can merge distinct keys (for example `1` and `"1"`).
- **Previously serialized data:** JSON produced before this change has already lost the
  original Python key types. This change cannot identify or repair that loss retroactively.
- **Stored data:** hashes of valid finite, string-keyed records remain unchanged. No live
  database is inspected or migrated by this change. The old helper accepting `NaN`/infinities
  does not establish that PostgreSQL accepted those non-JSON tokens. Any out-of-contract data
  needs explicit investigation; do not silently normalize or rehash historical records.

## 6. Privacy and security considerations

Rejection is fail-closed and happens before any bytes are produced or hashed. Error messages do
not echo keys or values. The validator walks containers iteratively, adds no recursion limit of
its own, skips containers already on the current path so circular input still reaches the
serializer's circular-reference check, and visits shared containers once. The added cost is one
pass over reachable containers without copying.

The separate encoder in `src/provable_agent_reference/control_plane/store.py` is replaced by an
import of the shared serializer. Its JSON-only hash wrapper remains, so bytes do not become a
new accepted input. A synthetic connection test verifies that malformed activity records fail
before an INSERT is attempted; it does not claim to test PostgreSQL persistence or rollback.

## 7. Test vectors and failure cases

- Each coerced key type at the root and inside dictionaries, lists, tuples and mixed nesting is
  rejected by `canonical_json` and `sha256_uri`; each string counterpart is accepted.
- Other hashable non-string keys stay rejected; mixed string and non-string maps are rejected
  regardless of insertion position or value.
- Shared non-cyclic containers are accepted; direct and indirect cycles are rejected without
  hanging; the recursion boundary is unchanged.
- A pinned fixture produced by the unfixed implementation keeps its exact canonical text and
  digest; raw-bytes hashing is unchanged.
- `sign_assurance_packet` and `authorize_exact_use` reject non-string keys while their string
  counterparts succeed.
- Store serialization and hashing reject non-string keys and non-finite values at nested
  positions. Valid legacy activity hashes still reach the write boundary unchanged; malformed
  bodies with matching legacy hashes are rejected before that boundary.
- Property tests place every coerced key category at generated depths and positions.

## 8. Implementation and rollout plan

1. Record this accepted decision in an ADR under `docs/decisions/` with the implementation.
2. Include the shared store serializer and its compatibility tests in the same change.
3. Require all GitHub checks on the final PR head before squash merge.
4. Note the narrowed Python API in the release notes for the next package release.

## 9. Unresolved questions and non-goals

The maintainer has accepted this input-domain clarification and its compatibility evidence.
Package release scheduling is separate from this source change.
The existing JSON wire contract and protocol identifier are retained; no new conformance profile
or assurance claim is introduced.

Non-goals: key coercion, `default=str` or any other conversion, key skipping, a new depth or
recursion policy, raw JSON duplicate-member handling, a new canonicalization standard, float or
Unicode normalization, cross-language key semantics beyond JSON strings, record or schema
redesign, live database inspection or migration, and changes to database transaction semantics.
