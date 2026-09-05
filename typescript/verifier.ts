import { createHash, createPublicKey, verify as verifySignature } from "node:crypto";
import { readFileSync } from "node:fs";

export const PAYLOAD_TYPE = "application/vnd.digitrans.provable-agent.assurance-packet+json;version=0.3.0-candidate.1";

function fail(message: string): never { throw new Error(message); }
function object(value: unknown, name: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) fail(`${name} must be an object`);
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, expected: string[], name: string): void {
  if (Object.keys(value).sort().join("\0") !== [...expected].sort().join("\0")) fail(`${name} fields are invalid`);
}
function decodeBase64(value: unknown, name: string): Buffer {
  if (typeof value !== "string" || value.length === 0 || value.length % 4 !== 0) fail(`${name} is not base64`);
  const decoded = Buffer.from(value, "base64");
  if (decoded.toString("base64") !== value) fail(`${name} is not canonical base64`);
  return decoded;
}
function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map(key => `${JSON.stringify(key)}:${canonical(record[key])}`).join(",")}}`;
}
function validateNumbers(value: unknown, path = "$"): void {
  if (typeof value === "number" && (!Number.isSafeInteger(value))) fail(`non-interoperable number at ${path}`);
  if (Array.isArray(value)) value.forEach((item, index) => validateNumbers(item, `${path}[${index}]`));
  else if (value !== null && typeof value === "object") {
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) validateNumbers(item, `${path}.${key}`);
  }
}
export function pae(payloadType: string, payload: Buffer): Buffer {
  const type = Buffer.from(payloadType, "utf8");
  return Buffer.concat([Buffer.from(`DSSEv1 ${type.length} `), type, Buffer.from(` ${payload.length} `), payload]);
}

export function verifyEnvelope(envelopeValue: unknown, trustValue: unknown, now = new Date()): Record<string, unknown> {
  const envelope = object(envelopeValue, "envelope");
  exactKeys(envelope, ["payloadType", "payload", "signatures"], "envelope");
  if (envelope.payloadType !== PAYLOAD_TYPE) fail("unexpected payload type");
  if (!Array.isArray(envelope.signatures) || envelope.signatures.length !== 1) fail("exactly one signature is required");
  const signature = object(envelope.signatures[0], "signature");
  exactKeys(signature, ["keyid", "sig"], "signature");
  const trust = object(trustValue, "trust bundle");
  if (!Array.isArray(trust.keys)) fail("trust bundle keys are missing");
  const matches = trust.keys.map((key) => object(key, "key")).filter((key) => key.keyid === signature.keyid);
  if (matches.length !== 1) fail("key is not uniquely pinned");
  const key = matches[0];
  if (key.algorithm !== "Ed25519" || key.role !== "packet_issuer") fail("key algorithm or role is unauthorized");
  if (key.status !== "active" || key.revoked_at !== null) fail("key is disabled or revoked");
  if (typeof key.not_before !== "string" || typeof key.not_after !== "string") fail("key validity is missing");
  if (!key.not_before.endsWith("Z") || !key.not_after.endsWith("Z")) fail("key validity must use UTC RFC3339");
  const notBefore = new Date(key.not_before);
  const notAfter = new Date(key.not_after);
  if (Number.isNaN(notBefore.valueOf()) || Number.isNaN(notAfter.valueOf())) fail("key validity is invalid");
  if (now < notBefore || now > notAfter) fail("key is outside its validity window");
  const payload = decodeBase64(envelope.payload, "payload");
  const rawKey = decodeBase64(key.public_key_base64, "public key");
  if (rawKey.length !== 32) fail("Ed25519 public key must be 32 bytes");
  const spki = Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), rawKey]);
  const publicKey = createPublicKey({key: spki, format: "der", type: "spki"});
  if (!verifySignature(null, pae(PAYLOAD_TYPE, payload), publicKey, decodeBase64(signature.sig, "signature"))) fail("signature verification failed");
  let packet: unknown;
  try { packet = JSON.parse(payload.toString("utf8")); } catch { fail("payload is not JSON"); }
  if (canonical(packet) !== payload.toString("utf8")) fail("payload is not canonical JSON");
  validateNumbers(packet);
  const packetObject = object(packet, "packet");
  if ("packet_hash" in packetObject) {
    if (typeof packetObject.packet_hash !== "string") fail("packet_hash must be a string");
    const unsigned = {...packetObject};
    const claimed = unsigned.packet_hash;
    delete unsigned.packet_hash;
    const actual = `sha256:${createHash("sha256").update(canonical(unsigned), "utf8").digest("hex")}`;
    if (claimed !== actual) fail("packet_hash does not bind the canonical packet");
  }
  return packetObject;
}

if (process.argv[1]?.endsWith("verifier.ts")) {
  if (process.argv.length !== 4) fail("usage: node verifier.ts ENVELOPE TRUST_BUNDLE");
  const envelope = JSON.parse(readFileSync(process.argv[2], "utf8"));
  const trust = JSON.parse(readFileSync(process.argv[3], "utf8"));
  verifyEnvelope(envelope, trust, new Date("2027-01-01T00:00:00Z"));
  process.stdout.write("DSSE verification passed\n");
}
