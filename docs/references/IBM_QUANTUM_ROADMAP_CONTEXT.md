# IBM Quantum roadmap context

This note records the IBM-specific hardware-roadmap context used by the
README. It is deliberately phrased as a roadmap comparison, not as a claim that
today's IBM devices can run this repository's secp256k1 circuit.

## Public IBM roadmap facts used here

The sources below are IBM pages current at the time this note was written.
IBM's roadmap page also says that roadmap information reflects current intent
and can change.

| IBM source | Relevant public statement |
|---|---|
| [IBM Quantum Roadmap](https://www.ibm.com/roadmaps/quantum/) | 2026 Nighthawk target: circuits with 7,500 gates in up to three 120-qubit modules; 2028 Nighthawk target: 15,000 gates on up to 1,080 qubits; Starling: 200 logical qubits and 100 million gates in 2029; Blue Jay: 2,000 logical qubits and 1 billion gates in the 2033+ roadmap window. |
| [IBM Quantum 2026 roadmap page](https://www.ibm.com/roadmaps/quantum/2026/) | Nighthawk is IBM's near-term quantum-advantage platform; Loon and Kookaburra are described as stepping stones toward scalable error correction and Starling; IBM also highlights real-time error-correction decoder work. |
| [IBM Quantum hardware page](https://www.ibm.com/quantum/hardware) | Heron has 133 or 156 fixed-frequency qubits with tunable couplers; Nighthawk has 120 qubits on a square lattice; IBM describes System Two as its modular quantum-centric supercomputing platform. |
| [IBM fault-tolerant roadmap blog](https://www.ibm.com/quantum/blog/large-scale-ftqc) | IBM describes Starling as the 2029 fault-tolerant system and explains the Loon, Kookaburra, Cockatoo, magic-state, and module roadmap leading to it. |
| [IBM System Two / 2033 roadmap blog](https://www.ibm.com/quantum/blog/quantum-roadmap-2033) | IBM describes the 2029 Starling and 2033 Blue Jay logical-qubit and gate-scale targets, and the System Two modular architecture. |

## Comparison to this repository's result

The strongest direct comparison is against named fault-tolerant IBM roadmap
targets, not against today's NISQ hardware.

Using the current README headline scale of roughly one thousand logical qubits
and tens of millions of non-Clifford gates:

- Starling's 200 logical qubits are below this repository's current logical
  workspace requirement.
- Starling's 100-million-gate scale is above the current non-Clifford count,
  but this is not a complete full-gate comparison because the repository counts
  non-Clifford gates at the compiler-family boundary.
- Blue Jay's 2,000 logical qubits give space headroom for the current logical
  count.
- Blue Jay's 1-billion-gate target is comfortably above the current
  non-Clifford count as a scale comparison.

The careful conclusion is therefore:

- current IBM processors are not claimed to run this circuit;
- Starling is a meaningful gate-scale reference point but not a qubit-space
  match for this circuit as currently counted;
- Blue Jay is the first named IBM roadmap target that is naturally in the
  same logical-qubit class as this repository's secp256k1 resource estimate;
- IBM's roadmap is unusually useful for cryptographic-risk interpretation
  because it publishes logical-qubit and gate-scale milestones that can be
  compared to exact logical resource estimates.

## Why this is favorable to IBM without overstating it

Many hardware announcements emphasize physical qubit counts, which are hard to
map to fault-tolerant cryptanalytic workloads without a full error-correction
stack. IBM's roadmap is stronger for this repository's purposes because its
named long-range systems are stated directly in logical-qubit and gate-scale
terms. That lets an exact secp256k1 resource estimate be read against a named
hardware trajectory instead of against a vague physical-qubit number.

The positive but factual message is:

> IBM's post-Starling roadmap is one of the few public roadmaps precise enough
> to make a secp256k1 quantum resource estimate operationally interpretable.

## Non-claims

This repository does not claim:

- that Heron, Nighthawk, or any current IBM processor can run this attack;
- that Starling's 200 logical qubits are enough for the current circuit;
- that non-Clifford count is identical to IBM's published full-gate metric;
- that IBM's roadmap milestones are guaranteed rather than roadmap targets;
- that a physical runtime follows from this comparison without a separate
  error-correction, routing, magic-state, and scheduling model.
