import { Atom, Binary, CircuitBoard, ClipboardList, Cpu, GitCompareArrows, KeyRound, Layers3, RotateCcw, Route, ShieldCheck, Sigma, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type LessonId =
  | 'zero'
  | 'qubit'
  | 'gates'
  | 'clifford'
  | 'logic-physical'
  | 'phase-estimation'
  | 'netlists'
  | 'ecdlp'
  | 'coordinates'
  | 'lookup-qroam'
  | 'programming'
  | 'cleanup'
  | 'modular-lowering'
  | 'owner-capacity'
  | 'resource-engine'
  | 'mini-engine'
  | 'optimization'
  | 'point-add-boundary'
  | 'contribution'
  | 'zkp-boundary'
  | 'repo-baselines';

export type CourseLesson = {
  id: LessonId;
  module: string;
  title: string;
  icon: LucideIcon;
  intuition: string;
  whyItMatters: string;
  mentalModel: string;
  checkpoint: string;
  deepDive?: string[];
  coreIdeas?: string[];
  practicePrompt?: string;
};

export const lessons: CourseLesson[] = [
  {
    id: 'zero',
    module: 'Orientation',
    title: 'What the project is trying to prove',
    icon: Route,
    intuition:
      'The repo is trying to make one exact object exist: a reversible secp256k1 oracle whose behavior, live wires, resource count, and proof statement all refer to the same boundary.',
    whyItMatters:
      'Most wrong low-qubit results fail because two layers silently talk about different objects: a semantic point-add formula, a lookup abstraction, a liveness list, or a proof input. The course trains you to notice those layer changes.',
    mentalModel:
      'The useful mental model is a chain of lossless translations. If any link summarizes away a quantum wire, forgets cleanup, or changes the boundary cases, the final number may still look precise while no longer describing an executable circuit.',
    checkpoint: 'A result is trustworthy only when semantics, liveness, resource owners, and proof inputs all bind the same circuit boundary.',
    deepDive: [
      'A classical program can often hide temporary storage behind a compiler. A quantum circuit cannot: every coherent temporary value remains physically present until it is uncomputed, measured under an allowed rule, or declared as part of the output. That is why this repo is mostly about boundaries, not formulas.',
      'The attack idea is high level: use phase estimation around many controlled elliptic-curve additions. The hard part is proving that the repeated point-add leaf, lookup data, modular arithmetic, owner capacities, and ZKP public values are all describing the same repeated operation.',
    ],
    coreIdeas: [
      'Semantic correctness is about the mathematical map.',
      'Resource correctness is about every live wire at every row.',
      'Publication correctness is about the exact artifact and proof input being current.',
    ],
    practicePrompt: 'Use the learning path map below first. Then open the attack map and ask which layer would catch a hidden lookup-output wire.',
  },
  {
    id: 'qubit',
    module: 'Quantum substrate',
    title: 'Qubits as vectors you can steer',
    icon: Atom,
    intuition:
      'A qubit is not a fuzzy bit. It is a two-amplitude state whose direction can be rotated, entangled with other wires, and made to interfere before one classical answer is sampled.',
    whyItMatters:
      'This project counts coherent information, not variables in source code. A 256-bit field value is 256 quantum wires whose amplitudes must stay phase-consistent while arithmetic, lookup, and cleanup happen.',
    mentalModel:
      'Think of a qubit as a tiny two-number vector with a private phase angle. A single qubit is already richer than a probability coin because phases can later add or cancel. A useful quantum computation is built by arranging those cancellations so wrong answers erase themselves and useful structure survives measurement.',
    checkpoint: 'The useful power is not “many classical worlds”; it is controlled interference before measurement.',
    deepDive: [
      'The state a|0> + b|1> has two complex amplitudes. Measurement does not reveal a and b; it samples 0 with probability |a|^2 and 1 with probability |b|^2. Gates matter because they change the amplitudes before that irreversible sampling step.',
      'The phase of one isolated amplitude is not directly visible. Relative phase becomes visible only when paths are recombined. That is the core intuition behind the Fourier parts of Shor-style algorithms: phase slopes are converted into measurement peaks.',
      'When many qubits represent a field element, they are not 256 independent UI toggles. They are one coherent register that can be in a superposition of many field values, and the circuit must transform the whole register reversibly.',
    ],
    coreIdeas: [
      'Amplitudes are not observed directly; probabilities are.',
      'Relative phase becomes information through interference.',
      'A field slot is many qubits treated as one coherent register.',
    ],
    practicePrompt: 'Use H in the Bloch playground, then run the interference program in the state-vector lab and watch a 50/50-looking intermediate state become a deterministic output.',
  },
  {
    id: 'gates',
    module: 'Quantum substrate',
    title: 'Gates, wires, controls, and reversibility',
    icon: CircuitBoard,
    intuition:
      'A quantum circuit is a time-ordered netlist of gates over named wires. Most useful arithmetic has to be reversible or explicitly uncomputed.',
    whyItMatters:
      'A temporary wire that is computed and not cleaned remains entangled garbage. It still counts and can break the algorithm.',
    mentalModel:
      'Reversible computing is a workshop where every jig you build must either become part of the output or be disassembled using the same evidence that built it.',
    checkpoint: 'A “scratch” bit is not free. It is a quantum wire with lifetime, owner, and cleanup obligations.',
  },
  {
    id: 'clifford',
    module: 'Cost model',
    title: 'Clifford vs non-Clifford',
    icon: Sparkles,
    intuition:
      'Clifford gates are the easy stabilizer backbone. Non-Clifford gates, especially Toffoli-like resources in this repo, are the expensive magic-state fuel.',
    whyItMatters:
      'The project optimizes two scarce resources at once: logical qubits for peak live state and non-Clifford count for expensive fault-tolerant work.',
    mentalModel:
      'Clifford gates are cheap rails. Non-Clifford gates are scarce switches that let the train leave the stabilizer railway.',
    checkpoint: 'A low-qubit circuit can be bad if it explodes non-Clifford count, and a low-gate circuit can be bad if it needs too many live qubits.',
  },
  {
    id: 'logic-physical',
    module: 'Fault tolerance',
    title: 'Logical qubits are not physical qubits',
    icon: ShieldCheck,
    intuition:
      'A logical qubit is an encoded, error-corrected information unit. A physical qubit is a hardware carrier used to protect it.',
    whyItMatters:
      'This repo’s numbers are logical-resource counts. They are not a hardware layout, wall-clock runtime, or physical-qubit bill.',
    mentalModel:
      'A logical qubit is a reliable database record. Physical qubits are the replication, checksums, and recovery machinery beneath it.',
    checkpoint: 'Logical counts let us compare algorithms; hardware execution needs an additional error-correction and architecture model.',
  },
  {
    id: 'phase-estimation',
    module: 'Attack algorithm',
    title: 'Phase estimation turns rhythm into bits',
    icon: Sigma,
    intuition:
      'Shor-style attacks use quantum phase estimation to convert a hidden periodic structure into a measurable binary estimate.',
    whyItMatters:
      'The secp256k1 circuit is expensive because phase estimation asks for many controlled group operations, and each one expands into point-add arithmetic.',
    mentalModel:
      'Imagine many clock hands rotating by the same secret rhythm. The inverse QFT is the lens that makes the hands agree on a binary label.',
    checkpoint: 'The curve arithmetic is the engine; phase estimation is the measuring instrument wrapped around it.',
  },
  {
    id: 'netlists',
    module: 'Compiler reality',
    title: 'Primitive netlists and liveness',
    icon: Binary,
    intuition:
      'A flat primitive netlist is the boring object that makes claims real: gate rows, wire operands, owners, intervals, and peak live count.',
    whyItMatters:
      'Every bug we found was a mismatch between an attractive boundary and the wires a real primitive circuit would have to keep alive.',
    mentalModel:
      'A netlist is an electrical city map. Liveness is rush-hour traffic. The qubit count is the maximum number of roads occupied at once.',
    checkpoint: 'The best future engine is one source of truth that executes, counts, tests, and feeds proof inputs.',
  },
  {
    id: 'ecdlp',
    module: 'Attack algorithm',
    title: 'Why secp256k1 is the target',
    icon: KeyRound,
    intuition:
      'Bitcoin public keys expose elliptic-curve points. Shor-style period finding can turn the discrete-log problem into quantum phase estimation over group operations.',
    whyItMatters:
      'The expensive repeated operation is controlled elliptic-curve point addition over secp256k1. The repo is mostly about making that operation cheaper and auditable.',
    mentalModel:
      'The quantum computer asks the curve many structured “what if I add this point?” questions in superposition, then phase estimation extracts the hidden rhythm.',
    checkpoint: 'The project is a circuit-engineering problem around a repeated secp256k1 point-add leaf, not a generic black-box quantum threat claim.',
  },
  {
    id: 'coordinates',
    module: 'Elliptic curve layer',
    title: 'Affine, projective, infinity, and slots',
    icon: Sigma,
    intuition:
      'Affine points are compact but division-heavy. Projective coordinates trade extra registers for multiplication-friendly formulas and explicit infinity cases.',
    whyItMatters:
      'The repo’s slot fights are about how many field-sized live registers are needed while computing a point-add boundary.',
    mentalModel:
      'Affine is a precise street address. Projective is a family of equivalent addresses that avoids expensive division until you really need it.',
    checkpoint: 'A field slot is one field-sized quantum register, 256 wires for secp256k1, and it must have a counted owner.',
  },
  {
    id: 'lookup-qroam',
    module: 'Lookup systems',
    title: 'QROAM is table lookup under quantum accounting',
    icon: Binary,
    intuition:
      'The circuit repeatedly selects precomputed curve-point data. A standard QROAM model pays for table selection with explicit controls, target bits, and cleanup.',
    whyItMatters:
      'Several earlier low-qubit stories failed because a lookup output lane or QROAM junk register was treated as if it were not live.',
    mentalModel:
      'QROAM is a warehouse robot: it can fetch one box by address, but the address decoder, target shelf, and cleanup route all occupy space.',
    checkpoint: 'A lookup output is only free if the executable liveness artifact proves it aliases already-counted capacity.',
  },
  {
    id: 'programming',
    module: 'Practice',
    title: 'Program tiny circuits before trusting giant ones',
    icon: CircuitBoard,
    intuition:
      'The right learning loop is to write tiny reversible circuits, inspect their wires, and watch how cleanup changes the resource story.',
    whyItMatters:
      'Once you can see why a three-wire toy leaves garbage, you can spot the same class of bug in a million-row arithmetic lowering.',
    mentalModel:
      'Every quantum program is a contract between state transformation and cleanup. The debugger is liveness.',
    checkpoint: 'A useful contributor can translate an attractive algebraic trick into a reversible wire-level contract.',
  },
  {
    id: 'cleanup',
    module: 'Practice',
    title: 'Cleanup is the difference between scratch and garbage',
    icon: RotateCcw,
    intuition:
      'Quantum temporary values are allowed only if the circuit later erases them reversibly or counts them as live output state.',
    whyItMatters:
      'The modular accumulator work in this repo is largely about proving that partial-product scratch can be consumed and uncomputed without hidden garbage.',
    mentalModel:
      'Compute is walking into a maze while laying string. Uncompute is following the same string back so the maze has no trace of you.',
    checkpoint: 'A cleanup proof must identify the source controls, target, inverse operation, and liveness interval.',
  },
  {
    id: 'modular-lowering',
    module: 'Arithmetic lowering',
    title: 'Modular multiplication is a grid plus a cleanup story',
    icon: Binary,
    intuition:
      'A field multiplication is a grid of bit products, carry/fold obligations, and cleanup. The algebraic formula is tiny; the wire story is not.',
    whyItMatters:
      'The current physical-baseline blocker lives here: modular accumulator consume/fold/source-uncompute rows must become one promoted primitive stream.',
    mentalModel:
      'Multiplication is not one operation. It is a factory line: partial products, columns, carries, reductions, and cleanup receipts.',
    checkpoint: 'A lowering is convincing only when every temporary bit has a route, owner, and inverse or measured cleanup.',
  },
  {
    id: 'owner-capacity',
    module: 'Repo engine',
    title: 'Owner capacity turns intuition into an audit',
    icon: Cpu,
    intuition:
      'Naming an owner is not enough. The owner must have enough logical-qubit capacity for every concurrently live wire assigned to it.',
    whyItMatters:
      'This is the exact class of error behind “free lookup lane” and “one-bit guard” mistakes.',
    mentalModel:
      'An owner is a parking garage. A wire assignment is a car. The audit fails when rush hour has more cars than spaces.',
    checkpoint: 'Every wire group needs exactly one owner, and every owner capacity must cover peak assigned live width.',
  },
  {
    id: 'resource-engine',
    module: 'Repo engine',
    title: 'The resource engine and why trust was not enough',
    icon: Cpu,
    intuition:
      'The engine should derive resource counts from executable primitive streams, not from manually selected register lists or formulas.',
    whyItMatters:
      'The strict baseline work exists because plausible “borrowed” wires and lookup lanes repeatedly hid real capacity requirements.',
    mentalModel:
      'A good engine is a typechecker for quantum accounting: every wire must have exactly one owner and every owner must have enough capacity.',
    checkpoint: 'If a number is not generated from executable liveness, it is a hypothesis until proven otherwise.',
  },
  {
    id: 'mini-engine',
    module: 'Repo engine',
    title: 'Derive peak qubits from liveness, not vibes',
    icon: Cpu,
    intuition:
      'A resource engine scans primitive rows, derives live intervals, assigns each live wire to one owner, then takes the maximum concurrent width.',
    whyItMatters:
      'This is the mechanical habit needed to attack the repo constructively: every proposed optimization must survive the same liveness derivation.',
    mentalModel:
      'Imagine a tiny garbage-collected runtime where values have birth rows, death rows, owners, and heap capacities. The qubit count is max heap pressure.',
    checkpoint: 'To improve a circuit, you need to move births earlier/later, shorten deaths with cleanup, or give owners enough counted capacity.',
  },
  {
    id: 'optimization',
    module: 'Repo engine',
    title: 'Optimization is a constrained search, not a wish',
    icon: Sigma,
    intuition:
      'The project is searching inside a hard box: lower qubits, keep non-Clifford under budget, preserve semantics, and promote the result into an executable contract.',
    whyItMatters:
      'A numeric row can look brilliant while failing because it is not executable, misses gate budget, or hides lookup workspace. Real improvements pass every axis.',
    mentalModel:
      'Think of each candidate as a point in a resource landscape. A breakthrough is not the closest point to the target; it is a path that also has a bridge to executable proof.',
    checkpoint: 'A useful optimization proposal must say which constraint it relaxes, which cost it pays, and how it will be promoted into the engine.',
  },
  {
    id: 'point-add-boundary',
    module: 'Repo engine',
    title: 'Point-add edge cases are part of the contract',
    icon: GitCompareArrows,
    intuition:
      'A point-add leaf is not proven by ordinary random additions alone. Doubling, inverse pairs, accumulator infinity, and lookup infinity are separate semantic boundaries.',
    whyItMatters:
      'Earlier attractive schedules looked plausible on the hot path while failing exact point-add boundaries. The counted family has to execute the same edge-case contract it claims.',
    mentalModel:
      'The point-add leaf is an API with branch tests, not a single formula. Random tests knock on the front door; edge cases check every emergency exit.',
    checkpoint: 'A reviewer should reject a lower-qubit point-add result until every boundary family passes against the counted executable interface.',
  },
  {
    id: 'contribution',
    module: 'Practice',
    title: 'Turn understanding into a useful patch',
    icon: ClipboardList,
    intuition:
      'A useful contribution is a small claim with the right evidence: source artifact, semantic boundary, owner capacity, liveness recomputation, and publication hygiene.',
    whyItMatters:
      'This repo has repeatedly shown that impressive-looking numbers are easy to invent and hard to prove. Contributor skill is knowing which proof habit closes which class of bug.',
    mentalModel:
      'Treat every patch as a mission packet: what object changes, what evidence is new, which blocker it closes, and which claim level is now justified.',
    checkpoint: 'Before proposing an optimization, state the mission, the required evidence, and the exact claim status after the patch.',
  },
  {
    id: 'zkp-boundary',
    module: 'Repo engine',
    title: 'ZKP proves a statement, not every unstated assumption',
    icon: ShieldCheck,
    intuition:
      'A compressed or Groth16 proof can be valid while proving an old input, a smoke corpus, or a macro-boundary statement that is weaker than a physical-circuit claim.',
    whyItMatters:
      'The repo now separates proof freshness, public values, release corpus size, and physical-baseline readiness so a green verifier cannot hide a stale or weaker contract.',
    mentalModel:
      'A ZKP is a notarized receipt. It is powerful only after you inspect exactly what was purchased, which input hash it binds, and whether that item is the thing you wanted.',
    checkpoint: 'A reviewer should ask: what input, what corpus, what public values, what resource digest, and what remaining macro boundary?',
  },
  {
    id: 'repo-baselines',
    module: 'This repo now',
    title: 'Current candidates, blockers, and what to improve',
    icon: Layers3,
    intuition:
      'The current repo state is honest but not finished: it has a strict candidate, a guard-corrected consequence, and explicit blockers before accepting a physical baseline.',
    whyItMatters:
      'This is the right learning target: understand enough to close blockers or find optimizations without inventing uncounted wires.',
    mentalModel:
      'Treat every resource result as a contract with a status: accepted, candidate, consequence, rejected, or hypothesis.',
    checkpoint: 'The next useful work is not more hype; it is converting remaining macro boundaries into executable primitive evidence.',
  },
];

export const glossary = [
  ['Qubit', 'A coherent two-state quantum system used as one wire in a circuit.'],
  ['Amplitude', 'A complex state-vector component whose squared magnitude gives a measurement probability.'],
  ['Entanglement', 'A joint quantum state that cannot be decomposed into independent per-qubit states.'],
  ['Logical qubit', 'An error-corrected qubit abstraction counted by this repo.'],
  ['Physical qubit', 'A hardware qubit used by an error-correcting implementation.'],
  ['Repetition code', 'A simple error-correction intuition model where several physical carriers vote for one encoded value.'],
  ['Code distance', 'A fault-tolerance knob that increases physical overhead to suppress logical errors.'],
  ['Logical failure', 'The probability that enough physical errors occur to defeat the decoder for one encoded logical value.'],
  ['Clifford', 'Cheap stabilizer-preserving gate family in many fault-tolerant models.'],
  ['Stabilizer state', 'A state that Clifford operations can move and track inside a discrete, efficiently simulable frame.'],
  ['Non-Clifford', 'Expensive gates/resources needed for universal quantum computation.'],
  ['Magic state', 'A costly fault-tolerant resource that can supply non-Clifford operations.'],
  ['T gate', 'A single-qubit non-Clifford step that moves between Clifford stabilizer axes in the toy wheel.'],
  ['Netlist', 'A concrete list of primitive gate rows and wire operands.'],
  ['Opcode lowering', 'The expansion of one abstract operation into primitive gate rows with concrete operands and costs.'],
  ['Primitive row', 'One executable gate-level row that a resource engine can count and bind to live wires.'],
  ['Liveness', 'The interval during which a wire value must remain available.'],
  ['Schedule', 'The ordered placement of compute, consume, cleanup, and output rows that determines live overlap.'],
  ['Circuit stack', 'The chain from algorithm shell to lookup, point-add, arithmetic lowering, primitive netlist, resource count, and proof boundary.'],
  ['Window scaffold', 'The phase-register schedule that groups control bits into fixed-size windows, with each retained window becoming a point-add leaf.'],
  ['Field slot', 'A 256-wire secp256k1 field-sized quantum register.'],
  ['QROAM', 'A quantum read-only memory tradeoff for selecting table data.'],
  ['Phase estimation', 'A quantum routine that extracts a hidden eigenphase or period into classical bits.'],
  ['Fourier transform', 'A change of basis that turns evenly rotating phase slopes into sharp frequency labels.'],
  ['Destructive interference', 'Amplitude cancellation caused by arrows pointing in different directions before measurement.'],
  ['Discrete logarithm', 'The hidden scalar d in Q = dG, where G and Q are known group elements.'],
  ['Oracle', 'A reversible black-box-style operation the quantum algorithm queries in superposition.'],
  ['Whole-oracle composition', 'The resource reconstruction that combines the phase shell, direct seed, point-add leaves, lookup work, arithmetic work, and peak workspace into one checked oracle row.'],
  ['Peak workspace', 'The live logical-qubit surface reused across repeated calls; unlike gate count, it is not multiplied by the number of sequential leaves.'],
  ['Hidden period', 'A repeated relation in the oracle outputs, such as shifting (a,b) without changing aG + bQ.'],
  ['Phase kickback', 'A pattern where a computed oracle value is returned to zero while its phase imprint remains on the input register.'],
  ['Fourier label', 'A frequency-state label that converts an oracle output value into a phase slope over the queried inputs.'],
  ['Affine point', 'An elliptic-curve point represented directly as x and y coordinates.'],
  ['Projective point', 'An equivalent point representation using extra scale coordinates to avoid division.'],
  ['Coordinate normalization', 'The step that converts a projective representative back into direct affine coordinates.'],
  ['Reversible overwrite', 'An in-place update that is a permutation of the old quantum state, not destructive assignment.'],
  ['Permutation contract', 'Evidence that an in-place transform is injective on the executable boundary, so it can be implemented reversibly.'],
  ['Uncompute', 'Running the dependency path backward to clean temporary quantum state.'],
  ['Temporary AND', 'A scratch target produced by an AND/CCX-style row that must be consumed and then cleaned or counted as live garbage.'],
  ['Source-uncompute', 'Cleanup that replays the same source controls that computed a temporary value so the target returns to zero.'],
  ['Consume row', 'A row that uses a temporary value to update the counted destination before cleanup is allowed.'],
  ['Abandoned garbage', 'A computed quantum temporary left without an output role, owner capacity, or reversible cleanup route.'],
  ['Owner', 'A counted resource bucket responsible for a live wire group.'],
  ['Capacity', 'The logical-qubit budget an owner proves it can hold at peak liveness.'],
  ['Live interval', 'The row range over which a quantum value must remain coherent and counted.'],
  ['Peak live qubits', 'The maximum sum of all concurrently live quantum wire widths.'],
  ['Tradeoff', 'A resource exchange where improving one axis such as qubits can worsen another such as non-Clifford count.'],
  ['Baseline', 'A comparison resource row whose status must be read before using it as evidence.'],
  ['Pareto frontier', 'A tradeoff boundary where improving one resource axis requires worsening another or changing the construction.'],
  ['Promoted candidate', 'A candidate whose semantics, primitive lowering, owner capacity, and resource totals are all part of the accepted engine path.'],
  ['Claim classification', 'The reviewer habit of labeling a result as accepted, candidate, consequence, reference, hypothesis, or rejected before repeating it.'],
  ['Mission packet', 'A contribution framed as a target outcome plus the evidence required to make that outcome true.'],
  ['Artifact atlas', 'A map from checked repo paths to the audit questions they can answer and the claims they cannot prove alone.'],
  ['Confidence ladder', 'The ordered reviewer workflow from idea, to semantic boundary, to primitive stream, to owner capacity, to fresh proof, to accepted baseline.'],
  ['Learning path', 'The staged route through prerequisites that turns isolated labs into contributor-ready understanding.'],
  ['Contributor readiness', 'A course status meaning the required mental models for useful repo patches have been completed.'],
  ['Partial product', 'A bit-level AND contribution inside schoolbook multiplication.'],
  ['Fold', 'A modular-reduction route that moves high product columns back into field range.'],
  ['Accumulator', 'A running register or column structure that receives many partial contributions before reduction.'],
  ['Carry-save', 'A compression strategy that reduces tall bit columns without immediately propagating every carry.'],
  ['Zero-lift guard', 'A predicate guard for an in-place tail overwrite edge case.'],
  ['Point-add boundary', 'The full set of ordinary and edge-case point-add behaviors that the counted leaf must execute.'],
  ['Lookup infinity', 'A lookup table identity entry that should leave the accumulator unchanged.'],
  ['ZKP', 'A proof that a specific statement/input relation was satisfied without exposing every witness detail.'],
  ['Groth16', 'A succinct proof wrapper; useful only after its verifier key, public values, and input binding are current.'],
  ['Public values', 'The explicit values a verifier sees and checks against the proof statement.'],
];

export const quiz = [
  {
    prompt: 'Why is a borrowed quantum scratch wire suspicious?',
    answers: [
      'Because it still has a lifetime and may be live concurrently with the owner it supposedly replaces.',
      'Because all scratch wires are classical and cannot be used in quantum circuits.',
      'Because borrowed wires always add non-Clifford gates.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What would make a qubit headline much stronger?',
    answers: [
      'A prettier formula in the README.',
      'A flat primitive netlist whose liveness produces the same number that tests and proof inputs consume.',
      'A lower number copied from a modeled hypothesis document.',
    ],
    correctIndex: 1,
  },
  {
    prompt: 'What is the current accepted Clifford-complete physical baseline in this repo?',
    answers: ['1,968 logical qubits.', '2,222 logical qubits.', 'None yet.'],
    correctIndex: 2,
  },
  {
    prompt: 'Why does QROAM matter for this project?',
    answers: [
      'It is the only part of the circuit that runs on classical hardware.',
      'It selects precomputed lookup data, and its target/junk/workspace wires must be counted.',
      'It removes the need for elliptic-curve point addition.',
    ],
    correctIndex: 1,
  },
  {
    prompt: 'What does inverse QFT do in the Shor-style story?',
    answers: [
      'It turns phase/rhythm information into a computational-basis measurement peak.',
      'It reduces physical qubits to logical qubits.',
      'It proves a Groth16 proof.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why does the inverse QFT produce a sharp label for a clean phase slope?',
    answers: [
      'The correct label aligns all phase arrows, while wrong labels make arrows cancel by destructive interference.',
      'It measures every possible label and keeps the smallest one.',
      'It replaces controlled group operations with classical sorting.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why does the ECDLP oracle use two scalar registers a and b?',
    answers: [
      'Because aG + bQ = (a + b*d)G hides d as a collision/period relation across pairs.',
      'Because secp256k1 points have exactly two physical qubits.',
      'Because Groth16 requires two public inputs for every proof.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What does phase kickback do for the toy ECDLP oracle?',
    answers: [
      'It turns f(a,b) into a phase slope over the input lattice while the output register can be uncomputed.',
      'It measures the secret d directly before running any group operation.',
      'It replaces QROAM lookup workspace with a classical cache.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'When is a temporary quantum value safe?',
    answers: [
      'When it is small enough to ignore.',
      'When it is either part of the intended output or reversibly uncomputed with counted live wires.',
      'When it appears only in a formula artifact.',
    ],
    correctIndex: 1,
  },
  {
    prompt: 'What does owner capacity prove?',
    answers: [
      'That the owner name sounds like the right subsystem.',
      'That assigned live wire width fits inside the owner logical-qubit budget.',
      'That non-Clifford cost is always lower.',
    ],
    correctIndex: 1,
  },
  {
    prompt: 'What does a valid Groth16 proof not prove by itself?',
    answers: [
      'That the exact current physical baseline contract has no remaining macro boundary.',
      'That one committed statement verified under one verifier key.',
      'That public values were part of the checked proof statement.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why is the modular accumulator still a blocker?',
    answers: [
      'Because row obligations and carry-save candidates still need promotion into one counted primitive stream.',
      'Because modular multiplication is not used in elliptic-curve point addition.',
      'Because full adders have no non-Clifford gates.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why does the modular accumulator scratch lifecycle need consume and cleanup rows?',
    answers: [
      'Because a temporary AND target must update counted accumulator state and then be uncomputed from the same source controls instead of being left as entangled garbage.',
      'Because every scratch target can be deleted once its name disappears from the formula.',
      'Because cleanup rows reduce non-Clifford count to zero.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What does a liveness-derived qubit count do?',
    answers: [
      'It sums every wire ever mentioned, even when lifetimes do not overlap.',
      'It takes the peak width of wires live at the same time and checks owner capacity.',
      'It ignores cleanup because cleanup only affects gate count.',
    ],
    correctIndex: 1,
  },
  {
    prompt: 'What does opcode lowering add to an abstract circuit operation?',
    answers: [
      'Primitive rows with concrete operands, owners, cleanup obligations, and countable gate cost.',
      'A prettier high-level name for the same formula.',
      'A way to skip liveness because the source opcode was already tested.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why can a numerically attractive optimization still be blocked?',
    answers: [
      'Because it may lack an executable contract or may pay too much on another resource axis.',
      'Because lower qubit count is never useful.',
      'Because non-Clifford gates are free in fault-tolerant circuits.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why are random point-add tests insufficient for this repo?',
    answers: [
      'Because edge cases such as doubling, inverse pairs, and infinity branches can fail while random ordinary additions pass.',
      'Because random tests always use classical bits and cannot check any quantum circuit.',
      'Because point-add is not part of the secp256k1 attack.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What does the two-qubit state-vector lab make visible?',
    answers: [
      'How gate code changes amplitudes and measurement probabilities before any resource counting.',
      'How to replace logical qubits with physical qubits one-to-one.',
      'How Groth16 verifies elliptic-curve point addition without inputs.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why are this repo’s logical-qubit numbers not a physical hardware bill?',
    answers: [
      'Because an additional error-correction and layout model is needed to map each logical qubit to many physical qubits.',
      'Because logical qubits are always larger than physical qubits.',
      'Because physical qubits only matter for classical table lookups.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What does the repetition-code toy lab teach?',
    answers: [
      'How multiple noisy physical carriers can encode one logical value through majority voting.',
      'That the repo logical-qubit count is already a physical-qubit count.',
      'That error correction removes the need for non-Clifford gates.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What is the projective-coordinate tradeoff?',
    answers: [
      'It uses more live field coordinates to avoid inversion-heavy affine formulas on the hot path.',
      'It removes the need to count field slots.',
      'It makes every point-add case classical.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why does the repo track non-Clifford count separately from logical qubits?',
    answers: [
      'Because non-Clifford operations consume scarce magic-state resources even when peak live qubits are unchanged.',
      'Because Clifford gates cannot appear in a quantum circuit.',
      'Because non-Clifford count is another name for physical qubits.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What does the stabilizer-vs-magic wheel show?',
    answers: [
      'Clifford steps stay on efficiently trackable stabilizer axes, while a T step moves into a magic state that must be paid for.',
      'Every rotation is free as long as it is drawn on a circle.',
      'Non-Clifford gates reduce logical-qubit count automatically.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'How can scheduling reduce peak live qubits without changing outputs?',
    answers: [
      'By moving valid cleanup earlier so temporary wire lifetimes stop overlapping later values.',
      'By deleting output wires from the count.',
      'By counting every wire ever mentioned instead of live intervals.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why is an end-to-end circuit stack map useful?',
    answers: [
      'It checks that each layer consumes the exact object emitted by the previous layer, so a resource claim does not drift away from the tested circuit.',
      'It replaces the need for edge-case tests.',
      'It proves physical qubit counts without an error-correction model.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What should a contributor do before repeating a lower resource number as a result?',
    answers: [
      'Classify the claim and check the exact evidence required for that claim level.',
      'Use the smallest number anywhere in the repo.',
      'Treat every valid proof file as an accepted physical baseline.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'How should the Google 1,200q / 90M and 1,450q / 70M rows be read?',
    answers: [
      'As two public tradeoff comparison lines, one lower-qubit and one lower-gate, not as one hidden circuit reconstructed by this repo.',
      'As accepted physical baselines generated by this repository.',
      'As proof that non-Clifford count and logical qubits always improve together.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why does whole-oracle non-Clifford count add across point-add leaves while logical qubits do not?',
    answers: [
      'Because gate work accumulates over time, but logical qubits count the peak concurrent workspace reused across calls.',
      'Because every point-add leaf creates a new permanent copy of all field slots.',
      'Because QROAM workspace is classical and disappears from qubit accounting.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What makes a circuit-improvement patch contributor-ready?',
    answers: [
      'A narrow mission, explicit evidence checklist, recomputed resources, and a clear post-patch claim status.',
      'A lower number in a comment without changing artifacts.',
      'A screenshot of a chart with no source artifact.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'Why does this course need a learning path instead of only independent labs?',
    answers: [
      'Because each later audit skill depends on earlier mental models: amplitudes, reversibility, point-add semantics, liveness, and claim status.',
      'Because independent labs cannot be tested with Playwright.',
      'Because a learning path replaces the need to inspect repo artifacts.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What is the right way to use a checked artifact path?',
    answers: [
      'Ask which audit question it answers and which claim it does not prove alone.',
      'Treat every JSON file as an accepted physical baseline.',
      'Copy the lowest number from the artifact into README without checking status.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What is the safest reviewer habit before saying “accepted baseline”?',
    answers: [
      'Climb the confidence ladder and verify every required rung is current and promoted.',
      'Check only that one semantic test file passes.',
      'Check only that a Groth16 proof file exists.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'What does a retained 16-bit window become in this attack scaffold?',
    answers: [
      'One lookup-fed point-add leaf.',
      'One physical qubit.',
      'One Groth16 verifier key.',
    ],
    correctIndex: 0,
  },
  {
    prompt: 'When is an in-place quantum overwrite allowed?',
    answers: [
      'When the update is a reversible permutation of the old value under the counted live inputs.',
      'Whenever the target wire name is no longer needed in the formula.',
      'Only when it deletes the old value with measurement.',
    ],
    correctIndex: 0,
  },
];
