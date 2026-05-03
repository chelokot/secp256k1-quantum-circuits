#![no_main]
sp1_zkvm::entrypoint!(main);

use secp256k1_zkp_attestation_lib::{run_prepared_attestation, PreparedAttestationInput};

pub fn main() {
    let input = sp1_zkvm::io::read::<PreparedAttestationInput>();
    let public_values = run_prepared_attestation(&input);
    sp1_zkvm::io::commit(&public_values);
}
