/**
 * Browser-side BN254 (alt_bn128) G1 arithmetic and the AUTHENTIQ Schnorr proof.
 *
 * This mirrors the server implementation in `backend/app/zkp/sigma.py` and
 * `backend/app/zkp/curve.py` byte for byte, so proofs generated entirely in
 * the browser verify against the Python verifier.
 */

export const SIGMA_SCHEME = "AUTHENTIQ-SCHNORR-BN254-G1-V1";
const PUBLIC_SIGNAL_SCHEME = "AUTHENTIQ-PUBLIC-SIGNALS-V1";
const BASE_FIELD_PRIME = 21888242871839275222246405745257275088696311157297823662689037894645226208583n;
const SCALAR_FIELD_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const CURVE_B = 3n;
const PEDERSEN_H_LABEL = "AUTHENTIQ-PEDERSEN-H-V1";

type Point = [bigint, bigint] | null;

export interface VerificationKey {
  opening: bigint;
  blinding: bigint;
}

export interface SchnorrProof {
  scheme: string;
  commitment: string;
  anchor: string;
  challenge: string;
  response: [string, string];
  public_signals: {
    scheme: string;
    fingerprint: string;
    registration_id: string;
    commitment: string;
    challenge_nonce: string;
  };
}

const GENERATOR: Point = [1n, 2n];

function mod(value: bigint, modulus: bigint): bigint {
  const result = value % modulus;
  return result >= 0n ? result : result + modulus;
}

function modPow(base: bigint, exponent: bigint, modulus: bigint): bigint {
  let result = 1n;
  let factor = mod(base, modulus);
  let power = exponent;
  while (power > 0n) {
    if (power & 1n) result = (result * factor) % modulus;
    factor = (factor * factor) % modulus;
    power >>= 1n;
  }
  return result;
}

function inverse(value: bigint): bigint {
  return modPow(mod(value, BASE_FIELD_PRIME), BASE_FIELD_PRIME - 2n, BASE_FIELD_PRIME);
}

function pointAdd(left: Point, right: Point): Point {
  if (left === null) return right;
  if (right === null) return left;
  const [x1, y1] = left;
  const [x2, y2] = right;
  if (x1 === x2 && mod(y1 + y2, BASE_FIELD_PRIME) === 0n) return null;
  let slope: bigint;
  if (x1 === x2 && y1 === y2) {
    slope = mod(3n * x1 * x1 * inverse(2n * y1), BASE_FIELD_PRIME);
  } else {
    slope = mod((y2 - y1) * inverse(x2 - x1), BASE_FIELD_PRIME);
  }
  const x3 = mod(slope * slope - x1 - x2, BASE_FIELD_PRIME);
  const y3 = mod(slope * (x1 - x3) - y1, BASE_FIELD_PRIME);
  return [x3, y3];
}

function scalarMul(scalar: bigint, point: Point): Point {
  let k = mod(scalar, SCALAR_FIELD_PRIME);
  let result: Point = null;
  let addend = point;
  while (k > 0n) {
    if (k & 1n) result = pointAdd(result, addend);
    addend = pointAdd(addend, addend);
    k >>= 1n;
  }
  return result;
}

function pad64(value: bigint): string {
  return value.toString(16).padStart(64, "0");
}

export function pointToHex(point: Point): string {
  if (point === null) return `0x${"0".repeat(128)}`;
  return `0x${pad64(point[0])}${pad64(point[1])}`;
}

export function pointFromHex(value: string): Point {
  const raw = value.startsWith("0x") ? value.slice(2) : value;
  if (raw.length !== 128) throw new Error("Point encoding must contain 128 hex characters");
  const x = BigInt(`0x${raw.slice(0, 64)}`);
  const y = BigInt(`0x${raw.slice(64)}`);
  if (x >= BASE_FIELD_PRIME || y >= BASE_FIELD_PRIME) throw new Error("Point is outside the BN254 base field");
  const lhs = mod(y * y, BASE_FIELD_PRIME);
  const rhs = mod(x * x * x + CURVE_B, BASE_FIELD_PRIME);
  if (lhs !== rhs) throw new Error("Point is not on the BN254 curve");
  return [x, y];
}

