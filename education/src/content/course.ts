import { Atom, Binary, CircuitBoard, ClipboardList, Cpu, GitCompareArrows, KeyRound, Layers3, RotateCcw, Route, ShieldCheck, Sigma, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type LessonId =
  | 'zero'
  | 'qubit'
  | 'one-qubit'
  | 'two-qubit'
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
  glossaryTerms?: string[];
};

export const lessons: CourseLesson[] = [
  {
    id: 'zero',
    module: 'Orientation',
    title: 'What the project is trying to prove',
    icon: Route,
    intuition:
      'A quantum circuit is still a computer program in the broad sense: it stores state, applies operations, and finally reads an answer. The difference is the kind of state and the rules operations must obey.',
    whyItMatters:
      'The repo result is a resource claim about that program: how many protected quantum memory wires are live at once, and how many expensive quantum operations the circuit uses.',
    mentalModel:
      'Compare it to an ordinary computer first. Classical memory stores one discrete bit string at a time. Quantum memory stores amplitudes over many bit strings, and gates transform those amplitudes by strict reversible linear rules before measurement gives a discrete answer.',
    checkpoint: 'The repo must connect the mathematical attack, the quantum state-and-gate program, tests, and resource numbers into one auditable chain.',
    deepDive: [
      'Same skeleton: both models have memory, operations, intermediate state, and readout. A normal CPU step updates a bit string. A quantum gate updates an amplitude vector.',
      'Different state: classical state is one point such as 0101. Quantum state is a vector of complex amplitudes over labels such as |0000>, |0001>, and so on.',
      'Different operations: classical code may erase or overwrite freely. A closed quantum gate must be reversible and probability-preserving, so temporary values need cleanup instead of being forgotten.',
      'Math chain: a quantum circuit is a chain of mathematical transformations. The transformations are continuous at the amplitude level, but measurement still returns ordinary discrete bits.',
      'Project target: given a public key Q, the attack tries to recover the hidden private number d such that Q = dG. This repo asks what the quantum circuit for that recovery actually costs.',
      'Resource claim: peak logical qubits means the largest number of protected quantum wires alive at once. Non-Clifford count means the expensive quantum work summed over the whole run.',
    ],
    coreIdeas: [
      'Classical program: bit string plus discrete updates.',
      'Quantum circuit: amplitude vector plus reversible linear updates.',
      'Repo claim: resource numbers for one executable quantum attack circuit.',
    ],
    practicePrompt: 'Start with the classical-vs-quantum bridge. The only thing to hold in your head for now: this project counts the concrete quantum program, not an abstract threat slogan.',
    glossaryTerms: ['secp256k1', 'Discrete logarithm', 'Logical qubit', 'Non-Clifford'],
  },
  {
    id: 'qubit',
    module: 'Quantum substrate',
    title: 'Qubit basics: amplitudes and measurement',
    icon: Atom,
    intuition:
      'A qubit is one coherent two-amplitude state. Direct measurement sees squared arrow lengths as probabilities; it does not directly show the arrow angle.',
    whyItMatters:
      'The whole course depends on this split: measurement reads probabilities, while gates can use hidden relative angle before measurement.',
    mentalModel:
      'Start with only one qubit. It has one amplitude for outcome 0 and one amplitude for outcome 1. Picture each amplitude as an arrow: its length affects direct measurement, and its direction can matter later.',
    checkpoint: 'A probability coin has only chances. A qubit has amplitude lengths plus a relative angle that can matter before measurement.',
    deepDive: [
      'Notation: $|\\psi\\rangle = a|0\\rangle + b|1\\rangle$. The symbols $a$ and $b$ are complex numbers. For this course, a complex number just means an arrow in a flat plane: length plus angle.',
      'Probability rule: $P(0)=|a|^2$ and $P(1)=|b|^2$. The vertical bars mean arrow length. If both arrows have length $1/\\sqrt{2}$, direct measurement is 50/50.',
      'Relative angle: two states can have the same direct 50/50 probabilities but different arrow directions. Direct measurement cannot see that difference by itself.',
      'Measurement: a measurement samples one outcome and changes what remains. It is not a passive screen capture of both arrows.',
      'Bridge to gates: a gate is applied before measurement. The next page studies how valid gates can turn relative angle into a changed probability.',
    ],
    coreIdeas: [
      'Amplitude = arrow with length and angle.',
      'Measurement probability = squared arrow length.',
      'Relative angle is real circuit information even when direct measurement cannot see it.',
    ],
    practicePrompt: 'Use the phase-to-probability bridge only as a measurement experiment: keep the arrow lengths fixed and move the angle. Direct measurement stays 50/50.',
    glossaryTerms: ['Qubit', 'Amplitude'],
  },
  {
    id: 'one-qubit',
    module: 'Quantum substrate',
    title: 'One-qubit gates as reversible motion',
    icon: GitCompareArrows,
    intuition:
      'A one-qubit gate is a valid steering rule for the two-amplitude state. It can rotate, swap, and recombine amplitudes, but as a closed gate it must remain reversible.',
    whyItMatters:
      'This is the first place where “quantum speedup” stops sounding like magic. Gates do not push probabilities downhill toward the answer. They preserve information while arranging amplitude directions so later steps can make wrong branches cancel and useful branches reinforce.',
    mentalModel:
      'Start from one question: if a qubit is two amplitude arrows, which physical moves are legal before measurement? A legal closed gate is a two-by-two linear rule that preserves total probability, so it can split, swap, rotate, and recombine amplitudes without erasing where the state came from.',
    checkpoint: 'A one-qubit gate can make probabilities change, but a closed gate cannot be a many-to-one convergence rule because it must have an inverse.',
    deepDive: [
      'Valid gate: a quantum gate is a controlled physical operation applied before measurement. Mathematically it is unitary: linear, reversible, and total-probability preserving.',
      'Hadamard: H recombines the two amplitudes into a sum channel and a difference channel. That is why equal arrows can become always-0 or always-1 depending on relative angle.',
      'Cycles: some gates return after a few repeats. X twice returns to identity, H twice returns to identity, and four S phase turns return to identity.',
      'Long rotations: a rotation by an angle that is not a neat fraction of a full turn will keep visiting new positions instead of closing quickly.',
      'No attractor: a closed gate cannot steadily erase all starting states into one final point. If it did, the inverse would not know which starting state to recover.',
      'Measurement exception: measurement can collapse many possible states into one sampled result. That is why measurement is treated differently from reversible gates.',
    ],
    coreIdeas: [
      'A one-qubit gate is a two-by-two rule over the amplitude vector.',
      'Unitary means linear, reversible, and probability preserving.',
      'Measurement can collapse; a closed gate cannot be an attractor.',
    ],
    practicePrompt: 'Use the one-qubit labs as missions: make a balanced state, return to the start, create a hidden phase, then expose that phase by mixing again.',
    glossaryTerms: ['Quantum gate', 'Unitary', 'Hadamard gate', 'Destructive interference'],
  },
  {
    id: 'two-qubit',
    module: 'Quantum substrate',
    title: 'Two qubits: joint states and entanglement',
    icon: Binary,
    intuition:
      'Two qubits are not just two separate arrows. The full state has four amplitudes, one for each joint label: 00, 01, 10, and 11.',
    whyItMatters:
      'The moment operations can connect wires, the circuit can create joint structure that no pair of independent one-qubit descriptions can capture.',
    mentalModel:
      'Adding a second qubit changes the object from two amplitudes to a four-entry joint table: 00, 01, 10, and 11. Some tables are just two independent one-qubit states multiplied together. Entangled tables are different: the joint pattern is the smallest honest description.',
    checkpoint: 'A two-qubit state is entangled when the four-amplitude pattern cannot be factored into separate one-qubit states.',
    deepDive: [
      'State size: one qubit has two amplitudes. Two qubits have four amplitudes: $|00\\rangle$, $|01\\rangle$, $|10\\rangle$, and $|11\\rangle$. Three qubits would have eight.',
      'Product state: if the four-amplitude table can be built from one state for q0 and one state for q1, the qubits are still independent in this sense.',
      'Controlled gate: controlled-X, also called CNOT or CX, flips the target branch only where the control branch is 1. It is still a reversible gate.',
      'Bell pair: H on q0 followed by CX q0 q1 creates a state with only $|00\\rangle$ and $|11\\rangle$ branches. The two measurements agree even though neither qubit alone has a definite value.',
      'Entanglement: the Bell pair is not two private one-qubit states hiding behind the scenes. The compact description is the joint four-amplitude pattern.',
      'Observation: measurement samples one full two-bit label. Repeating the same circuit many times reveals the probability pattern.',
    ],
    coreIdeas: [
      'Two qubits are represented by four joint amplitudes.',
      'Controlled-X is a reversible branch permutation, not a measurement.',
      'Entanglement means the four-entry table cannot factor into two one-qubit states.',
    ],
    practicePrompt: 'Run the two-qubit missions. First make a product split, then make a Bell pair, then use interference to cancel one branch.',
    glossaryTerms: ['State vector', 'Controlled-X', 'CNOT', 'Bell pair', 'Entanglement'],
  },
  {
    id: 'gates',
    module: 'Quantum substrate',
    title: 'Gates, wires, controls, and reversibility',
    icon: CircuitBoard,
    intuition:
      'A quantum circuit is a time-ordered netlist of gates over named wires. Most useful arithmetic has to be reversible or explicitly uncomputed.',
    whyItMatters:
      'This is the bridge from “quantum ideas” to repo engineering. Once a value is a named quantum wire, it has a lifetime. If a temporary value is not cleaned, it is not just messy bookkeeping; it can remain correlated with the result and must still be counted.',
    mentalModel:
      'Read a circuit from left to right like a dataflow story. Wires carry quantum state through time. Gates touch specific wires. Controls make a target move only on selected branches. A useful temporary value follows a lifecycle: compute it, use it, then uncompute it back to zero.',
    checkpoint: 'A “scratch” bit is not free. It is a quantum wire with lifetime, owner, and cleanup obligations.',
    deepDive: [
      'Classical code can overwrite a temporary variable and forget how it was made. A quantum circuit cannot generally do that: the old information is part of the state.',
      'The usual pattern is compute, use, uncompute. If a temporary value was made from inputs, the circuit later runs the inverse steps to return that temporary wire to zero.',
      'The toy netlist shows rows over q0, q1, and q2. The real repo uses the same idea at much larger scale: primitive rows over concrete wires.',
    ],
    coreIdeas: [
      'Wire = named quantum storage across time.',
      'Gate row = one transformation applied to specific wires.',
      'Cleanup = inverse work that removes temporary garbage.',
    ],
    practicePrompt: 'Add Hadamard, controlled-X, and Toffoli rows in the primitive netlist toy. Watch rows and non-Clifford count change, then compare with the cleanup puzzle.',
    glossaryTerms: ['Netlist', 'Primitive row', 'Uncompute'],
  },
  {
    id: 'clifford',
    module: 'Cost model',
    title: 'Clifford vs non-Clifford',
    icon: Sparkles,
    intuition:
      'Clifford gates are the easy stabilizer backbone. Non-Clifford gates, especially Toffoli-like resources in this repo, are the expensive magic-state fuel.',
    whyItMatters:
      'The project optimizes two scarce resources at once: logical qubits for peak live state and non-Clifford count for expensive fault-tolerant magic work. A result is not meaningful if it wins one axis by quietly losing the other.',
    mentalModel:
      'Think of Clifford gates as motion inside a stabilizer map: still quantum, still useful, but structurally cheap to track and usually cheap to implement fault tolerantly. A non-Clifford step leaves that map and spends magic-state fuel. Arithmetic needs those escapes, so the repo reports them separately from qubits.',
    checkpoint: 'A low-qubit circuit can be bad if it explodes non-Clifford count, and a low-gate circuit can be bad if it needs too many live qubits.',
    deepDive: [
      'Clifford-only circuits are special: their states can be tracked efficiently by a classical stabilizer description. That makes them relatively cheap in many fault-tolerant models.',
      'Non-Clifford operations break out of that efficiently tracked family. Fault-tolerant machines usually pay for them using prepared magic-state resources.',
      'This repo mostly counts Toffoli-like non-Clifford work, because reversible arithmetic and table selection are full of controlled bit products.',
    ],
    coreIdeas: [
      'Clifford gates preserve a compact stabilizer description.',
      'Non-Clifford gates supply the magic needed for universal arithmetic.',
      'Peak qubits and non-Clifford count are separate headline axes.',
    ],
    practicePrompt: 'Use the stabilizer vs magic wheel. Add cheap Clifford moves first, then add a T gate and notice when the state class changes.',
    glossaryTerms: ['Clifford', 'Stabilizer state', 'Non-Clifford', 'Magic state'],
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
      'Read the repo headline as an algorithm-layer statement: how many protected logical wires are live in the circuit, and how much logical non-Clifford work is needed. A hardware machine adds another layer: error-correcting code, code distance, physical error rates, layout, timing, decoding, and magic factories.',
    checkpoint: 'Logical counts let us compare algorithms; hardware execution needs an additional error-correction and architecture model.',
    deepDive: [
      'Quantum hardware is noisy. Fault-tolerant algorithms therefore encode one logical wire across many physical carriers so small errors can be detected and corrected.',
      'The repo headline counts logical wires and logical operations. That is the right layer for comparing circuit designs before choosing a hardware architecture.',
      'To estimate hardware, you still need an error-correction code, target failure rate, factory model, connectivity, timing, and layout assumptions.',
    ],
    coreIdeas: [
      'Physical qubit = device-level carrier.',
      'Logical qubit = protected encoded circuit wire.',
      'Hardware estimates require a QEC and architecture model on top of repo resources.',
    ],
    practicePrompt: 'Use the logical-to-physical bridge and change the code distance. Notice that the same logical circuit can imply very different hardware envelopes.',
    glossaryTerms: ['Physical qubit', 'Logical qubit', 'Code distance', 'Logical failure'],
  },
  {
    id: 'phase-estimation',
    module: 'Attack algorithm',
    title: 'Phase estimation turns rhythm into bits',
    icon: Sigma,
    intuition:
      'Phase estimation is the measurement wrapper: it turns a hidden repeating pattern into bits that can be read.',
    whyItMatters:
      'The secp256k1 circuit is expensive because phase estimation asks for many controlled group operations, and each one expands into point-add arithmetic.',
    mentalModel:
      'Do not picture the answer as a stored bit waiting to be read. The controlled powers of a unitary create a rhythm of phases across a control register. The inverse-QFT readout tests candidate rhythms and turns the matching phase pattern into a likely binary label.',
    checkpoint: 'The curve arithmetic is the engine; phase estimation is the measuring instrument wrapped around it.',
    deepDive: [
      'A hidden period means outputs repeat in a structured way. Shor-style algorithms turn that repetition into a regular angle pattern across the control register.',
      'The inverse QFT is the readout step. It converts a clean angle rhythm into a sharp measurement peak, similar to how a spectrum analyzer reveals a frequency.',
      'The expensive part for secp256k1 is not the final readout. It is creating the angle rhythm by repeatedly running controlled elliptic-curve group operations.',
    ],
    coreIdeas: [
      'Controlled powers create a binary phase rhythm.',
      'The inverse QFT turns the matching rhythm into a measurement peak.',
      'For secp256k1, controlled curve arithmetic creates the expensive rhythm.',
    ],
    practicePrompt: 'Move the hidden phase numerator slider. The bars show which bit label becomes most likely after the phase-estimation readout.',
    glossaryTerms: ['Phase estimation', 'Hidden period', 'Fourier transform', 'Fourier label'],
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
      'A netlist is a table of primitive rows. Liveness says when each wire value is born, when it dies, and which owner must have capacity for it.',
    checkpoint: 'The best future engine is one source of truth that executes, counts, tests, and feeds proof inputs.',
    deepDive: [
      'A formula such as “point add” is too high-level to count directly. The engine must lower it into rows like compute partial product, add column, clean scratch, and produce output.',
      'Peak logical qubits come from overlapping live intervals. If a value is still needed, it counts even if a human stopped writing it in the summary.',
      'The long-term target is one executable stream that drives tests, liveness, owner capacity, resource totals, and proof inputs.',
    ],
    coreIdeas: [
      'Primitive rows are the countable object.',
      'Live intervals determine peak qubits.',
      'One engine should feed execution, tests, counts, and ZKP input.',
    ],
    practicePrompt: 'Open the stack map and then the mini resource engine. The important habit is to ask where each wire is born, where it dies, and who owns it.',
    glossaryTerms: ['Netlist', 'Primitive row', 'Liveness', 'Owner'],
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
      'A private key is a scalar d, and the public key is the point Q = dG. The quantum circuit does not try private keys one by one. It builds reversible two-register group operations of the form aG + bQ = (a + b*d)G, creating a hidden-period structure that phase estimation can sample.',
    checkpoint: 'The project is a circuit-engineering problem around a repeated secp256k1 point-add leaf, not a generic black-box quantum threat claim.',
    deepDive: [
      'ECDLP means: given G and Q = dG, recover the hidden scalar d. The quantum attack builds reversible group operations whose repeated structure exposes d.',
      'The toy oracle uses aG + bQ = (a + b*d)G. Different (a,b) pairs can collide in a way that encodes the secret scalar.',
      'The real circuit does not use tiny toy points. It repeats lookup-fed secp256k1 point-add leaves many times, which is why point-add resources dominate this repo.',
    ],
    coreIdeas: [
      'Public input: generator G and public point Q = dG.',
      'Oracle shape: aG + bQ hides d as a period direction.',
      'Resource bottleneck: repeated controlled secp256k1 point-add leaves.',
    ],
    practicePrompt: 'Start with the Whole attack map, then use the Discrete-log oracle toy. Change the secret scalar and watch the hidden-period relation change before opening phase kickback.',
    glossaryTerms: ['Discrete logarithm', 'Oracle', 'Hidden period', 'Phase kickback'],
  },
  {
    id: 'coordinates',
    module: 'Elliptic curve layer',
    title: 'Coordinates, infinity, and field slots',
    icon: Sigma,
    intuition:
      'Affine points are the compact street address. Projective-style coordinates keep scale information live so the hot point-add loop can avoid repeated inversions.',
    whyItMatters:
      'The repo’s slot fights are about how many field-sized live registers are needed while computing a point-add boundary.',
    mentalModel:
      'Affine is one direct name for a point: x and y. Projective is a family of names for the same point: extra scale data is carried so the circuit can use multiply/add formulas instead of stopping for division inside every point-add. The price is live field slots, and each secp256k1 field slot is 256 logical wires.',
    checkpoint: 'A field slot is one secp256k1 coordinate-sized quantum register: 256 logical wires with an owner, capacity, birth row, and death row.',
    deepDive: [
      'Affine coordinates store a point directly as x and y. A direct point-add slope contains a division, which means a modular inverse over the field.',
      'Projective-style coordinates store an equivalent representative with extra scale information. The hot loop pays extra coordinate slots and more multiply/add work to avoid repeated inversion.',
      'The number 256 comes from secp256k1 field arithmetic. Each coordinate is a number modulo a roughly 256-bit prime, so one live coordinate register means 256 live logical wires.',
      'Infinity cases are part of the same point-add contract. Doubling, inverse pairs, accumulator infinity, and lookup infinity must execute the same counted boundary.',
      'Overwrite is a proof obligation. Reusing a coordinate lane is valid only when the engine proves an owner-preserving reversible transformation, not when a human renames a variable.',
    ],
    coreIdeas: [
      'Affine saves live coordinates but pays inversion in point-add formulas.',
      'Projective spends scale slots to use multiply/add formulas on the hot path.',
      'Every live secp256k1 field slot is 256 counted logical wires.',
    ],
    practicePrompt: 'Move the projective scale first and confirm that several triples name the same affine point. Then open the overwrite and boundary labs and ask which field slots are live at the same time.',
    glossaryTerms: ['Affine point', 'Projective point', 'Field slot', 'Point-add boundary'],
  },
  {
    id: 'lookup-qroam',
    module: 'Lookup systems',
    title: 'QROAM is table lookup under quantum accounting',
    icon: Binary,
    intuition:
      'The circuit repeatedly selects precomputed curve-point data. In quantum form, a lookup is not a free memory read; it is a reversible selection circuit with controls, target bits, workspace, and cleanup.',
    whyItMatters:
      'Several earlier low-qubit stories failed because a lookup output lane or QROAM junk register was treated as if it were not live.',
    mentalModel:
      'A QROAM lookup is a reversible table-selection circuit. The address controls decide which row contributes, the selected bits land in a target register, helper junk supports the selection network, and cleanup removes the temporary path. Gates and qubits must come from the same model.',
    checkpoint: 'A lookup output is only free if the executable liveness artifact proves it aliases already-counted capacity.',
    deepDive: [
      'The attack uses precomputed point chunks. A quantum address cannot simply index a classical array for free; the table selection has controls, target bits, workspace, and cleanup.',
      'QROAMClean-style accounting trades non-Clifford work against workspace. If K is increased, the gate formula changes and the junk-register capacity changes too.',
      'A low-qubit claim fails if lookup target lanes or QROAM junk registers are omitted from live capacity. This was one of the central bug classes in the repo.',
      'The useful question is not “is there a lookup?” but “which bits are selected, where does the selected data live, and when is the selection workspace uncomputed?”',
    ],
    coreIdeas: [
      'Lookup address, target, junk, and cleanup all count.',
      'QROAM trades gate count against workspace.',
      'Free output lanes require liveness proof, not assertion.',
    ],
    practicePrompt: 'Select table bits in the QROAM toy, then use the QROAMClean tradeoff dial. Compare how workspace and non-Clifford pressure move in opposite directions.',
    glossaryTerms: ['QROAM', 'Lookup infinity', 'Owner', 'Capacity'],
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
    deepDive: [
      'The toy DSL is intentionally small: H, X, CX, CCX, and M. The point is to feel that even simple rows have concrete wire operands and countable costs.',
      'Invalid opcodes are useful. They show that a compiler must reject unknown operations instead of silently pretending a circuit was produced.',
      'The same habit scales up: an arithmetic optimization is not real until it becomes primitive rows with owners, costs, and cleanup.',
    ],
    coreIdeas: [
      'Write rows before trusting formulas.',
      'Unknown operations must fail loudly.',
      'Tiny netlists train the same audit reflex used on large lowerings.',
    ],
    practicePrompt: 'Edit the DSL into an invalid program, then fix it with H, CX, and CCX rows. Check that the parser, non-Clifford count, and row list agree.',
    glossaryTerms: ['Netlist', 'Opcode lowering', 'Primitive row', 'Non-Clifford'],
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
      'A temporary value is safe only if it is used as intended and then returned to zero by reversing the computation that created it.',
    checkpoint: 'A cleanup proof must identify the source controls, target, inverse operation, and liveness interval.',
    deepDive: [
      'Compute creates a temporary wire from source controls. Use consumes that temporary into the intended destination.',
      'Uncompute must replay the matching source controls so the temporary target returns to zero. Merely dropping the variable name is not cleanup.',
      'The modular accumulator blocker is this pattern at scale: many temporary AND targets need consume rows and source-uncompute rows.',
    ],
    coreIdeas: [
      'Temporary value = live quantum state.',
      'Cleanup = inverse path with the same sources.',
      'No cleanup means garbage still counts or breaks semantics.',
    ],
    practicePrompt: 'In the cleanup puzzle, select the matching uncompute row. Then open the scratch lifecycle lab and compare the consume-row and source-control requirements.',
    glossaryTerms: ['Uncompute', 'Temporary AND', 'Source-uncompute', 'Abandoned garbage'],
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
    deepDive: [
      'A field multiply starts as many bit-level partial products. Each product is a temporary quantum value unless it is immediately consumed and cleaned.',
      'Modular reduction folds high columns back into the field range. Those fold rows are part of the primitive stream, not post-hoc arithmetic narration.',
      'The repo blocker is promotion: candidate accumulator rows must become the counted executable stream, with source-uncompute and Clifford expansion accounted for.',
    ],
    coreIdeas: [
      'Multiply = partial products plus carries plus reduction.',
      'Every temporary product needs a lifecycle.',
      'Promotion requires one primitive stream, not a side artifact.',
    ],
    practicePrompt: 'Use the partial-product grid first. Then inspect accumulator lowering and switch to promoted-only facts to see what is still not accepted.',
    glossaryTerms: ['Partial product', 'Fold', 'Accumulator', 'Carry-save'],
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
      'An owner is a counted capacity bucket. A live wire group assigned to that owner is valid only when peak assigned width fits inside the owner budget.',
    checkpoint: 'Every wire group needs exactly one owner, and every owner capacity must cover peak assigned live width.',
    deepDive: [
      'Naming an owner is not proof. The engine must sum live assigned widths and compare them with the owner capacity at the busiest row.',
      'A borrowed wire is suspicious because it may be live at the same time as the resource it claims to replace.',
      'The owner-capacity game intentionally starts failing so the learner has to assign the missing guard workspace explicitly.',
    ],
    coreIdeas: [
      'Exactly one owner per live wire group.',
      'Owner capacity must cover peak assigned width.',
      'Borrowed lanes are invalid until liveness proves aliasing.',
    ],
    practicePrompt: 'Inject the hidden scratch lane in the invariant lab, then fix owner assignment in the capacity game until the numeric load fits.',
    glossaryTerms: ['Owner', 'Capacity', 'Live interval', 'Peak live qubits'],
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
    deepDive: [
      'The engine takes primitive rows as input, derives live intervals, assigns owners, checks capacity, and computes peak logical qubits.',
      'The key architectural goal is one source of truth: the same stream should drive execution tests, liveness, resource totals, docs, and proof inputs.',
      'A resource result becomes stronger when fewer numbers are manually selected and more are generated from the executable circuit path.',
    ],
    coreIdeas: [
      'Executable primitive stream is the source of truth.',
      'Liveness derives qubits mechanically.',
      'Generated artifacts should feed docs and proofs.',
    ],
    practicePrompt: 'Open the circuit stack map and click Primitive netlist engine. Then use the mini engine to make the audit pass by fixing owner capacity and cleanup.',
    glossaryTerms: ['Circuit stack', 'Liveness', 'Owner', 'Artifact atlas'],
  },
  {
    id: 'mini-engine',
    module: 'Repo engine',
    title: 'Derive peak qubits from live intervals',
    icon: Cpu,
    intuition:
      'A resource engine scans primitive rows, derives live intervals, assigns each live wire to one owner, then takes the maximum concurrent width.',
    whyItMatters:
      'This is the mechanical habit needed to attack the repo constructively: every proposed optimization must survive the same liveness derivation.',
    mentalModel:
      'Treat the toy engine as the smallest version of the repo resource counter: rows create values, cleanup kills values, owners provide capacity, and the peak row determines qubits.',
    checkpoint: 'To improve a circuit, you need to move births earlier/later, shorten deaths with cleanup, or give owners enough counted capacity.',
    deepDive: [
      'The mini engine starts with a failing assignment so the learner sees why owner names are insufficient.',
      'Adding a source-uncompute row shortens a live interval. The output is unchanged, but the peak live width can drop.',
      'Opcode lowering shows the next layer down: one abstract operation expands into primitive rows with operands, cleanup, and non-Clifford cost.',
    ],
    coreIdeas: [
      'Birth/death rows define live intervals.',
      'Owner assignment and capacity are checked numerically.',
      'Lowering connects abstract operations to primitive rows.',
    ],
    practicePrompt: 'Make the mini engine pass by assigning the scratch owner and adding source uncompute. Then remove cleanup in opcode lowering and watch the audit fail.',
    glossaryTerms: ['Live interval', 'Owner', 'Capacity', 'Opcode lowering'],
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
      'A candidate is only useful if it improves a resource number and still has a path to executable semantics, owner capacity, primitive lowering, and proof input.',
    checkpoint: 'A useful optimization proposal must say which constraint it relaxes, which cost it pays, and how it will be promoted into the engine.',
    deepDive: [
      'The target is multi-axis: reduce logical qubits, keep non-Clifford under budget, preserve point-add semantics, and avoid hidden lookup or scratch capacity.',
      'Some rows are promising hypotheses rather than accepted results. The app should make that status visible instead of letting the smallest number win by default.',
      'A real optimization should explain what changed, which invariant still holds, what new cost appears, and which artifact proves the promotion.',
    ],
    coreIdeas: [
      'Lower qubits alone is not enough.',
      'Gate budget, semantics, capacity, and promotion all matter.',
      'Rejected and hypothesis rows are useful only when clearly labeled.',
    ],
    practicePrompt: 'Switch optimization candidates with both targets required. Then temporarily relax executable promotion to see why an attractive row can pass a toy gate but remain unpublishable.',
    glossaryTerms: ['Tradeoff', 'Pareto frontier', 'Promoted candidate', 'Claim classification'],
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
      'The point-add leaf is an API with branch tests, not a single formula. Random cases cover the ordinary branch; edge cases cover distinct branches with different algebraic behavior.',
    checkpoint: 'A reviewer should reject a lower-qubit point-add result until every boundary family passes against the counted executable interface.',
    deepDive: [
      'Ordinary random additions test the hot path. They do not prove doubling, inverse pairs, accumulator infinity, or lookup infinity behavior.',
      'The counted resource family must execute the same interface that the semantic artifact tests. Otherwise a proof can certify the wrong boundary.',
      'The debugger starts from passing evidence and lets you deliberately narrow coverage so the missing edge cases become visible.',
    ],
    coreIdeas: [
      'Point-add is an executable API boundary.',
      'Edge cases are part of semantics, not rare extras.',
      'Counted interface and tested interface must match.',
    ],
    practicePrompt: 'Click inverse pair and lookup infinity in the boundary debugger. Then enable random-only testing and watch the covered-case count collapse.',
    glossaryTerms: ['Point-add boundary', 'Lookup infinity', 'Permutation contract', 'Coordinate normalization'],
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
    deepDive: [
      'Useful repo work starts with a narrow claim. “Improve the circuit” is too vague; “promote this source-uncompute row into the primitive stream” is testable.',
      'Each claim level needs different evidence. A semantic candidate, a strict primitive result, and an accepted baseline are not interchangeable.',
      'The contribution page is the handoff from learning to action: choose a mission, complete its evidence checklist, and state the remaining blocker.',
    ],
    coreIdeas: [
      'Small claim, explicit evidence, clear status.',
      'Claim classification prevents accidental overstatement.',
      'Mission packets connect learning to repo patches.',
    ],
    practicePrompt: 'Use the mission board first. Then classify a claim in the audit drill and require the evidence items until the audit passes.',
    glossaryTerms: ['Mission packet', 'Claim classification', 'Confidence ladder', 'Promoted candidate'],
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
    deepDive: [
      'A verifier can say “this proof is valid” while the proved statement is stale, smoke-sized, or weaker than the current resource claim.',
      'The public values are the verifier-visible contract. They must bind the selected family, resource digest, case corpus, and proof statement being published.',
      'Compressed and Groth16 proofs are release evidence only after the checked input, verifier key, proof bundle, and physical baseline status agree.',
    ],
    coreIdeas: [
      'Proof validity is not the same as claim validity.',
      'Public values define what the verifier actually sees.',
      'Fresh artifacts and current resource contract must agree.',
    ],
    practicePrompt: 'Use the ZKP boundary lab to close fixtures, macro boundary, and proof verification. Then compare the confidence ladder before changing claim wording.',
    glossaryTerms: ['ZKP', 'Groth16', 'Public values', 'Confidence ladder'],
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
    deepDive: [
      'Google rows are external public comparison lines. They are useful context, but they are not artifacts generated by this repo.',
      'Repo rows must be read with status. A macro/ZKP wrapper reference, a strict candidate, and an accepted physical baseline would justify different wording.',
      'The current honest state is stronger than marketing but weaker than final victory: there are candidates, blockers, and a path to improve the evidence.',
    ],
    coreIdeas: [
      'External baselines are comparison rows.',
      'Repo results require status labels.',
      'Accepted baseline remains blocked until all gates close.',
    ],
    practicePrompt: 'Filter the baseline explorer by status, then use the promotion lab. Close blockers deliberately and check when the wording becomes allowed.',
    glossaryTerms: ['Baseline', 'Promoted candidate', 'Artifact atlas', 'Learning path'],
  },
];

