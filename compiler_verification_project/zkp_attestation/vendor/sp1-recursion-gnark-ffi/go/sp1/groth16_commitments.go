package sp1

import (
	"github.com/consensys/gnark/constraint"
	cs_bn254 "github.com/consensys/gnark/constraint/bn254"
)

func normalizeGroth16Commitments(system constraint.ConstraintSystem) {
	if r1cs, ok := system.(*cs_bn254.R1CS); ok && r1cs.CommitmentInfo == nil {
		r1cs.CommitmentInfo = constraint.Groth16Commitments{}
	}
}
