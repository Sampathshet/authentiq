# AUTHENTIQ optional ownership circuit

This directory contains an optional Circom implementation of the ownership commitment relation. It is **not used by the running backend**. The production default is the real Schnorr proof implemented in `backend/app/zkp/`.

## What the circuit proves

`ownership.circom` proves:

```text
commitment = Poseidon(fingerprint mod p, secret)
```

- `fingerprint` is public.
- `secret` is private.
- `commitment` is the public output.
- `p` is the BN254 scalar field prime `21888242871839275222246405745257275088548364400416034343698204186575808495617`.

The circuit does not hash the original file. The 256-bit SHA-256 digest is reduced modulo `p` before it becomes the `fingerprint` input. An external verifier must independently compute SHA-256 over the file and confirm that the public `fingerprint` equals `SHA256(file) mod p`. This binding check is outside the circuit.

## Install and build

Requirements: Node.js 20+, Circom 2.1.6+, and Circomlib.

```powershell
cd circuits
npm install
New-Item -ItemType Directory -Force build | Out-Null
npm run build
```

The build produces `build/ownership.r1cs`, `build/ownership_js/ownership.wasm`, and `build/ownership.sym`.

## Trusted setup and proof

```powershell
cd circuits
npx snarkjs powersoftau new bn128 14 build/pot14_0000.ptau -v
npx snarkjs powersoftau contribute build/pot14_0000.ptau build/pot14_0001.ptau --name="AUTHENTIQ phase 1" -v
npx snarkjs powersoftau prepare phase2 build/pot14_0001.ptau build/pot14_final.ptau -v
npm run setup
npm run contribute
npm run export
python scripts/prepare_input.py <sha256-hex> <secret-hex>
npm run prove
npm run verify
```

This development ceremony is not a production multi-party ceremony. A real deployment must use a properly coordinated ceremony and publish its transcript.

## Backend relationship

The backend commitment is `Poseidon(SHA256(file) mod p, secret)`, which matches this circuit. The backend's default proof is a Schnorr proof over the Pedersen commitment `C = sG + rH` where `s = Poseidon(SHA256(file) mod p, secret)`. The two systems share the Poseidon commitment value but use different proof systems.

The backend settings `AUTHENTIQ_GROTH16_WASM`, `AUTHENTIQ_GROTH16_ZKEY`, and `AUTHENTIQ_GROTH16_VKEY` reserve configuration names. No Groth16 proving or verification path is currently enabled at runtime: the current release does not claim that the circuit is integrated. The default runtime proof is real; its exact scope is documented in `docs/ZKP.md`.
