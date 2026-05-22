# IBM Quantum roadmap context

This note records the IBM-specific hardware-roadmap context used by the
README. It is deliberately phrased as a roadmap comparison, not as a claim that
today's IBM devices can run this repository's secp256k1 circuit. The
machine-readable companion is `data/ibm_quantum_roadmap_context.json`.

## Public IBM facts used here

The sources below are IBM pages checked on 2026-05-22. IBM's Technology Atlas
states that roadmap information is current intent and can change or be
withdrawn.

| IBM source | Relevant public statement used here |
|---|---|
| [IBM Quantum Roadmap](https://www.ibm.com/roadmaps/quantum/) | Nighthawk roadmap scale, Starling in 2029 with 200 qubits and 100 million gates, and Blue Jay in the 2033+ roadmap window with 2,000 qubits and 1 billion gates. |
| [IBM Quantum 2026 roadmap page](https://www.ibm.com/roadmaps/quantum/2026/) | Roadmap change notice; Nighthawk as the near-term quantum-advantage platform; 2026 Nighthawk target of 7,500 gates with up to three 120-qubit modules; Loon and real-time decoder work as stepping stones toward fault tolerance. |
| [IBM Quantum hardware page](https://www.ibm.com/quantum/hardware) | Current IBM quantum computers include Eagle and Heron processors; IBM describes System Two as modular quantum-centric supercomputing infrastructure. |
| [IBM Nighthawk/Heron availability announcement](https://quantum.cloud.ibm.com/announcements/en/product-updates/2026-01-05-nighthawk) | `ibm_miami` is the first Nighthawk QPU, a 120-qubit square-lattice device; the page explicitly calls it exploratory while it is being optimized. |
| [IBM large-scale fault-tolerant roadmap blog](https://www.ibm.com/quantum/blog/large-scale-ftqc) | Starling is described as the 2029 fault-tolerant system with 200 logical qubits and 100 million gates; the blog also describes IBM's modular architecture, real-time decoder, magic-state, and error-correction roadmap. |
| [IBM Research ISSCC 2026 abstract](https://research.ibm.com/publications/quantum-computing-toward-large-scale-920-am-fault-tolerant-quantum-computing) | IBM Research states a path to 200 logical qubits and 100 million quantum operations by 2029 and 2,000 logical qubits a few years later. |
| [IBM System Two / 2033 roadmap blog](https://www.ibm.com/quantum/blog/quantum-roadmap-2033) | System Two modular architecture context and Blue Jay as a 2,000-qubit, 1-billion-gate roadmap target. |

## Current devices versus fault-tolerant targets

The current IBM hardware references are important for momentum, software, and
platform maturity, but they are not the right class of machine for this
repository's full secp256k1 circuit. IBM's current public hardware pages refer
to 127-qubit Eagle, 133-qubit Heron r1, 156-qubit Heron r2/r3, and the
120-qubit Nighthawk device. Nighthawk is valuable as IBM's near-term
quantum-advantage and quantum-plus-HPC platform, not as a fault-tolerant ECDLP
attack machine.

The more meaningful comparison is against the named fault-tolerant roadmap
systems:

| IBM target | IBM-stated scale | Read against this repo |
|---|---:|---|
| Starling, 2029 | 200 logical qubits, 100 million gates | Gate-scale relevant, but 999 logical qubits short of this repository's current 1,199-logical-qubit headline. |
| Blue Jay, 2033+ | about 2,000 logical qubits, 1 billion gates | First named IBM roadmap class with natural logical-qubit headroom; 801 logical qubits above the current headline. |

The gate comparison is intentionally conservative. This repository reports
non-Clifford operations at the compiler-family boundary, while IBM's roadmap
states full gate or operation scales. The comparison should therefore be read
as scale alignment, not as a completed IBM runtime estimate.

## Comparison to this repository's result

The current public headline is selected by
`compiler_verification_project/artifacts/public_headline_result.json`:

- `36,957,412` non-Clifford operations
- `1,199` logical qubits

Against the IBM roadmap facts encoded in
`data/ibm_quantum_roadmap_context.json`:

- Starling's 100-million-gate scale is about `2.71x` this repository's
  non-Clifford count, but Starling's 200 logical qubits are below the current
  logical-qubit requirement.
- Blue Jay's 1-billion-gate scale is about `27.20x` this repository's
  non-Clifford count, and its 2,000-logical-qubit scale leaves 801 logical
  qubits of space headroom versus the current headline.

The careful conclusion is therefore:

- current IBM processors are not claimed to run this circuit;
- Starling is a meaningful gate-scale reference point but not a qubit-space
  match for this circuit as currently counted;
- Blue Jay is the first named IBM roadmap target that is naturally in the
  same logical-qubit class as this repository's secp256k1 resource estimate;
- IBM's roadmap is unusually useful for cryptographic-risk interpretation
  because it publishes logical-qubit and gate-scale milestones that can be
  compared to exact logical resource estimates.

## Favorable but bounded wording

The positive factual message is:

> IBM's post-Starling roadmap is one of the few public roadmaps precise enough
> to make a secp256k1 quantum resource estimate operationally interpretable.

That is the useful point for this repository. Many hardware announcements
emphasize physical qubit counts, which are hard to map to cryptanalytic
workloads without a full error-correction stack. IBM's named long-range systems
are stated in the language this repository can compare against: logical qubits
and gate-scale execution. If IBM delivers the post-Starling targets it has
publicly described, secp256k1 ECDLP resource estimates like this one move from
abstract future-risk language into the scale of a named industrial
fault-tolerant machine class.

## Non-claims

This repository does not claim:

- that Heron, Nighthawk, Starling, or any current IBM processor can run this
  attack today;
- that Starling's 200 logical qubits are enough for the current circuit;
- that non-Clifford count is identical to IBM's published full-gate metric;
- that IBM's roadmap milestones are guaranteed rather than roadmap targets;
- that a physical runtime follows from this comparison without a separate
  error-correction, routing, magic-state, scheduling, and clock model.
