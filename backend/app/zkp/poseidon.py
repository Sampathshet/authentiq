from app.zkp.poseidon_constants import POSEIDON_C, POSEIDON_M

FIELD_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617
T = 3
FULL_ROUNDS = 8
PARTIAL_ROUNDS = 57
SBOX_EXPONENT = 5


def poseidon2(left: int, right: int) -> int:
    state = [0, left % FIELD_PRIME, right % FIELD_PRIME]
    total_rounds = FULL_ROUNDS + PARTIAL_ROUNDS
    for round_index in range(total_rounds):
        offset = round_index * T
        state[0] = (state[0] + POSEIDON_C[offset]) % FIELD_PRIME
        state[1] = (state[1] + POSEIDON_C[offset + 1]) % FIELD_PRIME
        state[2] = (state[2] + POSEIDON_C[offset + 2]) % FIELD_PRIME

        if round_index < FULL_ROUNDS // 2 or round_index >= FULL_ROUNDS // 2 + PARTIAL_ROUNDS:
            state[0] = pow(state[0], SBOX_EXPONENT, FIELD_PRIME)
            state[1] = pow(state[1], SBOX_EXPONENT, FIELD_PRIME)
            state[2] = pow(state[2], SBOX_EXPONENT, FIELD_PRIME)
        else:
            state[0] = pow(state[0], SBOX_EXPONENT, FIELD_PRIME)

        mixed_0 = (
            POSEIDON_M[0][0] * state[0]
            + POSEIDON_M[0][1] * state[1]
            + POSEIDON_M[0][2] * state[2]
        ) % FIELD_PRIME
        mixed_1 = (
            POSEIDON_M[1][0] * state[0]
            + POSEIDON_M[1][1] * state[1]
            + POSEIDON_M[1][2] * state[2]
        ) % FIELD_PRIME
        mixed_2 = (
            POSEIDON_M[2][0] * state[0]
            + POSEIDON_M[2][1] * state[1]
            + POSEIDON_M[2][2] * state[2]
        ) % FIELD_PRIME
        state = [mixed_0, mixed_1, mixed_2]

    return state[0] % FIELD_PRIME
