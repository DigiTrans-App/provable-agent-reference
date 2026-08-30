# Protocol candidate

The protocol candidate defines portable requirements independently of the Python reference
implementation. Its current version is `0.3.0-candidate.1`.

## Normative language

The terms **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** describe
normative requirements. A requirement is binding only when it appears in a candidate or stable
protocol document and is associated with a versioned conformance profile.

## Documents

- [Lifecycle state machine](lifecycle.md)
- [Assurance Packet candidate](assurance-packet.md)
- [Conformance profiles](conformance-profiles.md)

JSON Schema validates record shape. It cannot prove hash correctness, cross-record bindings,
identity, source authenticity, completeness, or conformance. Implementations MUST execute the
semantic checks required by the claimed profile.

## Compatibility policy

- Candidate versions MAY make incompatible changes after public review.
- Stable protocol versions MUST use semantic versioning.
- Additive optional fields require a minor version change.
- Removing or redefining a field, hash input, state transition, or profile requirement requires
  a major version change.
- A verifier MUST reject an unsupported protocol version rather than guess compatibility.
- Canonicalization and hash inputs MUST be specified with test vectors before a stable release.

Normative changes follow the [change process](../change-process.md).
