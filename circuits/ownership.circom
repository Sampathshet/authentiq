pragma circom 2.1.6;

include "../node_modules/circomlib/circuits/poseidon.circom";

template OwnershipCommitment() {
    signal input fingerprint;
    signal input secret;
    signal output commitment;

    component hasher = Poseidon(2);
    hasher.inputs[0] <== fingerprint;
    hasher.inputs[1] <== secret;
    commitment <== hasher.out;
}

component main {public [fingerprint]} = OwnershipCommitment();