async function sha256Bytes(input: Uint8Array): Promise<Uint8Array> {
  const buffer = input.buffer.slice(input.byteOffset, input.byteOffset + input.byteLength) as ArrayBuffer;
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return new Uint8Array(digest);
}

async function sha256BigInt(text: string): Promise<bigint> {
  const digest = await sha256Bytes(new TextEncoder().encode(text));
  return BigInt(`0x${Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("")}`);
}

let cachedH: Point = null;

async function pedersenH(): Promise<Point> {
  if (cachedH) return cachedH;
  for (let counter = 0; counter < 1000; counter += 1) {
    const digest = await sha256Bytes(new TextEncoder().encode(`${PEDERSEN_H_LABEL}:${counter}`));
    const x = mod(
      BigInt(`0x${Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("")}`),
      BASE_FIELD_PRIME,
    );
    const rhs = mod(x * x * x + CURVE_B, BASE_FIELD_PRIME);
    const y = modPow(rhs, (BASE_FIELD_PRIME + 1n) / 4n, BASE_FIELD_PRIME);
    if (mod(y * y, BASE_FIELD_PRIME) === rhs && !(x === GENERATOR![0] && y === GENERATOR![1])) {
      cachedH = [x, y];
      return cachedH;
    }
  }
  throw new Error("Could not derive the Pedersen generator");
}

function randomScalar(): bigint {
  const raw = new Uint8Array(64);
  crypto.getRandomValues(raw);
  const value =
    BigInt(`0x${Array.from(raw, (byte) => byte.toString(16).padStart(2, "0")).join("")}`) %
    (SCALAR_FIELD_PRIME - 1n);
  return value + 1n;
}

export function parseVerificationKey(input: string): VerificationKey | null {
  const match = /^aqv1_([0-9a-f]{64})_([0-9a-f]{64})$/i.exec(input.trim());
  if (!match) return null;
  const opening = BigInt(`0x${match[1]}`);
  const blinding = BigInt(`0x${match[2]}`);
  if (opening <= 0n || opening >= SCALAR_FIELD_PRIME) return null;
  if (blinding <= 0n || blinding >= SCALAR_FIELD_PRIME) return null;
  return { opening, blinding };
}

export async function generateSchnorrProof(params: {
  key: VerificationKey;
  fingerprint: string;
  registrationId: string;
  nonce: string;
  commitment: string;
}): Promise<SchnorrProof> {
  const fingerprint = params.fingerprint.toLowerCase();
  const commitmentPoint = pointFromHex(params.commitment);
  const h = await pedersenH();
  const u1 = randomScalar();
  const u2 = randomScalar();
  const anchor = pointAdd(scalarMul(u1, GENERATOR), scalarMul(u2, h));
  const challenge = mod(
    await sha256BigInt(
      [
        SIGMA_SCHEME,
        pointToHex(anchor),
        pointToHex(commitmentPoint),
        fingerprint,
        params.registrationId,
        params.nonce,
      ].join("|"),
    ),
    SCALAR_FIELD_PRIME,
  );
  const z1 = mod(u1 + challenge * params.key.opening, SCALAR_FIELD_PRIME);
  const z2 = mod(u2 + challenge * params.key.blinding, SCALAR_FIELD_PRIME);
  return {
    scheme: SIGMA_SCHEME,
    commitment: pointToHex(commitmentPoint),
    anchor: pointToHex(anchor),
    challenge: `0x${pad64(challenge)}`,
    response: [pad64(z1), pad64(z2)],
    public_signals: {
      scheme: PUBLIC_SIGNAL_SCHEME,
      fingerprint,
      registration_id: params.registrationId,
      commitment: params.commitment,
      challenge_nonce: params.nonce,
    },
  };
}