export const glossary = [
  ['secp256k1', 'The elliptic-curve system used by Bitcoin public keys; this repo studies the quantum circuit cost of attacking its discrete logarithm problem.'],
  ['Qubit', 'A coherent two-state quantum system used as one wire in a circuit.'],
  ['Amplitude', 'A complex state-vector component whose squared magnitude gives a measurement probability.'],
  ['Quantum gate', 'A controlled operation applied before measurement. In the circuit model it is a fixed transformation of amplitudes.'],
  ['Unitary', 'A valid quantum gate rule that is linear, reversible, and preserves total probability.'],
  ['Hadamard gate', 'A one-qubit gate that combines the 0-amplitude and 1-amplitude so their relative angle can change measured probabilities. Circuit diagrams often abbreviate it as H.'],
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
  ['Field slot', 'One secp256k1 coordinate-sized number register. It has 256 logical wires because secp256k1 field elements are 256-bit numbers.'],
  ['QROAM', 'A quantum read-only memory tradeoff for selecting table data.'],
  ['Phase estimation', 'A quantum routine that extracts a hidden eigenphase or period into classical bits.'],
  ['Fourier transform', 'A change of basis that turns a regular amplitude-angle rhythm into a sharp frequency label.'],
  ['Destructive interference', 'Amplitude cancellation caused by arrows pointing in different directions before measurement.'],
  ['Discrete logarithm', 'The hidden scalar d in Q = dG, where G and Q are known group elements.'],
  ['Oracle', 'A reversible black-box-style operation the quantum algorithm queries in superposition.'],
  ['Whole-oracle composition', 'The resource reconstruction that combines the phase shell, direct seed, point-add leaves, lookup work, arithmetic work, and peak workspace into one checked oracle row.'],
  ['Peak workspace', 'The live logical-qubit surface reused across repeated calls; unlike gate count, it is not multiplied by the number of sequential leaves.'],
  ['Hidden period', 'A repeated relation in the oracle outputs, such as shifting (a,b) without changing aG + bQ.'],
  ['Phase kickback', 'A pattern where a computed oracle value is returned to zero while its phase imprint remains on the input register.'],
  ['Fourier label', 'A frequency-state label that converts an oracle output value into a regular angle pattern over the queried inputs.'],
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
    prompt: 'Why does the inverse QFT produce a sharp label for a clean angle rhythm?',
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
      'It turns f(a,b) into an angle pattern over the input lattice while the output register can be uncomputed.',
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
