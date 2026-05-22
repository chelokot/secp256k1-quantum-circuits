use num_bigint::BigUint;
use num_traits::{Num, One, ToPrimitive, Zero};
use serde::{
    de::{DeserializeOwned, Deserializer},
    ser::{SerializeSeq, SerializeStruct, Serializer},
    Deserialize, Serialize,
};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

const DIGEST_SCHEME: &str = "compiler-project-semantic-json-sha256-v1";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttestationInput {
    pub schema: String,
    pub claim: CommittedDocument<ClaimDocument>,
    pub leaf_document: CommittedDocument<LeafDocument>,
    pub family_document: CommittedDocument<FamilyDocument>,
    pub case_corpus_document: CommittedDocument<CaseCorpusDocument>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommittedDocument<T> {
    pub document_type: String,
    pub artifact_path: String,
    pub digest_scheme: String,
    pub sha256: String,
    pub payload: T,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SemanticJsonPayload(pub Value);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaimDocument {
    pub schema: String,
    pub selected_family_alias: String,
    pub selected_family_name: String,
    pub field_bits: u32,
    pub leaf_call_count_total: u32,
    pub expected_full_oracle_non_clifford: u64,
    pub expected_total_logical_qubits: u64,
    pub expected_case_count: u32,
    pub non_clifford_formula: NonCliffordFormula,
    pub logical_qubit_formula: LogicalQubitFormula,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct NonCliffordFormula {
    pub arithmetic_leaf_non_clifford: u64,
    pub per_leaf_lookup_non_clifford: u64,
    pub direct_seed_non_clifford: u64,
    pub leaf_call_count_total: u32,
    pub arithmetic_component: u64,
    pub lookup_component: u64,
    pub reconstructed_total: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LogicalQubitFormula {
    pub field_bits: u32,
    pub arithmetic_slot_count: u32,
    pub control_slot_count: u32,
    pub borrowed_interface_qubits: u32,
    pub lookup_workspace_qubits: u32,
    pub live_phase_bits: u32,
    pub arithmetic_component: u64,
    pub reconstructed_total: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeafDocument {
    pub schema: String,
    pub curve: String,
    pub field_modulus_hex: String,
    pub curve_b: u32,
    pub b3: u32,
    pub variant: String,
    pub interface_wires: Vec<String>,
    pub lookup_interface_slots: Vec<String>,
    pub arithmetic_slots: Vec<String>,
    #[serde(default)]
    pub lookup_infinity_policy: Option<String>,
    pub instructions: Vec<Instruction>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct Instruction {
    pub pc: u32,
    pub op: String,
    pub comment: Option<String>,
    pub dst: Option<InstructionDestination>,
    pub src: Option<InstructionSource>,
    pub flag: Option<String>,
    pub const_value: Option<u64>,
    pub chunk_bits: Option<u32>,
    pub chunk_count: Option<u32>,
    pub b3: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InstructionDestination {
    Register(String),
    Registers(Vec<String>),
}

#[derive(Serialize, Deserialize)]
#[serde(untagged)]
enum HumanInstructionDestination {
    Register(String),
    Registers(Vec<String>),
}

#[derive(Serialize, Deserialize)]
enum BinaryInstructionDestination {
    Register(String),
    Registers(Vec<String>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InstructionSource {
    Register(String),
    Pair([String; 2]),
    Triple([String; 3]),
    StreamedTail {
        c: String,
        h: String,
        a: String,
        y: String,
        z: String,
    },
    FullyStreamedTail {
        x: String,
        h: String,
        y: String,
        z: String,
    },
    ReusableChunkTail {
        x: String,
        y: String,
        z: String,
        scratch: String,
    },
    AllStreamedTail {
        x: String,
        y: String,
        z: String,
    },
    FlagBit {
        flags: String,
        bit: u64,
    },
    Lookup {
        table: String,
        key: String,
    },
}

#[derive(Serialize, Deserialize)]
#[serde(untagged)]
enum HumanInstructionSource {
    Register(String),
    Pair([String; 2]),
    Triple([String; 3]),
    StreamedTail {
        c: String,
        h: String,
        a: String,
        y: String,
        z: String,
    },
    FullyStreamedTail {
        x: String,
        h: String,
        y: String,
        z: String,
    },
    ReusableChunkTail {
        x: String,
        y: String,
        z: String,
        scratch: String,
    },
    AllStreamedTail {
        x: String,
        y: String,
        z: String,
    },
    FlagBit {
        flags: String,
        bit: u64,
    },
    Lookup {
        table: String,
        key: String,
    },
}

#[derive(Serialize, Deserialize)]
enum BinaryInstructionSource {
    Register(String),
    Pair([String; 2]),
    Triple([String; 3]),
    StreamedTail {
        c: String,
        h: String,
        a: String,
        y: String,
        z: String,
    },
    FullyStreamedTail {
        x: String,
        h: String,
        y: String,
        z: String,
    },
    AllStreamedTail {
        x: String,
        y: String,
        z: String,
    },
    ReusableChunkTail {
        x: String,
        y: String,
        z: String,
        scratch: String,
    },
    FlagBit {
        flags: String,
        bit: u64,
    },
    Lookup {
        table: String,
        key: String,
    },
}

#[derive(Serialize, Deserialize)]
struct HumanInstruction {
    pc: u32,
    op: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    comment: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    dst: Option<InstructionDestination>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    src: Option<InstructionSource>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    flag: Option<String>,
    #[serde(rename = "const", default, skip_serializing_if = "Option::is_none")]
    const_value: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    chunk_bits: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    chunk_count: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    b3: Option<u64>,
}

#[derive(Serialize, Deserialize)]
struct BinaryInstruction {
    pc: u32,
    op: String,
    comment: Option<String>,
    dst: Option<InstructionDestination>,
    src: Option<InstructionSource>,
    flag: Option<String>,
    const_value: Option<u64>,
    chunk_bits: Option<u32>,
    chunk_count: Option<u32>,
    b3: Option<u64>,
}

impl From<&Instruction> for HumanInstruction {
    fn from(value: &Instruction) -> Self {
        Self {
            pc: value.pc,
            op: value.op.clone(),
            comment: value.comment.clone(),
            dst: value.dst.clone(),
            src: value.src.clone(),
            flag: value.flag.clone(),
            const_value: value.const_value,
            chunk_bits: value.chunk_bits,
            chunk_count: value.chunk_count,
            b3: value.b3,
        }
    }
}

impl From<HumanInstruction> for Instruction {
    fn from(value: HumanInstruction) -> Self {
        Self {
            pc: value.pc,
            op: value.op,
            comment: value.comment,
            dst: value.dst,
            src: value.src,
            flag: value.flag,
            const_value: value.const_value,
            chunk_bits: value.chunk_bits,
            chunk_count: value.chunk_count,
            b3: value.b3,
        }
    }
}

impl From<&Instruction> for BinaryInstruction {
    fn from(value: &Instruction) -> Self {
        Self {
            pc: value.pc,
            op: value.op.clone(),
            comment: value.comment.clone(),
            dst: value.dst.clone(),
            src: value.src.clone(),
            flag: value.flag.clone(),
            const_value: value.const_value,
            chunk_bits: value.chunk_bits,
            chunk_count: value.chunk_count,
            b3: value.b3,
        }
    }
}

impl From<BinaryInstruction> for Instruction {
    fn from(value: BinaryInstruction) -> Self {
        Self {
            pc: value.pc,
            op: value.op,
            comment: value.comment,
            dst: value.dst,
            src: value.src,
            flag: value.flag,
            const_value: value.const_value,
            chunk_bits: value.chunk_bits,
            chunk_count: value.chunk_count,
            b3: value.b3,
        }
    }
}

impl Serialize for InstructionDestination {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if serializer.is_human_readable() {
            match self {
                InstructionDestination::Register(register) => serializer.serialize_str(register),
                InstructionDestination::Registers(registers) => {
                    let mut seq = serializer.serialize_seq(Some(registers.len()))?;
                    for register in registers {
                        seq.serialize_element(register)?;
                    }
                    seq.end()
                }
            }
        } else {
            match self {
                InstructionDestination::Register(register) => {
                    BinaryInstructionDestination::Register(register.clone())
                }
                InstructionDestination::Registers(registers) => {
                    BinaryInstructionDestination::Registers(registers.clone())
                }
            }
            .serialize(serializer)
        }
    }
}

impl<'de> Deserialize<'de> for InstructionDestination {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        if deserializer.is_human_readable() {
            let destination = HumanInstructionDestination::deserialize(deserializer)?;
            Ok(match destination {
                HumanInstructionDestination::Register(register) => {
                    InstructionDestination::Register(register)
                }
                HumanInstructionDestination::Registers(registers) => {
                    InstructionDestination::Registers(registers)
                }
            })
        } else {
            let destination = BinaryInstructionDestination::deserialize(deserializer)?;
            Ok(match destination {
                BinaryInstructionDestination::Register(register) => {
                    InstructionDestination::Register(register)
                }
                BinaryInstructionDestination::Registers(registers) => {
                    InstructionDestination::Registers(registers)
                }
            })
        }
    }
}

impl Serialize for SemanticJsonPayload {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if serializer.is_human_readable() {
            self.0.serialize(serializer)
        } else {
            serde_json::to_string(&self.0)
                .expect("failed to serialize semantic JSON payload")
                .serialize(serializer)
        }
    }
}

impl<'de> Deserialize<'de> for SemanticJsonPayload {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        if deserializer.is_human_readable() {
            Value::deserialize(deserializer).map(Self)
        } else {
            let encoded = String::deserialize(deserializer)?;
            serde_json::from_str(&encoded)
                .map(Self)
                .map_err(serde::de::Error::custom)
        }
    }
}

impl Serialize for Instruction {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if serializer.is_human_readable() {
            HumanInstruction::from(self).serialize(serializer)
        } else {
            BinaryInstruction::from(self).serialize(serializer)
        }
    }
}

impl<'de> Deserialize<'de> for Instruction {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        if deserializer.is_human_readable() {
            HumanInstruction::deserialize(deserializer).map(Into::into)
        } else {
            BinaryInstruction::deserialize(deserializer).map(Into::into)
        }
    }
}

impl Serialize for InstructionSource {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if serializer.is_human_readable() {
            match self {
                InstructionSource::Register(register) => serializer.serialize_str(register),
                InstructionSource::Pair(pair) => {
                    let mut seq = serializer.serialize_seq(Some(pair.len()))?;
                    for item in pair {
                        seq.serialize_element(item)?;
                    }
                    seq.end()
                }
                InstructionSource::Triple(triple) => {
                    let mut seq = serializer.serialize_seq(Some(triple.len()))?;
                    for item in triple {
                        seq.serialize_element(item)?;
                    }
                    seq.end()
                }
                InstructionSource::StreamedTail { c, h, a, y, z } => {
                    let mut map = serializer.serialize_struct("InstructionSource", 5)?;
                    map.serialize_field("a", a)?;
                    map.serialize_field("c", c)?;
                    map.serialize_field("h", h)?;
                    map.serialize_field("y", y)?;
                    map.serialize_field("z", z)?;
                    map.end()
                }
                InstructionSource::FullyStreamedTail { x, h, y, z } => {
                    let mut map = serializer.serialize_struct("InstructionSource", 4)?;
                    map.serialize_field("h", h)?;
                    map.serialize_field("x", x)?;
                    map.serialize_field("y", y)?;
                    map.serialize_field("z", z)?;
                    map.end()
                }
                InstructionSource::AllStreamedTail { x, y, z } => {
                    let mut map = serializer.serialize_struct("InstructionSource", 3)?;
                    map.serialize_field("x", x)?;
                    map.serialize_field("y", y)?;
                    map.serialize_field("z", z)?;
                    map.end()
                }
                InstructionSource::ReusableChunkTail { x, y, z, scratch } => {
                    let mut map = serializer.serialize_struct("InstructionSource", 4)?;
                    map.serialize_field("scratch", scratch)?;
                    map.serialize_field("x", x)?;
                    map.serialize_field("y", y)?;
                    map.serialize_field("z", z)?;
                    map.end()
                }
                InstructionSource::FlagBit { flags, bit } => {
                    let mut map = serializer.serialize_struct("InstructionSource", 2)?;
                    map.serialize_field("flags", flags)?;
                    map.serialize_field("bit", bit)?;
                    map.end()
                }
                InstructionSource::Lookup { table, key } => {
                    let mut map = serializer.serialize_struct("InstructionSource", 2)?;
                    map.serialize_field("table", table)?;
                    map.serialize_field("key", key)?;
                    map.end()
                }
            }
        } else {
            match self {
                InstructionSource::Register(register) => {
                    BinaryInstructionSource::Register(register.clone())
                }
                InstructionSource::Pair(pair) => BinaryInstructionSource::Pair(pair.clone()),
                InstructionSource::Triple(triple) => {
                    BinaryInstructionSource::Triple(triple.clone())
                }
                InstructionSource::StreamedTail { c, h, a, y, z } => {
                    BinaryInstructionSource::StreamedTail {
                        c: c.clone(),
                        h: h.clone(),
                        a: a.clone(),
                        y: y.clone(),
                        z: z.clone(),
                    }
                }
                InstructionSource::FullyStreamedTail { x, h, y, z } => {
                    BinaryInstructionSource::FullyStreamedTail {
                        x: x.clone(),
                        h: h.clone(),
                        y: y.clone(),
                        z: z.clone(),
                    }
                }
                InstructionSource::AllStreamedTail { x, y, z } => {
                    BinaryInstructionSource::AllStreamedTail {
                        x: x.clone(),
                        y: y.clone(),
                        z: z.clone(),
                    }
                }
                InstructionSource::ReusableChunkTail { x, y, z, scratch } => {
                    BinaryInstructionSource::ReusableChunkTail {
                        x: x.clone(),
                        y: y.clone(),
                        z: z.clone(),
                        scratch: scratch.clone(),
                    }
                }
                InstructionSource::FlagBit { flags, bit } => BinaryInstructionSource::FlagBit {
                    flags: flags.clone(),
                    bit: *bit,
                },
                InstructionSource::Lookup { table, key } => BinaryInstructionSource::Lookup {
                    table: table.clone(),
                    key: key.clone(),
                },
            }
            .serialize(serializer)
        }
    }
}

impl<'de> Deserialize<'de> for InstructionSource {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        if deserializer.is_human_readable() {
            let source = HumanInstructionSource::deserialize(deserializer)?;
            Ok(match source {
                HumanInstructionSource::Register(register) => InstructionSource::Register(register),
                HumanInstructionSource::Pair(pair) => InstructionSource::Pair(pair),
                HumanInstructionSource::Triple(triple) => InstructionSource::Triple(triple),
                HumanInstructionSource::StreamedTail { c, h, a, y, z } => {
                    InstructionSource::StreamedTail { c, h, a, y, z }
                }
                HumanInstructionSource::FullyStreamedTail { x, h, y, z } => {
                    InstructionSource::FullyStreamedTail { x, h, y, z }
                }
                HumanInstructionSource::AllStreamedTail { x, y, z } => {
                    InstructionSource::AllStreamedTail { x, y, z }
                }
                HumanInstructionSource::ReusableChunkTail { x, y, z, scratch } => {
                    InstructionSource::ReusableChunkTail { x, y, z, scratch }
                }
                HumanInstructionSource::FlagBit { flags, bit } => {
                    InstructionSource::FlagBit { flags, bit }
                }
                HumanInstructionSource::Lookup { table, key } => {
                    InstructionSource::Lookup { table, key }
                }
            })
        } else {
            let source = BinaryInstructionSource::deserialize(deserializer)?;
            Ok(match source {
                BinaryInstructionSource::Register(register) => {
                    InstructionSource::Register(register)
                }
                BinaryInstructionSource::Pair(pair) => InstructionSource::Pair(pair),
                BinaryInstructionSource::Triple(triple) => InstructionSource::Triple(triple),
                BinaryInstructionSource::StreamedTail { c, h, a, y, z } => {
                    InstructionSource::StreamedTail { c, h, a, y, z }
                }
                BinaryInstructionSource::FullyStreamedTail { x, h, y, z } => {
                    InstructionSource::FullyStreamedTail { x, h, y, z }
                }
                BinaryInstructionSource::AllStreamedTail { x, y, z } => {
                    InstructionSource::AllStreamedTail { x, y, z }
                }
                BinaryInstructionSource::ReusableChunkTail { x, y, z, scratch } => {
                    InstructionSource::ReusableChunkTail { x, y, z, scratch }
                }
                BinaryInstructionSource::FlagBit { flags, bit } => {
                    InstructionSource::FlagBit { flags, bit }
                }
                BinaryInstructionSource::Lookup { table, key } => {
                    InstructionSource::Lookup { table, key }
                }
            })
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FamilyDocument {
    pub name: String,
    pub summary: String,
    pub gate_set: String,
    pub phase_shell: String,
    pub slot_allocation_family: String,
    pub arithmetic_kernel_family: String,
    pub lookup_family: String,
    pub arithmetic_leaf_non_clifford: u64,
    pub direct_seed_non_clifford: u64,
    pub per_leaf_lookup_non_clifford: u64,
    pub full_oracle_non_clifford: u64,
    pub arithmetic_slot_count: u32,
    pub control_slot_count: u32,
    pub borrowed_interface_qubits: u32,
    pub lookup_workspace_qubits: u32,
    pub live_phase_bits: u32,
    pub total_logical_qubits: u64,
    pub phase_shell_hadamards: u64,
    pub phase_shell_measurements: u64,
    pub phase_shell_rotations: u64,
    pub phase_shell_rotation_depth: u64,
    pub total_measurements: u64,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct CaseCorpusDocument {
    pub schema: String,
    pub curve: String,
    pub field_modulus_hex: String,
    pub curve_b: u32,
    pub seed_sha256: String,
    pub seed_hash_scheme: Option<String>,
    pub case_start_index: Option<u32>,
    pub case_count: u32,
    pub category_counts: BTreeMap<String, u32>,
    pub cases: Vec<PointAddCase>,
    pub notes: Vec<String>,
}

#[derive(Serialize, Deserialize)]
struct HumanCaseCorpusDocument {
    schema: String,
    curve: String,
    field_modulus_hex: String,
    curve_b: u32,
    seed_sha256: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    seed_hash_scheme: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    case_start_index: Option<u32>,
    case_count: u32,
    category_counts: BTreeMap<String, u32>,
    cases: Vec<PointAddCase>,
    notes: Vec<String>,
}

#[derive(Serialize, Deserialize)]
struct BinaryCaseCorpusDocument {
    schema: String,
    curve: String,
    field_modulus_hex: String,
    curve_b: u32,
    seed_sha256: String,
    seed_hash_scheme: Option<String>,
    case_start_index: Option<u32>,
    case_count: u32,
    category_counts: BTreeMap<String, u32>,
    cases: Vec<PointAddCase>,
    notes: Vec<String>,
}

impl From<&CaseCorpusDocument> for HumanCaseCorpusDocument {
    fn from(value: &CaseCorpusDocument) -> Self {
        Self {
            schema: value.schema.clone(),
            curve: value.curve.clone(),
            field_modulus_hex: value.field_modulus_hex.clone(),
            curve_b: value.curve_b,
            seed_sha256: value.seed_sha256.clone(),
            seed_hash_scheme: value.seed_hash_scheme.clone(),
            case_start_index: value.case_start_index,
            case_count: value.case_count,
            category_counts: value.category_counts.clone(),
            cases: value.cases.clone(),
            notes: value.notes.clone(),
        }
    }
}

impl From<HumanCaseCorpusDocument> for CaseCorpusDocument {
    fn from(value: HumanCaseCorpusDocument) -> Self {
        Self {
            schema: value.schema,
            curve: value.curve,
            field_modulus_hex: value.field_modulus_hex,
            curve_b: value.curve_b,
            seed_sha256: value.seed_sha256,
            seed_hash_scheme: value.seed_hash_scheme,
            case_start_index: value.case_start_index,
            case_count: value.case_count,
            category_counts: value.category_counts,
            cases: value.cases,
            notes: value.notes,
        }
    }
}

impl From<&CaseCorpusDocument> for BinaryCaseCorpusDocument {
    fn from(value: &CaseCorpusDocument) -> Self {
        Self {
            schema: value.schema.clone(),
            curve: value.curve.clone(),
            field_modulus_hex: value.field_modulus_hex.clone(),
            curve_b: value.curve_b,
            seed_sha256: value.seed_sha256.clone(),
            seed_hash_scheme: value.seed_hash_scheme.clone(),
            case_start_index: value.case_start_index,
            case_count: value.case_count,
            category_counts: value.category_counts.clone(),
            cases: value.cases.clone(),
            notes: value.notes.clone(),
        }
    }
}

impl From<BinaryCaseCorpusDocument> for CaseCorpusDocument {
    fn from(value: BinaryCaseCorpusDocument) -> Self {
        Self {
            schema: value.schema,
            curve: value.curve,
            field_modulus_hex: value.field_modulus_hex,
            curve_b: value.curve_b,
            seed_sha256: value.seed_sha256,
            seed_hash_scheme: value.seed_hash_scheme,
            case_start_index: value.case_start_index,
            case_count: value.case_count,
            category_counts: value.category_counts,
            cases: value.cases,
            notes: value.notes,
        }
    }
}

impl Serialize for CaseCorpusDocument {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if serializer.is_human_readable() {
            HumanCaseCorpusDocument::from(self).serialize(serializer)
        } else {
            BinaryCaseCorpusDocument::from(self).serialize(serializer)
        }
    }
}

impl<'de> Deserialize<'de> for CaseCorpusDocument {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        if deserializer.is_human_readable() {
            HumanCaseCorpusDocument::deserialize(deserializer).map(Into::into)
        } else {
            BinaryCaseCorpusDocument::deserialize(deserializer).map(Into::into)
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PointAddCase {
    pub case_id: String,
    pub category: String,
    pub accumulator: Option<AffineEncoding>,
    pub lookup: Option<AffineEncoding>,
    pub expected: Option<AffineEncoding>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AffineEncoding {
    pub x_hex: String,
    pub y_hex: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PreparedClaimSummary {
    pub field_bits: u32,
    pub leaf_call_count_total: u32,
    pub expected_full_oracle_non_clifford: u64,
    pub expected_total_logical_qubits: u64,
    pub expected_case_count: u32,
    pub non_clifford_formula: NonCliffordFormula,
    pub logical_qubit_formula: LogicalQubitFormula,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PreparedFamilySummary {
    pub name: String,
    pub arithmetic_leaf_non_clifford: u64,
    pub direct_seed_non_clifford: u64,
    pub per_leaf_lookup_non_clifford: u64,
    pub full_oracle_non_clifford: u64,
    pub arithmetic_slot_count: u32,
    pub control_slot_count: u32,
    pub borrowed_interface_qubits: u32,
    pub lookup_workspace_qubits: u32,
    pub live_phase_bits: u32,
    pub total_logical_qubits: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PreparedCaseCorpus {
    pub field_modulus_hex: String,
    pub case_start_index: Option<u32>,
    pub case_count: u32,
    pub cases: Vec<PointAddCase>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublicValues {
    pub schema: String,
    pub document_digest_scheme: String,
    pub selected_family_name: String,
    pub claim_sha256: String,
    pub leaf_sha256: String,
    pub family_sha256: String,
    pub case_corpus_sha256: String,
    pub resource_certificate_sha256: String,
    pub expected_full_oracle_non_clifford: u64,
    pub expected_total_logical_qubits: u64,
    pub case_count: u32,
    pub passed_case_count: u32,
}

type PointAffine = Option<(BigUint, BigUint)>;
type PointProj = (BigUint, BigUint, BigUint);
type RegisterId = usize;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CompiledLeaf {
    register_count: usize,
    input_qx: RegisterId,
    input_qy: RegisterId,
    input_qz: RegisterId,
    input_k: RegisterId,
    input_lookup_x: RegisterId,
    input_lookup_y: RegisterId,
    input_lookup_meta: RegisterId,
    output_qx: RegisterId,
    output_qy: RegisterId,
    output_qz: RegisterId,
    skip_on_lookup_infinity: bool,
    instructions: Vec<CompiledInstruction>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CompiledInstruction {
    Copy {
        dst: RegisterId,
        src: RegisterId,
    },
    BoolFromFlag {
        dst: RegisterId,
        flags: RegisterId,
        bit: u64,
    },
    ClearBoolFromFlag {
        dst: RegisterId,
        flags: RegisterId,
        bit: u64,
    },
    FieldMul {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldMulLookupX {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldMulLookupY {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldMulLookupSum {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldAdd {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldSub {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldSubSum {
        dst: RegisterId,
        minuend: RegisterId,
        subtrahend_a: RegisterId,
        subtrahend_b: RegisterId,
    },
    FieldTriple {
        dst: RegisterId,
        src: RegisterId,
    },
    MulConst {
        dst: RegisterId,
        src: RegisterId,
        constant: u64,
    },
    SelectFieldIfFlag {
        dst: RegisterId,
        flag: RegisterId,
        when_nonzero: RegisterId,
        when_zero: RegisterId,
    },
    CompleteA0StreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        c: RegisterId,
        h: RegisterId,
        a: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0FullyStreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        h: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0AllStreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0ReusableChunkTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        y: RegisterId,
        z: RegisterId,
        scratch: RegisterId,
        chunk_bits: u32,
        chunk_count: u32,
        b3: u64,
    },
}

#[derive(Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum HumanCompiledInstruction {
    Copy {
        dst: RegisterId,
        src: RegisterId,
    },
    BoolFromFlag {
        dst: RegisterId,
        flags: RegisterId,
        bit: u64,
    },
    ClearBoolFromFlag {
        dst: RegisterId,
        flags: RegisterId,
        bit: u64,
    },
    FieldMul {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldMulLookupX {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldMulLookupY {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldMulLookupSum {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldAdd {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldSub {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldSubSum {
        dst: RegisterId,
        minuend: RegisterId,
        subtrahend_a: RegisterId,
        subtrahend_b: RegisterId,
    },
    FieldTriple {
        dst: RegisterId,
        src: RegisterId,
    },
    MulConst {
        dst: RegisterId,
        src: RegisterId,
        constant: u64,
    },
    SelectFieldIfFlag {
        dst: RegisterId,
        flag: RegisterId,
        when_nonzero: RegisterId,
        when_zero: RegisterId,
    },
    CompleteA0StreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        c: RegisterId,
        h: RegisterId,
        a: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0FullyStreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        h: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0AllStreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0ReusableChunkTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        y: RegisterId,
        z: RegisterId,
        scratch: RegisterId,
        chunk_bits: u32,
        chunk_count: u32,
        b3: u64,
    },
}

#[derive(Serialize, Deserialize)]
enum BinaryCompiledInstruction {
    Copy {
        dst: RegisterId,
        src: RegisterId,
    },
    BoolFromFlag {
        dst: RegisterId,
        flags: RegisterId,
        bit: u64,
    },
    ClearBoolFromFlag {
        dst: RegisterId,
        flags: RegisterId,
        bit: u64,
    },
    FieldMul {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldMulLookupX {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldMulLookupY {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldMulLookupSum {
        dst: RegisterId,
        src: RegisterId,
    },
    FieldAdd {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldSub {
        dst: RegisterId,
        left: RegisterId,
        right: RegisterId,
    },
    FieldSubSum {
        dst: RegisterId,
        minuend: RegisterId,
        subtrahend_a: RegisterId,
        subtrahend_b: RegisterId,
    },
    FieldTriple {
        dst: RegisterId,
        src: RegisterId,
    },
    MulConst {
        dst: RegisterId,
        src: RegisterId,
        constant: u64,
    },
    SelectFieldIfFlag {
        dst: RegisterId,
        flag: RegisterId,
        when_nonzero: RegisterId,
        when_zero: RegisterId,
    },
    CompleteA0StreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        c: RegisterId,
        h: RegisterId,
        a: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0FullyStreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        h: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0AllStreamedTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        y: RegisterId,
        z: RegisterId,
    },
    CompleteA0ReusableChunkTail {
        out_x: RegisterId,
        out_y: RegisterId,
        out_z: RegisterId,
        x: RegisterId,
        y: RegisterId,
        z: RegisterId,
        scratch: RegisterId,
        chunk_bits: u32,
        chunk_count: u32,
        b3: u64,
    },
}

impl From<&CompiledInstruction> for HumanCompiledInstruction {
    fn from(value: &CompiledInstruction) -> Self {
        match value {
            CompiledInstruction::Copy { dst, src } => Self::Copy {
                dst: *dst,
                src: *src,
            },
            CompiledInstruction::BoolFromFlag { dst, flags, bit } => Self::BoolFromFlag {
                dst: *dst,
                flags: *flags,
                bit: *bit,
            },
            CompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => Self::ClearBoolFromFlag {
                dst: *dst,
                flags: *flags,
                bit: *bit,
            },
            CompiledInstruction::FieldMul { dst, left, right } => Self::FieldMul {
                dst: *dst,
                left: *left,
                right: *right,
            },
            CompiledInstruction::FieldMulLookupX { dst, src } => Self::FieldMulLookupX {
                dst: *dst,
                src: *src,
            },
            CompiledInstruction::FieldMulLookupY { dst, src } => Self::FieldMulLookupY {
                dst: *dst,
                src: *src,
            },
            CompiledInstruction::FieldMulLookupSum { dst, src } => Self::FieldMulLookupSum {
                dst: *dst,
                src: *src,
            },
            CompiledInstruction::FieldAdd { dst, left, right } => Self::FieldAdd {
                dst: *dst,
                left: *left,
                right: *right,
            },
            CompiledInstruction::FieldSub { dst, left, right } => Self::FieldSub {
                dst: *dst,
                left: *left,
                right: *right,
            },
            CompiledInstruction::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            } => Self::FieldSubSum {
                dst: *dst,
                minuend: *minuend,
                subtrahend_a: *subtrahend_a,
                subtrahend_b: *subtrahend_b,
            },
            CompiledInstruction::FieldTriple { dst, src } => Self::FieldTriple {
                dst: *dst,
                src: *src,
            },
            CompiledInstruction::MulConst { dst, src, constant } => Self::MulConst {
                dst: *dst,
                src: *src,
                constant: *constant,
            },
            CompiledInstruction::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            } => Self::SelectFieldIfFlag {
                dst: *dst,
                flag: *flag,
                when_nonzero: *when_nonzero,
                when_zero: *when_zero,
            },
            CompiledInstruction::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            } => Self::CompleteA0StreamedTail {
                out_x: *out_x,
                out_y: *out_y,
                out_z: *out_z,
                c: *c,
                h: *h,
                a: *a,
                y: *y,
                z: *z,
            },
            CompiledInstruction::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            } => Self::CompleteA0FullyStreamedTail {
                out_x: *out_x,
                out_y: *out_y,
                out_z: *out_z,
                x: *x,
                h: *h,
                y: *y,
                z: *z,
            },
            CompiledInstruction::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            } => Self::CompleteA0AllStreamedTail {
                out_x: *out_x,
                out_y: *out_y,
                out_z: *out_z,
                x: *x,
                y: *y,
                z: *z,
            },
            CompiledInstruction::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            } => Self::CompleteA0ReusableChunkTail {
                out_x: *out_x,
                out_y: *out_y,
                out_z: *out_z,
                x: *x,
                y: *y,
                z: *z,
                scratch: *scratch,
                chunk_bits: *chunk_bits,
                chunk_count: *chunk_count,
                b3: *b3,
            },
        }
    }
}

impl From<HumanCompiledInstruction> for CompiledInstruction {
    fn from(value: HumanCompiledInstruction) -> Self {
        match value {
            HumanCompiledInstruction::Copy { dst, src } => Self::Copy { dst, src },
            HumanCompiledInstruction::BoolFromFlag { dst, flags, bit } => {
                Self::BoolFromFlag { dst, flags, bit }
            }
            HumanCompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                Self::ClearBoolFromFlag { dst, flags, bit }
            }
            HumanCompiledInstruction::FieldMul { dst, left, right } => {
                Self::FieldMul { dst, left, right }
            }
            HumanCompiledInstruction::FieldMulLookupX { dst, src } => {
                Self::FieldMulLookupX { dst, src }
            }
            HumanCompiledInstruction::FieldMulLookupY { dst, src } => {
                Self::FieldMulLookupY { dst, src }
            }
            HumanCompiledInstruction::FieldMulLookupSum { dst, src } => {
                Self::FieldMulLookupSum { dst, src }
            }
            HumanCompiledInstruction::FieldAdd { dst, left, right } => {
                Self::FieldAdd { dst, left, right }
            }
            HumanCompiledInstruction::FieldSub { dst, left, right } => {
                Self::FieldSub { dst, left, right }
            }
            HumanCompiledInstruction::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            } => Self::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            },
            HumanCompiledInstruction::FieldTriple { dst, src } => Self::FieldTriple { dst, src },
            HumanCompiledInstruction::MulConst { dst, src, constant } => {
                Self::MulConst { dst, src, constant }
            }
            HumanCompiledInstruction::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            } => Self::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            },
            HumanCompiledInstruction::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            } => Self::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            },
            HumanCompiledInstruction::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            } => Self::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            },
            HumanCompiledInstruction::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            } => Self::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            },
            HumanCompiledInstruction::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            } => Self::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            },
        }
    }
}

impl From<&CompiledInstruction> for BinaryCompiledInstruction {
    fn from(value: &CompiledInstruction) -> Self {
        match HumanCompiledInstruction::from(value) {
            HumanCompiledInstruction::Copy { dst, src } => Self::Copy { dst, src },
            HumanCompiledInstruction::BoolFromFlag { dst, flags, bit } => {
                Self::BoolFromFlag { dst, flags, bit }
            }
            HumanCompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                Self::ClearBoolFromFlag { dst, flags, bit }
            }
            HumanCompiledInstruction::FieldMul { dst, left, right } => {
                Self::FieldMul { dst, left, right }
            }
            HumanCompiledInstruction::FieldMulLookupX { dst, src } => {
                Self::FieldMulLookupX { dst, src }
            }
            HumanCompiledInstruction::FieldMulLookupY { dst, src } => {
                Self::FieldMulLookupY { dst, src }
            }
            HumanCompiledInstruction::FieldMulLookupSum { dst, src } => {
                Self::FieldMulLookupSum { dst, src }
            }
            HumanCompiledInstruction::FieldAdd { dst, left, right } => {
                Self::FieldAdd { dst, left, right }
            }
            HumanCompiledInstruction::FieldSub { dst, left, right } => {
                Self::FieldSub { dst, left, right }
            }
            HumanCompiledInstruction::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            } => Self::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            },
            HumanCompiledInstruction::FieldTriple { dst, src } => Self::FieldTriple { dst, src },
            HumanCompiledInstruction::MulConst { dst, src, constant } => {
                Self::MulConst { dst, src, constant }
            }
            HumanCompiledInstruction::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            } => Self::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            },
            HumanCompiledInstruction::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            } => Self::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            },
            HumanCompiledInstruction::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            } => Self::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            },
            HumanCompiledInstruction::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            } => Self::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            },
            HumanCompiledInstruction::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            } => Self::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            },
        }
    }
}

impl From<BinaryCompiledInstruction> for CompiledInstruction {
    fn from(value: BinaryCompiledInstruction) -> Self {
        match value {
            BinaryCompiledInstruction::Copy { dst, src } => Self::Copy { dst, src },
            BinaryCompiledInstruction::BoolFromFlag { dst, flags, bit } => {
                Self::BoolFromFlag { dst, flags, bit }
            }
            BinaryCompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                Self::ClearBoolFromFlag { dst, flags, bit }
            }
            BinaryCompiledInstruction::FieldMul { dst, left, right } => {
                Self::FieldMul { dst, left, right }
            }
            BinaryCompiledInstruction::FieldMulLookupX { dst, src } => {
                Self::FieldMulLookupX { dst, src }
            }
            BinaryCompiledInstruction::FieldMulLookupY { dst, src } => {
                Self::FieldMulLookupY { dst, src }
            }
            BinaryCompiledInstruction::FieldMulLookupSum { dst, src } => {
                Self::FieldMulLookupSum { dst, src }
            }
            BinaryCompiledInstruction::FieldAdd { dst, left, right } => {
                Self::FieldAdd { dst, left, right }
            }
            BinaryCompiledInstruction::FieldSub { dst, left, right } => {
                Self::FieldSub { dst, left, right }
            }
            BinaryCompiledInstruction::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            } => Self::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            },
            BinaryCompiledInstruction::FieldTriple { dst, src } => Self::FieldTriple { dst, src },
            BinaryCompiledInstruction::MulConst { dst, src, constant } => {
                Self::MulConst { dst, src, constant }
            }
            BinaryCompiledInstruction::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            } => Self::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            },
            BinaryCompiledInstruction::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            } => Self::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            },
            BinaryCompiledInstruction::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            } => Self::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            },
            BinaryCompiledInstruction::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            } => Self::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            },
            BinaryCompiledInstruction::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            } => Self::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            },
        }
    }
}

impl Serialize for CompiledInstruction {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if serializer.is_human_readable() {
            HumanCompiledInstruction::from(self).serialize(serializer)
        } else {
            BinaryCompiledInstruction::from(self).serialize(serializer)
        }
    }
}

impl<'de> Deserialize<'de> for CompiledInstruction {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        if deserializer.is_human_readable() {
            HumanCompiledInstruction::deserialize(deserializer).map(Into::into)
        } else {
            BinaryCompiledInstruction::deserialize(deserializer).map(Into::into)
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreparedAttestationInput {
    pub schema: String,
    pub document_digest_scheme: String,
    pub selected_family_name: String,
    pub claim_sha256: String,
    pub leaf_sha256: String,
    pub family_sha256: String,
    pub case_corpus_sha256: String,
    pub resource_certificate_sha256: String,
    pub compiler_parameters_sha256: String,
    pub claim_document: CommittedDocument<SemanticJsonPayload>,
    pub leaf_document: CommittedDocument<SemanticJsonPayload>,
    pub family_document: CommittedDocument<SemanticJsonPayload>,
    pub case_corpus_document: CommittedDocument<SemanticJsonPayload>,
    pub resource_certificate_document: CommittedDocument<SemanticJsonPayload>,
    pub compiler_parameters_document: CommittedDocument<SemanticJsonPayload>,
    pub claim_summary: PreparedClaimSummary,
    pub family_summary: PreparedFamilySummary,
    pub prepared_leaf: CompiledLeaf,
    pub proof_register_contract: SemanticJsonPayload,
    pub prepared_case_corpus: PreparedCaseCorpus,
    pub notes: Vec<String>,
}

trait SemanticHash {
    fn semantic_hash(&self, hasher: &mut Sha256);
}

#[derive(Debug, Clone)]
struct CompiledCase {
    case_id: String,
    accumulator: PointAffine,
    lookup: PointAffine,
    expected: PointAffine,
}

fn hash_len_prefixed_bytes(hasher: &mut Sha256, tag: u8, bytes: &[u8]) {
    hasher.update([tag]);
    hasher.update((bytes.len() as u64).to_be_bytes());
    hasher.update(bytes);
}

fn semantic_hash_object_start(hasher: &mut Sha256, field_count: usize) {
    hasher.update([b'o']);
    hasher.update((field_count as u64).to_be_bytes());
}

fn semantic_hash_array_start(hasher: &mut Sha256, item_count: usize) {
    hasher.update([b'l']);
    hasher.update((item_count as u64).to_be_bytes());
}

fn semantic_hash_field<T: SemanticHash>(hasher: &mut Sha256, key: &str, value: &T) {
    hash_len_prefixed_bytes(hasher, b's', key.as_bytes());
    value.semantic_hash(hasher);
}

impl SemanticHash for str {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        hash_len_prefixed_bytes(hasher, b's', self.as_bytes());
    }
}

impl SemanticHash for String {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        self.as_str().semantic_hash(hasher);
    }
}

impl SemanticHash for u32 {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        self.to_string().semantic_hash_integer(hasher);
    }
}

impl SemanticHash for u64 {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        self.to_string().semantic_hash_integer(hasher);
    }
}

trait SemanticHashInteger {
    fn semantic_hash_integer(&self, hasher: &mut Sha256);
}

impl SemanticHashInteger for String {
    fn semantic_hash_integer(&self, hasher: &mut Sha256) {
        hash_len_prefixed_bytes(hasher, b'i', self.as_bytes());
    }
}

impl<T: SemanticHash> SemanticHash for Vec<T> {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_array_start(hasher, self.len());
        for item in self {
            item.semantic_hash(hasher);
        }
    }
}

impl<T: SemanticHash> SemanticHash for Option<T> {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        match self {
            Some(value) => value.semantic_hash(hasher),
            None => hasher.update([b'n']),
        }
    }
}

impl SemanticHash for SemanticJsonPayload {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        self.0.semantic_hash(hasher);
    }
}

impl SemanticHash for Value {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        match self {
            Value::Null => hasher.update([b'n']),
            Value::Bool(true) => hasher.update([b't']),
            Value::Bool(false) => hasher.update([b'f']),
            Value::Number(number) => number.to_string().semantic_hash_integer(hasher),
            Value::String(value) => value.semantic_hash(hasher),
            Value::Array(values) => values.semantic_hash(hasher),
            Value::Object(object) => {
                let mut keys: Vec<&String> = object.keys().collect();
                keys.sort();
                semantic_hash_object_start(hasher, keys.len());
                for key in keys {
                    semantic_hash_field(
                        hasher,
                        key,
                        object.get(key).expect("missing sorted object key"),
                    );
                }
            }
        }
    }
}

impl SemanticHash for InstructionDestination {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        match self {
            InstructionDestination::Register(register) => register.semantic_hash(hasher),
            InstructionDestination::Registers(registers) => registers.semantic_hash(hasher),
        }
    }
}

impl SemanticHash for InstructionSource {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        match self {
            InstructionSource::Register(register) => register.semantic_hash(hasher),
            InstructionSource::Pair(pair) => {
                semantic_hash_array_start(hasher, pair.len());
                for item in pair {
                    item.semantic_hash(hasher);
                }
            }
            InstructionSource::Triple(triple) => {
                semantic_hash_array_start(hasher, triple.len());
                for item in triple {
                    item.semantic_hash(hasher);
                }
            }
            InstructionSource::StreamedTail { c, h, a, y, z } => {
                semantic_hash_object_start(hasher, 5);
                semantic_hash_field(hasher, "a", a);
                semantic_hash_field(hasher, "c", c);
                semantic_hash_field(hasher, "h", h);
                semantic_hash_field(hasher, "y", y);
                semantic_hash_field(hasher, "z", z);
            }
            InstructionSource::FullyStreamedTail { x, h, y, z } => {
                semantic_hash_object_start(hasher, 4);
                semantic_hash_field(hasher, "h", h);
                semantic_hash_field(hasher, "x", x);
                semantic_hash_field(hasher, "y", y);
                semantic_hash_field(hasher, "z", z);
            }
            InstructionSource::AllStreamedTail { x, y, z } => {
                semantic_hash_object_start(hasher, 3);
                semantic_hash_field(hasher, "x", x);
                semantic_hash_field(hasher, "y", y);
                semantic_hash_field(hasher, "z", z);
            }
            InstructionSource::ReusableChunkTail { x, y, z, scratch } => {
                semantic_hash_object_start(hasher, 4);
                semantic_hash_field(hasher, "scratch", scratch);
                semantic_hash_field(hasher, "x", x);
                semantic_hash_field(hasher, "y", y);
                semantic_hash_field(hasher, "z", z);
            }
            InstructionSource::FlagBit { flags, bit } => {
                semantic_hash_object_start(hasher, 2);
                semantic_hash_field(hasher, "bit", bit);
                semantic_hash_field(hasher, "flags", flags);
            }
            InstructionSource::Lookup { table, key } => {
                semantic_hash_object_start(hasher, 2);
                semantic_hash_field(hasher, "key", key);
                semantic_hash_field(hasher, "table", table);
            }
        }
    }
}

impl SemanticHash for NonCliffordFormula {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 7);
        semantic_hash_field(hasher, "arithmetic_component", &self.arithmetic_component);
        semantic_hash_field(
            hasher,
            "arithmetic_leaf_non_clifford",
            &self.arithmetic_leaf_non_clifford,
        );
        semantic_hash_field(
            hasher,
            "direct_seed_non_clifford",
            &self.direct_seed_non_clifford,
        );
        semantic_hash_field(hasher, "leaf_call_count_total", &self.leaf_call_count_total);
        semantic_hash_field(hasher, "lookup_component", &self.lookup_component);
        semantic_hash_field(
            hasher,
            "per_leaf_lookup_non_clifford",
            &self.per_leaf_lookup_non_clifford,
        );
        semantic_hash_field(hasher, "reconstructed_total", &self.reconstructed_total);
    }
}

impl SemanticHash for LogicalQubitFormula {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 8);
        semantic_hash_field(hasher, "arithmetic_component", &self.arithmetic_component);
        semantic_hash_field(hasher, "arithmetic_slot_count", &self.arithmetic_slot_count);
        semantic_hash_field(
            hasher,
            "borrowed_interface_qubits",
            &self.borrowed_interface_qubits,
        );
        semantic_hash_field(hasher, "control_slot_count", &self.control_slot_count);
        semantic_hash_field(hasher, "field_bits", &self.field_bits);
        semantic_hash_field(hasher, "live_phase_bits", &self.live_phase_bits);
        semantic_hash_field(
            hasher,
            "lookup_workspace_qubits",
            &self.lookup_workspace_qubits,
        );
        semantic_hash_field(hasher, "reconstructed_total", &self.reconstructed_total);
    }
}

impl SemanticHash for ClaimDocument {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 11);
        semantic_hash_field(hasher, "expected_case_count", &self.expected_case_count);
        semantic_hash_field(
            hasher,
            "expected_full_oracle_non_clifford",
            &self.expected_full_oracle_non_clifford,
        );
        semantic_hash_field(
            hasher,
            "expected_total_logical_qubits",
            &self.expected_total_logical_qubits,
        );
        semantic_hash_field(hasher, "field_bits", &self.field_bits);
        semantic_hash_field(hasher, "leaf_call_count_total", &self.leaf_call_count_total);
        semantic_hash_field(hasher, "logical_qubit_formula", &self.logical_qubit_formula);
        semantic_hash_field(hasher, "non_clifford_formula", &self.non_clifford_formula);
        semantic_hash_field(hasher, "notes", &self.notes);
        semantic_hash_field(hasher, "schema", &self.schema);
        semantic_hash_field(hasher, "selected_family_alias", &self.selected_family_alias);
        semantic_hash_field(hasher, "selected_family_name", &self.selected_family_name);
    }
}

impl SemanticHash for Instruction {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        let field_count = 2
            + usize::from(self.comment.is_some())
            + usize::from(self.const_value.is_some())
            + usize::from(self.chunk_bits.is_some())
            + usize::from(self.chunk_count.is_some())
            + usize::from(self.b3.is_some())
            + usize::from(self.dst.is_some())
            + usize::from(self.flag.is_some())
            + usize::from(self.src.is_some());
        semantic_hash_object_start(hasher, field_count);
        if let Some(comment) = &self.comment {
            semantic_hash_field(hasher, "comment", comment);
        }
        if let Some(const_value) = &self.const_value {
            semantic_hash_field(hasher, "const", const_value);
        }
        if let Some(chunk_bits) = &self.chunk_bits {
            semantic_hash_field(hasher, "chunk_bits", chunk_bits);
        }
        if let Some(chunk_count) = &self.chunk_count {
            semantic_hash_field(hasher, "chunk_count", chunk_count);
        }
        if let Some(b3) = &self.b3 {
            semantic_hash_field(hasher, "b3", b3);
        }
        if let Some(dst) = &self.dst {
            semantic_hash_field(hasher, "dst", dst);
        }
        if let Some(flag) = &self.flag {
            semantic_hash_field(hasher, "flag", flag);
        }
        semantic_hash_field(hasher, "op", &self.op);
        semantic_hash_field(hasher, "pc", &self.pc);
        if let Some(src) = &self.src {
            semantic_hash_field(hasher, "src", src);
        }
    }
}

impl SemanticHash for LeafDocument {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        let field_count = 11 + usize::from(self.lookup_infinity_policy.is_some());
        semantic_hash_object_start(hasher, field_count);
        semantic_hash_field(hasher, "arithmetic_slots", &self.arithmetic_slots);
        semantic_hash_field(hasher, "b3", &self.b3);
        semantic_hash_field(hasher, "curve", &self.curve);
        semantic_hash_field(hasher, "curve_b", &self.curve_b);
        semantic_hash_field(hasher, "field_modulus_hex", &self.field_modulus_hex);
        semantic_hash_field(hasher, "instructions", &self.instructions);
        semantic_hash_field(hasher, "interface_wires", &self.interface_wires);
        if let Some(lookup_infinity_policy) = &self.lookup_infinity_policy {
            semantic_hash_field(hasher, "lookup_infinity_policy", lookup_infinity_policy);
        }
        semantic_hash_field(
            hasher,
            "lookup_interface_slots",
            &self.lookup_interface_slots,
        );
        semantic_hash_field(hasher, "notes", &self.notes);
        semantic_hash_field(hasher, "schema", &self.schema);
        semantic_hash_field(hasher, "variant", &self.variant);
    }
}

impl SemanticHash for FamilyDocument {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 23);
        semantic_hash_field(
            hasher,
            "arithmetic_kernel_family",
            &self.arithmetic_kernel_family,
        );
        semantic_hash_field(
            hasher,
            "arithmetic_leaf_non_clifford",
            &self.arithmetic_leaf_non_clifford,
        );
        semantic_hash_field(hasher, "arithmetic_slot_count", &self.arithmetic_slot_count);
        semantic_hash_field(
            hasher,
            "borrowed_interface_qubits",
            &self.borrowed_interface_qubits,
        );
        semantic_hash_field(hasher, "control_slot_count", &self.control_slot_count);
        semantic_hash_field(
            hasher,
            "direct_seed_non_clifford",
            &self.direct_seed_non_clifford,
        );
        semantic_hash_field(
            hasher,
            "full_oracle_non_clifford",
            &self.full_oracle_non_clifford,
        );
        semantic_hash_field(hasher, "gate_set", &self.gate_set);
        semantic_hash_field(hasher, "live_phase_bits", &self.live_phase_bits);
        semantic_hash_field(hasher, "lookup_family", &self.lookup_family);
        semantic_hash_field(
            hasher,
            "lookup_workspace_qubits",
            &self.lookup_workspace_qubits,
        );
        semantic_hash_field(hasher, "name", &self.name);
        semantic_hash_field(hasher, "notes", &self.notes);
        semantic_hash_field(
            hasher,
            "per_leaf_lookup_non_clifford",
            &self.per_leaf_lookup_non_clifford,
        );
        semantic_hash_field(hasher, "phase_shell", &self.phase_shell);
        semantic_hash_field(hasher, "phase_shell_hadamards", &self.phase_shell_hadamards);
        semantic_hash_field(
            hasher,
            "phase_shell_measurements",
            &self.phase_shell_measurements,
        );
        semantic_hash_field(
            hasher,
            "phase_shell_rotation_depth",
            &self.phase_shell_rotation_depth,
        );
        semantic_hash_field(hasher, "phase_shell_rotations", &self.phase_shell_rotations);
        semantic_hash_field(
            hasher,
            "slot_allocation_family",
            &self.slot_allocation_family,
        );
        semantic_hash_field(hasher, "summary", &self.summary);
        semantic_hash_field(hasher, "total_logical_qubits", &self.total_logical_qubits);
        semantic_hash_field(hasher, "total_measurements", &self.total_measurements);
    }
}

impl SemanticHash for AffineEncoding {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 2);
        semantic_hash_field(hasher, "x_hex", &self.x_hex);
        semantic_hash_field(hasher, "y_hex", &self.y_hex);
    }
}

impl SemanticHash for PointAddCase {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 5);
        semantic_hash_field(hasher, "accumulator", &self.accumulator);
        semantic_hash_field(hasher, "case_id", &self.case_id);
        semantic_hash_field(hasher, "category", &self.category);
        semantic_hash_field(hasher, "expected", &self.expected);
        semantic_hash_field(hasher, "lookup", &self.lookup);
    }
}

impl SemanticHash for BTreeMap<String, u32> {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, self.len());
        for (key, value) in self {
            semantic_hash_field(hasher, key, value);
        }
    }
}

impl SemanticHash for CaseCorpusDocument {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        let field_count = 9
            + usize::from(self.case_start_index.is_some())
            + usize::from(self.seed_hash_scheme.is_some());
        semantic_hash_object_start(hasher, field_count);
        semantic_hash_field(hasher, "case_count", &self.case_count);
        if let Some(case_start_index) = &self.case_start_index {
            semantic_hash_field(hasher, "case_start_index", case_start_index);
        }
        semantic_hash_field(hasher, "cases", &self.cases);
        semantic_hash_field(hasher, "category_counts", &self.category_counts);
        semantic_hash_field(hasher, "curve", &self.curve);
        semantic_hash_field(hasher, "curve_b", &self.curve_b);
        semantic_hash_field(hasher, "field_modulus_hex", &self.field_modulus_hex);
        semantic_hash_field(hasher, "notes", &self.notes);
        semantic_hash_field(hasher, "schema", &self.schema);
        if let Some(seed_hash_scheme) = &self.seed_hash_scheme {
            semantic_hash_field(hasher, "seed_hash_scheme", seed_hash_scheme);
        }
        semantic_hash_field(hasher, "seed_sha256", &self.seed_sha256);
    }
}

fn semantic_payload_sha256<T: SemanticHash>(document_type: &str, payload: &T) -> String {
    let mut hasher = Sha256::new();
    hasher.update(DIGEST_SCHEME.as_bytes());
    hasher.update([0u8]);
    hasher.update(document_type.as_bytes());
    hasher.update([0u8]);
    payload.semantic_hash(&mut hasher);
    hex::encode(hasher.finalize())
}

fn parse_hex_uint(value: &str) -> BigUint {
    let trimmed = value.strip_prefix("0x").unwrap_or(value);
    BigUint::from_str_radix(trimmed, 16).expect("invalid hex integer")
}

fn decode_point(point: &Option<AffineEncoding>) -> PointAffine {
    point
        .as_ref()
        .map(|value| (parse_hex_uint(&value.x_hex), parse_hex_uint(&value.y_hex)))
}

fn mod_sub(lhs: &BigUint, rhs: &BigUint, modulus: &BigUint) -> BigUint {
    if lhs >= rhs {
        (lhs - rhs) % modulus
    } else {
        (modulus - ((rhs - lhs) % modulus)) % modulus
    }
}

fn affine_to_proj(point: PointAffine) -> PointProj {
    match point {
        Some((x, y)) => (x, y, BigUint::one()),
        None => (BigUint::zero(), BigUint::one(), BigUint::zero()),
    }
}

fn add_affine_projective(lhs: PointAffine, rhs: PointAffine, modulus: &BigUint) -> PointProj {
    match (lhs, rhs) {
        (None, other) => affine_to_proj(other),
        (other, None) => affine_to_proj(other),
        (Some((x1, y1)), Some((x2, y2))) => {
            if x1 == x2 {
                if (&y1 + &y2) % modulus == BigUint::zero() {
                    return affine_to_proj(None);
                }
                let numerator = (BigUint::from(3u32) * &x1 * &x1) % modulus;
                let denominator = (BigUint::from(2u32) * &y1) % modulus;
                if denominator.is_zero() {
                    return affine_to_proj(None);
                }
                let denominator_sq = (&denominator * &denominator) % modulus;
                let x3_numer = mod_sub(
                    &((&numerator * &numerator) % modulus),
                    &((BigUint::from(2u32) * &x1 % modulus) * &denominator_sq % modulus),
                    modulus,
                );
                let denominator_cu = (&denominator_sq * &denominator) % modulus;
                let y3 = mod_sub(
                    &((&numerator
                        * mod_sub(&((&x1 * &denominator_sq) % modulus), &x3_numer, modulus))
                        % modulus),
                    &((&y1 * &denominator_cu) % modulus),
                    modulus,
                );
                ((&denominator * &x3_numer) % modulus, y3, denominator_cu)
            } else {
                let delta_y = mod_sub(&y2, &y1, modulus);
                let delta_x = mod_sub(&x2, &x1, modulus);
                let delta_x_sq = (&delta_x * &delta_x) % modulus;
                let x3_numer = mod_sub(
                    &((&delta_y * &delta_y) % modulus),
                    &((&delta_x_sq * ((&x1 + &x2) % modulus)) % modulus),
                    modulus,
                );
                let delta_x_cu = (&delta_x_sq * &delta_x) % modulus;
                let y3 = mod_sub(
                    &((&delta_y * mod_sub(&((&x1 * &delta_x_sq) % modulus), &x3_numer, modulus))
                        % modulus),
                    &((&y1 * &delta_x_cu) % modulus),
                    modulus,
                );
                ((&delta_x * &x3_numer) % modulus, y3, delta_x_cu)
            }
        }
    }
}

fn source_as_pair(source: &InstructionSource) -> (&str, &str) {
    match source {
        InstructionSource::Pair([first, second]) => (first, second),
        _ => panic!("expected pair source"),
    }
}

fn source_as_triple(source: &InstructionSource) -> (&str, &str, &str) {
    match source {
        InstructionSource::Triple([first, second, third]) => (first, second, third),
        _ => panic!("expected triple source"),
    }
}

fn source_as_register(source: &InstructionSource) -> &str {
    match source {
        InstructionSource::Register(register) => register,
        _ => panic!("expected register source"),
    }
}

fn flag_bit(registers: &[BigUint], flags: RegisterId, bit: u64) -> u64 {
    let flag_value = registers[flags]
        .to_u64()
        .expect("flag register does not fit in u64");
    (flag_value >> bit) & 1
}

fn source_as_flag(source: &InstructionSource) -> (&str, u64) {
    match source {
        InstructionSource::FlagBit { flags, bit } => (flags, *bit),
        _ => panic!("expected flag source"),
    }
}

fn source_as_lookup(source: &InstructionSource) -> (&str, &str) {
    match source {
        InstructionSource::Lookup { table, key } => (table, key),
        _ => panic!("expected lookup source"),
    }
}

fn source_as_streamed_tail(source: &InstructionSource) -> (&str, &str, &str, &str, &str) {
    match source {
        InstructionSource::StreamedTail { c, h, a, y, z } => (c, h, a, y, z),
        _ => panic!("expected streamed tail source"),
    }
}

fn source_as_fully_streamed_tail(source: &InstructionSource) -> (&str, &str, &str, &str) {
    match source {
        InstructionSource::FullyStreamedTail { x, h, y, z } => (x, h, y, z),
        _ => panic!("expected fully streamed tail source"),
    }
}

fn source_as_all_streamed_tail(source: &InstructionSource) -> (&str, &str, &str) {
    match source {
        InstructionSource::AllStreamedTail { x, y, z } => (x, y, z),
        _ => panic!("expected all-streamed tail source"),
    }
}

fn source_as_reusable_chunk_tail(source: &InstructionSource) -> (&str, &str, &str, &str) {
    match source {
        InstructionSource::ReusableChunkTail { x, y, z, scratch } => (x, y, z, scratch),
        _ => panic!("expected reusable-chunk tail source"),
    }
}

fn destination_as_register(destination: &InstructionDestination) -> &str {
    match destination {
        InstructionDestination::Register(register) => register,
        _ => panic!("expected register destination"),
    }
}

fn destination_as_registers(destination: &InstructionDestination) -> &[String] {
    match destination {
        InstructionDestination::Registers(registers) => registers,
        _ => panic!("expected register-list destination"),
    }
}

fn register_id(register_ids: &BTreeMap<String, RegisterId>, name: &str) -> RegisterId {
    *register_ids
        .get(name)
        .unwrap_or_else(|| panic!("missing compiled register: {name}"))
}

fn ensure_defined_register(
    register_ids: &mut BTreeMap<String, RegisterId>,
    defined: &BTreeSet<String>,
    name: &str,
    context: &str,
) -> RegisterId {
    assert!(defined.contains(name), "missing {context} register: {name}");
    register_id(register_ids, name)
}

fn compile_leaf(leaf: &LeafDocument) -> CompiledLeaf {
    let mut register_ids = BTreeMap::new();
    let mut initial_registers = Vec::new();
    initial_registers.extend(leaf.interface_wires.iter().cloned());
    initial_registers.push("lookup_x".to_owned());
    initial_registers.push("lookup_y".to_owned());
    initial_registers.extend(leaf.lookup_interface_slots.iter().cloned());
    initial_registers.extend(leaf.arithmetic_slots.iter().cloned());
    for name in initial_registers {
        if !register_ids.contains_key(&name) {
            let next_id = register_ids.len();
            register_ids.insert(name, next_id);
        }
    }
    let mut defined = BTreeSet::new();
    defined.extend(leaf.interface_wires.iter().cloned());
    defined.insert("lookup_x".to_owned());
    defined.insert("lookup_y".to_owned());
    defined.extend(leaf.lookup_interface_slots.iter().cloned());
    let mut sorted_instructions = leaf.instructions.clone();
    sorted_instructions.sort_by_key(|instruction| instruction.pc);
    let mut compiled = Vec::with_capacity(sorted_instructions.len());
    for instruction in sorted_instructions {
        let destination = instruction
            .dst
            .as_ref()
            .expect("missing instruction destination");
        if instruction.op == "complete_a0_streamed_tail" {
            let dst_names = destination_as_registers(destination);
            assert_eq!(dst_names.len(), 3);
            let output_ids: Vec<RegisterId> = dst_names
                .iter()
                .map(|name| {
                    if let Some(existing) = register_ids.get(name) {
                        *existing
                    } else {
                        let next_id = register_ids.len();
                        register_ids.insert(name.clone(), next_id);
                        next_id
                    }
                })
                .collect();
            let (c_name, h_name, a_name, y_name, z_name) = source_as_streamed_tail(
                instruction
                    .src
                    .as_ref()
                    .expect("missing complete_a0_streamed_tail source"),
            );
            compiled.push(CompiledInstruction::CompleteA0StreamedTail {
                out_x: output_ids[0],
                out_y: output_ids[1],
                out_z: output_ids[2],
                c: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    c_name,
                    "complete_a0_streamed_tail C",
                ),
                h: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    h_name,
                    "complete_a0_streamed_tail H",
                ),
                a: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    a_name,
                    "complete_a0_streamed_tail A",
                ),
                y: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    y_name,
                    "complete_a0_streamed_tail Y",
                ),
                z: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    z_name,
                    "complete_a0_streamed_tail Z",
                ),
            });
            defined.extend(dst_names.iter().cloned());
            continue;
        }
        if instruction.op == "complete_a0_fully_streamed_tail" {
            let dst_names = destination_as_registers(destination);
            assert_eq!(dst_names.len(), 3);
            let output_ids: Vec<RegisterId> = dst_names
                .iter()
                .map(|name| {
                    if let Some(existing) = register_ids.get(name) {
                        *existing
                    } else {
                        let next_id = register_ids.len();
                        register_ids.insert(name.clone(), next_id);
                        next_id
                    }
                })
                .collect();
            let (x_name, h_name, y_name, z_name) = source_as_fully_streamed_tail(
                instruction
                    .src
                    .as_ref()
                    .expect("missing complete_a0_fully_streamed_tail source"),
            );
            compiled.push(CompiledInstruction::CompleteA0FullyStreamedTail {
                out_x: output_ids[0],
                out_y: output_ids[1],
                out_z: output_ids[2],
                x: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    x_name,
                    "complete_a0_fully_streamed_tail X",
                ),
                h: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    h_name,
                    "complete_a0_fully_streamed_tail H",
                ),
                y: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    y_name,
                    "complete_a0_fully_streamed_tail Y",
                ),
                z: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    z_name,
                    "complete_a0_fully_streamed_tail Z",
                ),
            });
            defined.extend(dst_names.iter().cloned());
            continue;
        }
        if instruction.op == "complete_a0_all_streamed_tail" {
            let dst_names = destination_as_registers(destination);
            assert_eq!(dst_names.len(), 3);
            let output_ids: Vec<RegisterId> = dst_names
                .iter()
                .map(|name| {
                    if let Some(existing) = register_ids.get(name) {
                        *existing
                    } else {
                        let next_id = register_ids.len();
                        register_ids.insert(name.clone(), next_id);
                        next_id
                    }
                })
                .collect();
            let (x_name, y_name, z_name) = source_as_all_streamed_tail(
                instruction
                    .src
                    .as_ref()
                    .expect("missing complete_a0_all_streamed_tail source"),
            );
            compiled.push(CompiledInstruction::CompleteA0AllStreamedTail {
                out_x: output_ids[0],
                out_y: output_ids[1],
                out_z: output_ids[2],
                x: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    x_name,
                    "complete_a0_all_streamed_tail X",
                ),
                y: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    y_name,
                    "complete_a0_all_streamed_tail Y",
                ),
                z: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    z_name,
                    "complete_a0_all_streamed_tail Z",
                ),
            });
            defined.extend(dst_names.iter().cloned());
            continue;
        }
        if instruction.op == "complete_a0_reusable_chunk_tail" {
            let dst_names = destination_as_registers(destination);
            assert_eq!(dst_names.len(), 3);
            let output_ids: Vec<RegisterId> = dst_names
                .iter()
                .map(|name| {
                    if let Some(existing) = register_ids.get(name) {
                        *existing
                    } else {
                        let next_id = register_ids.len();
                        register_ids.insert(name.clone(), next_id);
                        next_id
                    }
                })
                .collect();
            let (x_name, y_name, z_name, scratch_name) = source_as_reusable_chunk_tail(
                instruction
                    .src
                    .as_ref()
                    .expect("missing complete_a0_reusable_chunk_tail source"),
            );
            let scratch = if let Some(existing) = register_ids.get(scratch_name) {
                *existing
            } else {
                let next_id = register_ids.len();
                register_ids.insert(scratch_name.to_owned(), next_id);
                next_id
            };
            compiled.push(CompiledInstruction::CompleteA0ReusableChunkTail {
                out_x: output_ids[0],
                out_y: output_ids[1],
                out_z: output_ids[2],
                x: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    x_name,
                    "complete_a0_reusable_chunk_tail X",
                ),
                y: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    y_name,
                    "complete_a0_reusable_chunk_tail Y",
                ),
                z: ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    z_name,
                    "complete_a0_reusable_chunk_tail Z",
                ),
                scratch,
                chunk_bits: instruction
                    .chunk_bits
                    .expect("missing complete_a0_reusable_chunk_tail chunk_bits"),
                chunk_count: instruction
                    .chunk_count
                    .expect("missing complete_a0_reusable_chunk_tail chunk_count"),
                b3: instruction
                    .b3
                    .expect("missing complete_a0_reusable_chunk_tail b3"),
            });
            defined.extend(dst_names.iter().cloned());
            defined.insert(scratch_name.to_owned());
            continue;
        }
        let dst_name = destination_as_register(destination);
        let dst = if let Some(existing) = register_ids.get(dst_name) {
            *existing
        } else {
            let next_id = register_ids.len();
            register_ids.insert(dst_name.to_owned(), next_id);
            next_id
        };
        let compiled_instruction = match instruction.op.as_str() {
            "load_input" => {
                let src_name = source_as_register(
                    instruction.src.as_ref().expect("missing load_input source"),
                );
                let src = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    src_name,
                    "load_input source",
                );
                CompiledInstruction::Copy { dst, src }
            }
            "lookup_affine_x" => {
                let (table, key) = source_as_lookup(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing lookup_affine_x source"),
                );
                assert_eq!(table, "T.x");
                assert_eq!(key, "k");
                CompiledInstruction::Copy {
                    dst,
                    src: register_id(&register_ids, "lookup_x"),
                }
            }
            "lookup_affine_y" => {
                let (table, key) = source_as_lookup(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing lookup_affine_y source"),
                );
                assert_eq!(table, "T.y");
                assert_eq!(key, "k");
                CompiledInstruction::Copy {
                    dst,
                    src: register_id(&register_ids, "lookup_y"),
                }
            }
            "lookup_meta" => {
                let (table, key) = source_as_lookup(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing lookup_meta source"),
                );
                assert_eq!(table, "T.meta");
                assert_eq!(key, "k");
                CompiledInstruction::Copy {
                    dst,
                    src: register_id(&register_ids, "lookup_meta"),
                }
            }
            "bool_from_flag" => {
                let (flags_name, bit) = source_as_flag(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing bool_from_flag source"),
                );
                let flags = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    flags_name,
                    "bool_from_flag flags",
                );
                CompiledInstruction::BoolFromFlag { dst, flags, bit }
            }
            "clear_bool_from_flag" => {
                assert!(
                    defined.contains(dst_name),
                    "missing clear_bool_from_flag destination register: {dst_name}"
                );
                let (flags_name, bit) = source_as_flag(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing clear_bool_from_flag source"),
                );
                let flags = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    flags_name,
                    "clear_bool_from_flag flags",
                );
                CompiledInstruction::ClearBoolFromFlag { dst, flags, bit }
            }
            "field_mul" => {
                let (left_name, right_name) =
                    source_as_pair(instruction.src.as_ref().expect("missing field_mul source"));
                let left = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    left_name,
                    "field_mul lhs",
                );
                let right = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    right_name,
                    "field_mul rhs",
                );
                CompiledInstruction::FieldMul { dst, left, right }
            }
            "field_mul_lookup_x" => {
                let src_name = source_as_register(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing field_mul_lookup_x source"),
                );
                let src = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    src_name,
                    "field_mul_lookup_x source",
                );
                CompiledInstruction::FieldMulLookupX { dst, src }
            }
            "field_mul_lookup_y" => {
                let src_name = source_as_register(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing field_mul_lookup_y source"),
                );
                let src = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    src_name,
                    "field_mul_lookup_y source",
                );
                CompiledInstruction::FieldMulLookupY { dst, src }
            }
            "field_mul_lookup_sum" => {
                let src_name = source_as_register(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing field_mul_lookup_sum source"),
                );
                let src = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    src_name,
                    "field_mul_lookup_sum source",
                );
                CompiledInstruction::FieldMulLookupSum { dst, src }
            }
            "field_add" => {
                let (left_name, right_name) =
                    source_as_pair(instruction.src.as_ref().expect("missing field_add source"));
                let left = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    left_name,
                    "field_add lhs",
                );
                let right = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    right_name,
                    "field_add rhs",
                );
                CompiledInstruction::FieldAdd { dst, left, right }
            }
            "field_sub" => {
                let (left_name, right_name) =
                    source_as_pair(instruction.src.as_ref().expect("missing field_sub source"));
                let left = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    left_name,
                    "field_sub lhs",
                );
                let right = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    right_name,
                    "field_sub rhs",
                );
                CompiledInstruction::FieldSub { dst, left, right }
            }
            "field_sub_sum" => {
                let (minuend_name, subtrahend_a_name, subtrahend_b_name) = source_as_triple(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing field_sub_sum source"),
                );
                CompiledInstruction::FieldSubSum {
                    dst,
                    minuend: ensure_defined_register(
                        &mut register_ids,
                        &defined,
                        minuend_name,
                        "field_sub_sum minuend",
                    ),
                    subtrahend_a: ensure_defined_register(
                        &mut register_ids,
                        &defined,
                        subtrahend_a_name,
                        "field_sub_sum subtrahend_a",
                    ),
                    subtrahend_b: ensure_defined_register(
                        &mut register_ids,
                        &defined,
                        subtrahend_b_name,
                        "field_sub_sum subtrahend_b",
                    ),
                }
            }
            "field_triple" => {
                let src_name = source_as_register(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing field_triple source"),
                );
                let src = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    src_name,
                    "field_triple source",
                );
                CompiledInstruction::FieldTriple { dst, src }
            }
            "mul_const" => {
                let src_name =
                    source_as_register(instruction.src.as_ref().expect("missing mul_const source"));
                let src = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    src_name,
                    "mul_const source",
                );
                let constant = instruction.const_value.expect("missing mul_const constant");
                CompiledInstruction::MulConst { dst, src, constant }
            }
            "select_field_if_flag" => {
                let flag_name = instruction
                    .flag
                    .as_ref()
                    .expect("missing select_field_if_flag flag");
                let flag = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    flag_name,
                    "select_field_if_flag flag",
                );
                let (when_nonzero_name, when_zero_name) = source_as_pair(
                    instruction
                        .src
                        .as_ref()
                        .expect("missing select_field_if_flag source"),
                );
                let when_nonzero = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    when_nonzero_name,
                    "select_field_if_flag nonzero source",
                );
                let when_zero = ensure_defined_register(
                    &mut register_ids,
                    &defined,
                    when_zero_name,
                    "select_field_if_flag zero source",
                );
                CompiledInstruction::SelectFieldIfFlag {
                    dst,
                    flag,
                    when_nonzero,
                    when_zero,
                }
            }
            other => panic!("unsupported instruction opcode: {other}"),
        };
        compiled.push(compiled_instruction);
        defined.insert(dst_name.to_owned());
    }
    for output in ["qx", "qy", "qz"] {
        assert!(
            defined.contains(output),
            "missing output register: {output}"
        );
    }
    CompiledLeaf {
        register_count: register_ids.len(),
        input_qx: register_id(&register_ids, "Q.X"),
        input_qy: register_id(&register_ids, "Q.Y"),
        input_qz: register_id(&register_ids, "Q.Z"),
        input_k: register_id(&register_ids, "k"),
        input_lookup_x: register_id(&register_ids, "lookup_x"),
        input_lookup_y: register_id(&register_ids, "lookup_y"),
        input_lookup_meta: register_id(&register_ids, "lookup_meta"),
        output_qx: register_id(&register_ids, "qx"),
        output_qy: register_id(&register_ids, "qy"),
        output_qz: register_id(&register_ids, "qz"),
        skip_on_lookup_infinity: leaf.lookup_infinity_policy.as_deref() == Some("boundary_noop"),
        instructions: compiled,
    }
}

fn compile_case_corpus(case_corpus: &CaseCorpusDocument) -> Vec<CompiledCase> {
    case_corpus
        .cases
        .iter()
        .map(|case| CompiledCase {
            case_id: case.case_id.clone(),
            accumulator: decode_point(&case.accumulator),
            lookup: decode_point(&case.lookup),
            expected: decode_point(&case.expected),
        })
        .collect()
}

fn compile_prepared_case_corpus(case_corpus: &PreparedCaseCorpus) -> Vec<CompiledCase> {
    case_corpus
        .cases
        .iter()
        .map(|case| CompiledCase {
            case_id: case.case_id.clone(),
            accumulator: decode_point(&case.accumulator),
            lookup: decode_point(&case.lookup),
            expected: decode_point(&case.expected),
        })
        .collect()
}

fn projective_matches_affine(point: &PointProj, expected: &PointAffine, modulus: &BigUint) -> bool {
    let (x, y, z) = point;
    match expected {
        None => z.is_zero(),
        Some((expected_x, expected_y)) => {
            !z.is_zero() && x == &((expected_x * z) % modulus) && y == &((expected_y * z) % modulus)
        }
    }
}

fn chunked_const_mul(
    value: &BigUint,
    constant: &BigUint,
    modulus: &BigUint,
    chunk_bits: u32,
    chunk_count: u32,
) -> BigUint {
    let mask = (BigUint::one() << chunk_bits) - BigUint::one();
    let mut total = BigUint::zero();
    for chunk_index in 0..chunk_count {
        let shift = chunk_bits * chunk_index;
        let chunk = (constant >> shift) & &mask;
        let scale = (BigUint::one() << shift) % modulus;
        total = (total + value * chunk * scale) % modulus;
    }
    total
}

fn execute_leaf(
    leaf: &CompiledLeaf,
    accumulator: PointAffine,
    lookup: PointAffine,
    modulus: &BigUint,
) -> PointProj {
    let (qx, qy, qz) = affine_to_proj(accumulator);
    if leaf.skip_on_lookup_infinity && lookup.is_none() {
        return (qx, qy, qz);
    }
    let lookup_x = lookup
        .as_ref()
        .map(|(x, _)| x.clone())
        .unwrap_or_else(BigUint::zero);
    let lookup_y = lookup
        .as_ref()
        .map(|(_, y)| y.clone())
        .unwrap_or_else(BigUint::zero);
    let lookup_meta = if lookup.is_none() {
        BigUint::one()
    } else {
        BigUint::zero()
    };
    let mut registers = vec![BigUint::zero(); leaf.register_count];
    registers[leaf.input_qx] = qx;
    registers[leaf.input_qy] = qy;
    registers[leaf.input_qz] = qz;
    registers[leaf.input_k] = if lookup.is_none() {
        BigUint::zero()
    } else {
        BigUint::one()
    };
    registers[leaf.input_lookup_x] = lookup_x.clone();
    registers[leaf.input_lookup_y] = lookup_y.clone();
    registers[leaf.input_lookup_meta] = lookup_meta;
    for instruction in &leaf.instructions {
        match instruction {
            CompiledInstruction::Copy { dst, src } => {
                registers[*dst] = registers[*src].clone();
            }
            CompiledInstruction::BoolFromFlag { dst, flags, bit } => {
                registers[*dst] = BigUint::from(flag_bit(&registers, *flags, *bit));
            }
            CompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                let current = registers[*dst].to_u64().expect("flag register too wide");
                registers[*dst] = BigUint::from(current ^ flag_bit(&registers, *flags, *bit));
            }
            CompiledInstruction::FieldMul { dst, left, right } => {
                registers[*dst] = (&registers[*left] * &registers[*right]) % modulus;
            }
            CompiledInstruction::FieldMulLookupX { dst, src } => {
                registers[*dst] = (&registers[*src] * &lookup_x) % modulus;
            }
            CompiledInstruction::FieldMulLookupY { dst, src } => {
                registers[*dst] = (&registers[*src] * &lookup_y) % modulus;
            }
            CompiledInstruction::FieldMulLookupSum { dst, src } => {
                registers[*dst] =
                    (&registers[*src] * ((&lookup_x + &lookup_y) % modulus)) % modulus;
            }
            CompiledInstruction::FieldAdd { dst, left, right } => {
                registers[*dst] = (&registers[*left] + &registers[*right]) % modulus;
            }
            CompiledInstruction::FieldSub { dst, left, right } => {
                registers[*dst] = mod_sub(&registers[*left], &registers[*right], modulus);
            }
            CompiledInstruction::FieldSubSum {
                dst,
                minuend,
                subtrahend_a,
                subtrahend_b,
            } => {
                let first = mod_sub(&registers[*minuend], &registers[*subtrahend_a], modulus);
                registers[*dst] = mod_sub(&first, &registers[*subtrahend_b], modulus);
            }
            CompiledInstruction::FieldTriple { dst, src } => {
                registers[*dst] = (BigUint::from(3u32) * &registers[*src]) % modulus;
            }
            CompiledInstruction::MulConst { dst, src, constant } => {
                registers[*dst] = (BigUint::from(*constant) * &registers[*src]) % modulus;
            }
            CompiledInstruction::SelectFieldIfFlag {
                dst,
                flag,
                when_nonzero,
                when_zero,
            } => {
                let source = if registers[*flag].is_zero() {
                    *when_zero
                } else {
                    *when_nonzero
                };
                registers[*dst] = registers[source].clone();
            }
            CompiledInstruction::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                c,
                h,
                a,
                y,
                z,
            } => {
                let i = (&registers[*y] * &lookup_y) % modulus;
                let k_minus_a = mod_sub(&registers[*h], &registers[*a], modulus);
                let k = mod_sub(&k_minus_a, &i, modulus);
                let l = (BigUint::from(3u32) * &registers[*a]) % modulus;
                let yz = (&lookup_y * &registers[*z]) % modulus;
                let e = (&registers[*y] + yz) % modulus;
                let f = (BigUint::from(21u32) * &registers[*z]) % modulus;
                let m = (&i + &f) % modulus;
                let n = mod_sub(&i, &f, modulus);
                registers[*out_x] = mod_sub(
                    &((&k * &n) % modulus),
                    &((&e * &registers[*c]) % modulus),
                    modulus,
                );
                registers[*out_y] = ((&n * &m) + (&registers[*c] * &l)) % modulus;
                registers[*out_z] = ((&m * &e) + (&l * &k)) % modulus;
            }
            CompiledInstruction::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                h,
                y,
                z,
            } => {
                let a = (&registers[*x] * &lookup_x) % modulus;
                let zx = (&registers[*z] * &lookup_x) % modulus;
                let c = (BigUint::from(21u32) * ((&registers[*x] + &zx) % modulus)) % modulus;
                let i = (&registers[*y] * &lookup_y) % modulus;
                let k_minus_a = mod_sub(&registers[*h], &a, modulus);
                let k = mod_sub(&k_minus_a, &i, modulus);
                let l = (BigUint::from(3u32) * &a) % modulus;
                let yz = (&lookup_y * &registers[*z]) % modulus;
                let e = (&registers[*y] + yz) % modulus;
                let f = (BigUint::from(21u32) * &registers[*z]) % modulus;
                let m = (&i + &f) % modulus;
                let n = mod_sub(&i, &f, modulus);
                registers[*out_x] =
                    mod_sub(&((&k * &n) % modulus), &((&e * &c) % modulus), modulus);
                registers[*out_y] = ((&n * &m) + (&c * &l)) % modulus;
                registers[*out_z] = ((&m * &e) + (&l * &k)) % modulus;
            }
            CompiledInstruction::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
            } => {
                let lookup_sum = (&lookup_x + &lookup_y) % modulus;
                let h = (((&registers[*x] + &registers[*y]) % modulus) * lookup_sum) % modulus;
                let a = (&registers[*x] * &lookup_x) % modulus;
                let zx = (&registers[*z] * &lookup_x) % modulus;
                let c = (BigUint::from(21u32) * ((&registers[*x] + &zx) % modulus)) % modulus;
                let i = (&registers[*y] * &lookup_y) % modulus;
                let k_minus_a = mod_sub(&h, &a, modulus);
                let k = mod_sub(&k_minus_a, &i, modulus);
                let l = (BigUint::from(3u32) * &a) % modulus;
                let yz = (&lookup_y * &registers[*z]) % modulus;
                let e = (&registers[*y] + yz) % modulus;
                let f = (BigUint::from(21u32) * &registers[*z]) % modulus;
                let m = (&i + &f) % modulus;
                let n = mod_sub(&i, &f, modulus);
                registers[*out_x] =
                    mod_sub(&((&k * &n) % modulus), &((&e * &c) % modulus), modulus);
                registers[*out_y] = ((&n * &m) + (&c * &l)) % modulus;
                registers[*out_z] = ((&m * &e) + (&l * &k)) % modulus;
            }
            CompiledInstruction::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                x,
                y,
                z,
                scratch,
                chunk_bits,
                chunk_count,
                b3,
            } => {
                registers[*scratch] = BigUint::zero();
                let lookup_sum = (&lookup_x + &lookup_y) % modulus;
                let accumulator_sum = (&registers[*x] + &registers[*y]) % modulus;
                let h = chunked_const_mul(
                    &accumulator_sum,
                    &lookup_sum,
                    modulus,
                    *chunk_bits,
                    *chunk_count,
                );
                let a = chunked_const_mul(
                    &registers[*x],
                    &lookup_x,
                    modulus,
                    *chunk_bits,
                    *chunk_count,
                );
                let zx = chunked_const_mul(
                    &registers[*z],
                    &lookup_x,
                    modulus,
                    *chunk_bits,
                    *chunk_count,
                );
                let c = (BigUint::from(*b3) * ((&registers[*x] + &zx) % modulus)) % modulus;
                let i = chunked_const_mul(
                    &registers[*y],
                    &lookup_y,
                    modulus,
                    *chunk_bits,
                    *chunk_count,
                );
                let k_minus_a = mod_sub(&h, &a, modulus);
                let k = mod_sub(&k_minus_a, &i, modulus);
                let l = (BigUint::from(3u32) * &a) % modulus;
                let yz = chunked_const_mul(
                    &registers[*z],
                    &lookup_y,
                    modulus,
                    *chunk_bits,
                    *chunk_count,
                );
                let e = (&registers[*y] + yz) % modulus;
                let f = (BigUint::from(*b3) * &registers[*z]) % modulus;
                let m = (&i + &f) % modulus;
                let n = mod_sub(&i, &f, modulus);
                registers[*out_x] =
                    mod_sub(&((&k * &n) % modulus), &((&e * &c) % modulus), modulus);
                registers[*out_y] = ((&n * &m) + (&c * &l)) % modulus;
                registers[*out_z] = ((&m * &e) + (&l * &k)) % modulus;
            }
        }
    }
    (
        registers[leaf.output_qx].clone(),
        registers[leaf.output_qy].clone(),
        registers[leaf.output_qz].clone(),
    )
}

pub fn run_attestation(input: &AttestationInput) -> PublicValues {
    assert_eq!(input.schema, "compiler-project-zkp-attestation-input-v2");
    assert_eq!(input.claim.document_type, "attestation_claim");
    assert!(
        input.leaf_document.document_type == "lookup_fed_leaf"
            || input.leaf_document.document_type == "interface_borrowed_leaf"
    );
    assert_eq!(
        input.family_document.document_type,
        "compiler_family_summary"
    );
    assert_eq!(
        input.case_corpus_document.document_type,
        "pointadd_case_corpus"
    );
    assert_eq!(input.claim.digest_scheme, DIGEST_SCHEME);
    assert_eq!(input.leaf_document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(input.family_document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(input.case_corpus_document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(
        semantic_payload_sha256(&input.claim.document_type, &input.claim.payload),
        input.claim.sha256
    );
    assert_eq!(
        semantic_payload_sha256(
            &input.leaf_document.document_type,
            &input.leaf_document.payload
        ),
        input.leaf_document.sha256
    );
    assert_eq!(
        semantic_payload_sha256(
            &input.family_document.document_type,
            &input.family_document.payload
        ),
        input.family_document.sha256
    );
    assert_eq!(
        semantic_payload_sha256(
            &input.case_corpus_document.document_type,
            &input.case_corpus_document.payload
        ),
        input.case_corpus_document.sha256
    );

    let claim = &input.claim.payload;
    let leaf = &input.leaf_document.payload;
    let family = &input.family_document.payload;
    let case_corpus = &input.case_corpus_document.payload;
    let compiled_leaf = compile_leaf(leaf);
    let compiled_cases = compile_case_corpus(case_corpus);

    assert_eq!(claim.selected_family_name, family.name);
    assert_eq!(claim.expected_case_count, case_corpus.case_count);

    assert_eq!(
        claim.non_clifford_formula.arithmetic_leaf_non_clifford,
        family.arithmetic_leaf_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.per_leaf_lookup_non_clifford,
        family.per_leaf_lookup_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.direct_seed_non_clifford,
        family.direct_seed_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.leaf_call_count_total,
        claim.leaf_call_count_total
    );
    assert_eq!(
        claim.non_clifford_formula.arithmetic_component,
        family.arithmetic_leaf_non_clifford * claim.leaf_call_count_total as u64
    );
    assert_eq!(
        claim.non_clifford_formula.lookup_component,
        family.per_leaf_lookup_non_clifford * claim.leaf_call_count_total as u64
    );
    assert_eq!(
        claim.non_clifford_formula.reconstructed_total,
        claim.non_clifford_formula.arithmetic_component
            + claim.non_clifford_formula.lookup_component
            + family.direct_seed_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.reconstructed_total,
        family.full_oracle_non_clifford
    );
    assert_eq!(
        claim.expected_full_oracle_non_clifford,
        family.full_oracle_non_clifford
    );

    assert_eq!(claim.logical_qubit_formula.field_bits, claim.field_bits);
    assert_eq!(
        claim.logical_qubit_formula.arithmetic_slot_count,
        family.arithmetic_slot_count
    );
    assert_eq!(
        claim.logical_qubit_formula.control_slot_count,
        family.control_slot_count
    );
    assert_eq!(
        claim.logical_qubit_formula.borrowed_interface_qubits,
        family.borrowed_interface_qubits
    );
    assert_eq!(
        claim.logical_qubit_formula.lookup_workspace_qubits,
        family.lookup_workspace_qubits
    );
    assert_eq!(
        claim.logical_qubit_formula.live_phase_bits,
        family.live_phase_bits
    );
    assert_eq!(
        claim.logical_qubit_formula.arithmetic_component,
        claim.field_bits as u64 * family.arithmetic_slot_count as u64
    );
    assert_eq!(
        claim.logical_qubit_formula.reconstructed_total,
        claim.logical_qubit_formula.arithmetic_component
            + family.control_slot_count as u64
            + family.borrowed_interface_qubits as u64
            + family.lookup_workspace_qubits as u64
            + family.live_phase_bits as u64
    );
    assert_eq!(
        claim.logical_qubit_formula.reconstructed_total,
        family.total_logical_qubits
    );
    assert_eq!(
        claim.expected_total_logical_qubits,
        family.total_logical_qubits
    );

    let modulus = parse_hex_uint(&case_corpus.field_modulus_hex);
    let mut passed_case_count = 0u32;
    for case in &compiled_cases {
        let observed = execute_leaf(
            &compiled_leaf,
            case.accumulator.clone(),
            case.lookup.clone(),
            &modulus,
        );
        let reference =
            add_affine_projective(case.accumulator.clone(), case.lookup.clone(), &modulus);
        assert!(
            projective_matches_affine(&reference, &case.expected, &modulus),
            "expected group-law output mismatch on {}",
            case.case_id
        );
        assert!(
            projective_matches_affine(&observed, &case.expected, &modulus),
            "leaf output mismatch on {}",
            case.case_id
        );
        passed_case_count += 1;
    }
    assert_eq!(passed_case_count, case_corpus.case_count);

    PublicValues {
        schema: "compiler-project-zkp-attestation-public-v2".to_owned(),
        document_digest_scheme: DIGEST_SCHEME.to_owned(),
        selected_family_name: family.name.clone(),
        claim_sha256: input.claim.sha256.clone(),
        leaf_sha256: input.leaf_document.sha256.clone(),
        family_sha256: input.family_document.sha256.clone(),
        case_corpus_sha256: input.case_corpus_document.sha256.clone(),
        resource_certificate_sha256: "legacy-full-document-path-without-resource-certificate"
            .to_owned(),
        expected_full_oracle_non_clifford: claim.expected_full_oracle_non_clifford,
        expected_total_logical_qubits: claim.expected_total_logical_qubits,
        case_count: case_corpus.case_count,
        passed_case_count,
    }
}

fn validate_committed_value_document(
    document: &CommittedDocument<SemanticJsonPayload>,
    expected_document_type: &str,
    expected_sha256: &str,
) {
    assert_eq!(document.document_type, expected_document_type);
    assert_eq!(document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(document.sha256, expected_sha256);
    assert_eq!(
        semantic_payload_sha256(&document.document_type, &document.payload),
        document.sha256
    );
}

fn decode_committed_payload<T: DeserializeOwned>(
    document: &CommittedDocument<SemanticJsonPayload>,
) -> T {
    serde_json::from_value(document.payload.0.clone()).expect("failed to decode committed payload")
}

fn claim_summary_from_claim(claim: &ClaimDocument) -> PreparedClaimSummary {
    PreparedClaimSummary {
        field_bits: claim.field_bits,
        leaf_call_count_total: claim.leaf_call_count_total,
        expected_full_oracle_non_clifford: claim.expected_full_oracle_non_clifford,
        expected_total_logical_qubits: claim.expected_total_logical_qubits,
        expected_case_count: claim.expected_case_count,
        non_clifford_formula: claim.non_clifford_formula.clone(),
        logical_qubit_formula: claim.logical_qubit_formula.clone(),
    }
}

fn family_summary_from_family(family: &FamilyDocument) -> PreparedFamilySummary {
    PreparedFamilySummary {
        name: family.name.clone(),
        arithmetic_leaf_non_clifford: family.arithmetic_leaf_non_clifford,
        direct_seed_non_clifford: family.direct_seed_non_clifford,
        per_leaf_lookup_non_clifford: family.per_leaf_lookup_non_clifford,
        full_oracle_non_clifford: family.full_oracle_non_clifford,
        arithmetic_slot_count: family.arithmetic_slot_count,
        control_slot_count: family.control_slot_count,
        borrowed_interface_qubits: family.borrowed_interface_qubits,
        lookup_workspace_qubits: family.lookup_workspace_qubits,
        live_phase_bits: family.live_phase_bits,
        total_logical_qubits: family.total_logical_qubits,
    }
}

fn prepared_case_corpus_from_case_corpus(case_corpus: &CaseCorpusDocument) -> PreparedCaseCorpus {
    PreparedCaseCorpus {
        field_modulus_hex: case_corpus.field_modulus_hex.clone(),
        case_start_index: case_corpus.case_start_index,
        case_count: case_corpus.case_count,
        cases: case_corpus.cases.clone(),
    }
}

fn json_object_field<'a>(value: &'a Value, key: &str) -> &'a Value {
    value
        .get(key)
        .unwrap_or_else(|| panic!("missing resource certificate field: {key}"))
}

fn json_string_field<'a>(value: &'a Value, key: &str) -> &'a str {
    json_object_field(value, key)
        .as_str()
        .unwrap_or_else(|| panic!("resource certificate field is not a string: {key}"))
}

fn json_u64_field(value: &Value, key: &str) -> u64 {
    json_object_field(value, key)
        .as_u64()
        .unwrap_or_else(|| panic!("resource certificate field is not a u64: {key}"))
}

fn json_bool_field(value: &Value, key: &str) -> bool {
    json_object_field(value, key)
        .as_bool()
        .unwrap_or_else(|| panic!("resource certificate field is not a bool: {key}"))
}

fn assert_qroam_reference_cost(row: &Value) {
    let domain_size = json_u64_field(row, "domain_size");
    let target_bits = json_u64_field(row, "target_bits");
    let block_size = json_u64_field(row, "block_size");
    assert!(domain_size > 0);
    assert!(target_bits > 0);
    assert!(block_size > 0);
    let address_blocks = (domain_size + block_size - 1) / block_size;
    let junk_register_count = block_size - 1;
    let junk_register_qubits = junk_register_count * target_bits;
    let target_plus_junk_qubits = block_size * target_bits;
    let lookup_compute_non_clifford = address_blocks + junk_register_qubits;
    let measured_uncompute_non_clifford = address_blocks + junk_register_count;
    assert_eq!(json_u64_field(row, "address_blocks"), address_blocks);
    assert_eq!(json_u64_field(row, "target_register_qubits"), target_bits);
    assert_eq!(
        json_u64_field(row, "junk_register_count"),
        junk_register_count
    );
    assert_eq!(
        json_u64_field(row, "junk_register_qubits"),
        junk_register_qubits
    );
    assert_eq!(
        json_u64_field(row, "target_plus_junk_qubits"),
        target_plus_junk_qubits
    );
    assert_eq!(
        json_u64_field(row, "lookup_compute_non_clifford"),
        lookup_compute_non_clifford
    );
    assert_eq!(
        json_u64_field(row, "measured_uncompute_non_clifford"),
        measured_uncompute_non_clifford
    );
    assert_eq!(
        json_u64_field(row, "per_stream_non_clifford"),
        lookup_compute_non_clifford + measured_uncompute_non_clifford
    );
}

fn json_array_field<'a>(value: &'a Value, key: &str) -> &'a Vec<Value> {
    json_object_field(value, key)
        .as_array()
        .unwrap_or_else(|| panic!("resource certificate field is not an array: {key}"))
}

fn json_primitive_counts(value: &Value, key: &str) -> BTreeMap<String, u64> {
    let object = json_object_field(value, key);
    let mut counts = BTreeMap::new();
    for count_key in ["ccx", "cx", "x", "measurement"] {
        counts.insert(count_key.to_owned(), json_u64_field(object, count_key));
    }
    counts
}

fn validate_resource_certificate(
    certificate: &Value,
    claim: &PreparedClaimSummary,
    family: &PreparedFamilySummary,
) {
    assert_eq!(
        json_string_field(certificate, "schema"),
        "compiler-project-resource-liveness-certificate-v3"
    );
    assert!(json_bool_field(certificate, "pass"));
    assert_eq!(
        json_string_field(certificate, "selected_family"),
        family.name.as_str()
    );
    assert_eq!(
        json_u64_field(certificate, "field_bits"),
        claim.field_bits as u64
    );
    assert_eq!(
        json_u64_field(certificate, "global_peak_live_qubits"),
        claim.expected_total_logical_qubits
    );

    let headline = json_object_field(certificate, "headline_totals");
    assert_eq!(
        json_u64_field(headline, "full_oracle_non_clifford"),
        claim.expected_full_oracle_non_clifford
    );
    assert_eq!(
        json_u64_field(headline, "total_logical_qubits"),
        claim.expected_total_logical_qubits
    );
    assert_eq!(
        json_u64_field(headline, "arithmetic_leaf_non_clifford"),
        family.arithmetic_leaf_non_clifford
    );
    assert_eq!(
        json_u64_field(headline, "per_leaf_lookup_non_clifford"),
        family.per_leaf_lookup_non_clifford
    );
    assert_eq!(
        json_u64_field(headline, "leaf_call_count_total"),
        claim.leaf_call_count_total as u64
    );

    let leaf_liveness = json_object_field(certificate, "flat_leaf_liveness");
    assert_eq!(
        json_u64_field(leaf_liveness, "arithmetic_slots_from_schedule"),
        family.arithmetic_slot_count as u64
    );
    assert_eq!(
        json_u64_field(leaf_liveness, "control_slots_from_schedule"),
        family.control_slot_count as u64
    );
    assert_eq!(
        json_u64_field(leaf_liveness, "arithmetic_qubits_from_schedule"),
        claim.field_bits as u64 * family.arithmetic_slot_count as u64
    );
    assert_eq!(json_u64_field(leaf_liveness, "borrowed_field_lanes"), 0);

    let qroam_workspace = json_object_field(certificate, "qroam_workspace");
    assert_eq!(
        json_u64_field(qroam_workspace, "lookup_workspace_qubits"),
        family.lookup_workspace_qubits as u64
    );
    assert_eq!(
        json_u64_field(qroam_workspace, "coordinate_field_lanes_materialized"),
        0
    );
    assert_eq!(
        json_u64_field(qroam_workspace, "coordinate_field_lane_qubits_materialized"),
        0
    );

    let owner_capacity = json_object_field(certificate, "derived_owner_capacity");
    assert_eq!(json_u64_field(owner_capacity, "owner_count"), 4);
    assert_eq!(
        json_u64_field(owner_capacity, "required_global_peak_qubits"),
        claim.expected_total_logical_qubits
    );
    assert_eq!(
        json_u64_field(owner_capacity, "capacity_global_peak_qubits"),
        claim.expected_total_logical_qubits
    );
    let owner_capacity_rows = json_array_field(owner_capacity, "rows");
    assert_eq!(
        owner_capacity_rows.len() as u64,
        json_u64_field(owner_capacity, "owner_count")
    );
    let mut owner_ids = BTreeSet::new();
    let mut required_peak_total = 0u64;
    let mut capacity_peak_total = 0u64;
    for row in owner_capacity_rows {
        let owner_id = json_string_field(row, "owner_id");
        owner_ids.insert(owner_id.to_owned());
        let capacity = json_u64_field(row, "capacity_qubits");
        let required = json_u64_field(row, "required_peak_qubits");
        assert!(
            capacity >= required,
            "owner capacity below derived requirement: {owner_id}"
        );
        assert_eq!(
            json_u64_field(row, "capacity_margin_qubits"),
            capacity - required
        );
        let assigned_components = json_object_field(row, "assigned_components");
        let component_total: u64 = assigned_components
            .as_object()
            .expect("assigned_components must be an object")
            .values()
            .map(|value| value.as_u64().expect("owner component must be u64"))
            .sum();
        assert_eq!(
            component_total,
            json_u64_field(row, "assigned_component_total")
        );
        assert_eq!(component_total, required);
        required_peak_total += required;
        capacity_peak_total += capacity;
    }
    assert_eq!(
        owner_ids,
        BTreeSet::from([
            "arithmetic_slot_register_file".to_owned(),
            "control_slot_register_file".to_owned(),
            "lookup_workspace".to_owned(),
            "phase_shell_live_register".to_owned(),
        ])
    );
    assert_eq!(required_peak_total, claim.expected_total_logical_qubits);
    assert_eq!(capacity_peak_total, claim.expected_total_logical_qubits);

    let primitive_ir = json_object_field(certificate, "primitive_oracle_ir");
    assert_eq!(
        json_string_field(primitive_ir, "selected_family"),
        family.name.as_str()
    );
    assert_eq!(
        json_string_field(primitive_ir, "source_schema"),
        "compiler-project-ft-ir-v2"
    );
    let leaf_sigma = json_array_field(primitive_ir, "leaf_sigma");
    assert_eq!(
        json_u64_field(primitive_ir, "leaf_sigma_count"),
        leaf_sigma.len() as u64
    );
    let mut primitive_totals: BTreeMap<String, u64> = BTreeMap::new();
    for key in ["ccx", "cx", "x", "measurement"] {
        primitive_totals.insert(key.to_owned(), 0);
    }
    let mut logical_qubits_total = 0u64;
    let mut phase_shell_hadamards = 0u64;
    let mut phase_shell_measurements = 0u64;
    let mut phase_shell_rotations = 0u64;
    let mut phase_shell_rotation_depth = 0u64;
    let mut tail_row_count = 0u64;
    let mut tail_non_clifford = 0u64;
    for row in leaf_sigma {
        let leaf_id = json_string_field(row, "leaf_id");
        let semantics = json_string_field(row, "resource_semantics");
        let path_multiplicity = json_u64_field(row, "path_multiplicity");
        match semantics {
            "additive_primitive" => {
                let base_instance_count = json_u64_field(row, "base_instance_count");
                let per_instance = json_primitive_counts(row, "primitive_counts_per_instance");
                let total = json_primitive_counts(row, "primitive_counts_total");
                for key in ["ccx", "cx", "x", "measurement"] {
                    let reconstructed = path_multiplicity * base_instance_count * per_instance[key];
                    assert_eq!(
                        reconstructed, total[key],
                        "primitive leaf-sigma row does not reconstruct: {leaf_id}:{key}"
                    );
                    *primitive_totals.get_mut(key).unwrap() += reconstructed;
                }
                if leaf_id.starts_with("arithmetic_opcode__complete_a0_all_streamed_tail__") {
                    tail_row_count += 1;
                    tail_non_clifford += total["ccx"];
                }
            }
            "peak_live_qubits" => {
                let reconstructed = path_multiplicity * json_u64_field(row, "logical_qubits");
                assert_eq!(
                    reconstructed,
                    json_u64_field(row, "logical_qubits_total"),
                    "live-qubit leaf-sigma row does not reconstruct: {leaf_id}"
                );
                logical_qubits_total += reconstructed;
            }
            "additive_phase_hadamards" => {
                let reconstructed = path_multiplicity * json_u64_field(row, "count");
                assert_eq!(reconstructed, json_u64_field(row, "count_total"));
                phase_shell_hadamards += reconstructed;
            }
            "additive_phase_measurements" => {
                let reconstructed = path_multiplicity * json_u64_field(row, "count");
                assert_eq!(reconstructed, json_u64_field(row, "count_total"));
                phase_shell_measurements += reconstructed;
            }
            "additive_phase_rotations" => {
                let reconstructed = path_multiplicity * json_u64_field(row, "count");
                assert_eq!(reconstructed, json_u64_field(row, "count_total"));
                phase_shell_rotations += reconstructed;
            }
            "additive_phase_rotation_depth" => {
                let reconstructed = path_multiplicity * json_u64_field(row, "count");
                assert_eq!(reconstructed, json_u64_field(row, "count_total"));
                phase_shell_rotation_depth += reconstructed;
            }
            _ => panic!("unknown resource leaf-sigma semantics: {semantics}"),
        }
    }
    let reconstruction = json_object_field(primitive_ir, "reconstruction_from_leaf_sigma");
    assert_eq!(
        primitive_totals["ccx"],
        claim.expected_full_oracle_non_clifford
    );
    assert_eq!(
        json_u64_field(reconstruction, "full_oracle_non_clifford"),
        primitive_totals["ccx"]
    );
    assert_eq!(
        json_primitive_counts(reconstruction, "primitive_totals"),
        primitive_totals
    );
    assert_eq!(
        json_u64_field(reconstruction, "total_logical_qubits"),
        logical_qubits_total
    );
    assert_eq!(logical_qubits_total, claim.expected_total_logical_qubits);
    assert_eq!(
        json_u64_field(reconstruction, "phase_shell_hadamards"),
        phase_shell_hadamards
    );
    assert_eq!(
        json_u64_field(reconstruction, "phase_shell_measurements"),
        phase_shell_measurements
    );
    assert_eq!(
        json_u64_field(reconstruction, "phase_shell_rotations"),
        phase_shell_rotations
    );
    assert_eq!(
        json_u64_field(reconstruction, "phase_shell_rotation_depth"),
        phase_shell_rotation_depth
    );
    let generated = json_object_field(primitive_ir, "generated_block_inventory_reconstruction");
    assert_eq!(
        json_u64_field(generated, "full_oracle_non_clifford"),
        primitive_totals["ccx"]
    );
    assert_eq!(
        json_u64_field(generated, "total_logical_qubits"),
        logical_qubits_total
    );
    let tail_rows = json_object_field(primitive_ir, "tail_macro_rows");
    assert_eq!(json_u64_field(tail_rows, "row_count"), tail_row_count);
    assert_eq!(
        json_u64_field(tail_rows, "whole_oracle_non_clifford"),
        tail_non_clifford
    );
    assert_eq!(
        tail_non_clifford,
        json_u64_field(tail_rows, "per_leaf_non_clifford")
            * json_u64_field(tail_rows, "leaf_call_count_total")
    );
    assert!(
        tail_row_count >= 20,
        "tail macro must be expanded into primitive leaf-sigma rows"
    );

    let arithmetic_operation_ir = json_object_field(certificate, "arithmetic_operation_ir");
    assert_eq!(
        json_string_field(arithmetic_operation_ir, "schema"),
        "compiler-project-arithmetic-operation-ir-v1"
    );
    assert!(json_bool_field(arithmetic_operation_ir, "pass"));
    let arithmetic_ir_checks = json_object_field(arithmetic_operation_ir, "checks")
        .as_object()
        .expect("arithmetic operation IR checks must be an object");
    assert!(
        arithmetic_ir_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "arithmetic operation IR contains a failing check"
    );
    let arithmetic_ir_summary = json_object_field(arithmetic_operation_ir, "summary");
    assert!(
        json_u64_field(arithmetic_ir_summary, "kernel_count") > 0,
        "arithmetic operation IR must contain kernels"
    );
    assert!(
        json_u64_field(arithmetic_ir_summary, "stage_count") > 0,
        "arithmetic operation IR must contain stages"
    );
    assert!(
        json_u64_field(arithmetic_ir_summary, "block_count") > 0,
        "arithmetic operation IR must contain blocks"
    );
    assert!(
        json_u64_field(arithmetic_ir_summary, "max_block_operand_slots_required") >= claim.field_bits as u64,
        "arithmetic operation IR operand profile must cover at least one field register"
    );
    let primitive_count_keys = ["ccx", "cx", "x", "measurement"];
    let mut observed_kernel_count = 0u64;
    let mut observed_stage_count = 0u64;
    let mut observed_block_count = 0u64;
    let mut observed_kernel_operation_count = 0u64;
    let mut max_block_operand_slots_required = 0u64;
    let mut arithmetic_kernel_lookup: BTreeMap<String, (u64, u64, String)> = BTreeMap::new();
    for kernel in json_array_field(arithmetic_operation_ir, "kernels") {
        observed_kernel_count += 1;
        let opcode = json_string_field(kernel, "opcode").to_owned();
        let stages = json_array_field(kernel, "stages");
        assert_eq!(
            json_u64_field(kernel, "stage_count"),
            stages.len() as u64,
            "arithmetic operation IR kernel stage count mismatch: {opcode}"
        );
        let mut kernel_counts: BTreeMap<String, u64> = BTreeMap::new();
        for key in primitive_count_keys {
            kernel_counts.insert(key.to_owned(), 0);
        }
        let mut kernel_operation_cursor = 0u64;
        for stage in stages {
            observed_stage_count += 1;
            let stage_name = json_string_field(stage, "stage").to_owned();
            assert_eq!(json_string_field(stage, "kernel"), opcode.as_str());
            assert_eq!(
                json_u64_field(stage, "operation_start"),
                kernel_operation_cursor,
                "arithmetic operation IR stage start mismatch: {opcode}:{stage_name}"
            );
            let blocks = json_array_field(stage, "blocks");
            assert_eq!(
                json_u64_field(stage, "block_count"),
                blocks.len() as u64,
                "arithmetic operation IR stage block count mismatch: {opcode}:{stage_name}"
            );
            assert!(
                json_string_field(stage, "block_digest_sha256").len() == 64,
                "arithmetic operation IR stage must bind a block digest"
            );
            let mut stage_counts: BTreeMap<String, u64> = BTreeMap::new();
            for key in primitive_count_keys {
                stage_counts.insert(key.to_owned(), 0);
            }
            let mut stage_operation_cursor = json_u64_field(stage, "operation_start");
            for block in blocks {
                observed_block_count += 1;
                let block_name = json_string_field(block, "block");
                assert_eq!(json_string_field(block, "kernel"), opcode.as_str());
                assert_eq!(json_string_field(block, "stage"), stage_name.as_str());
                assert_eq!(
                    json_u64_field(block, "operation_start"),
                    stage_operation_cursor,
                    "arithmetic operation IR block start mismatch: {opcode}:{stage_name}:{block_name}"
                );
                assert_eq!(
                    json_u64_field(block, "operation_count"),
                    json_u64_field(block, "operation_end_exclusive")
                        - json_u64_field(block, "operation_start"),
                    "arithmetic operation IR block operation count mismatch"
                );
                assert!(
                    json_string_field(block, "operation_stream_sha256").len() == 64,
                    "arithmetic operation IR block must bind an operation stream digest"
                );
                let operand_profile = json_object_field(block, "operand_profile");
                assert_eq!(json_u64_field(operand_profile, "negative_operand_count"), 0);
                assert_eq!(json_u64_field(operand_profile, "too_wide_operand_rows"), 0);
                max_block_operand_slots_required = max_block_operand_slots_required
                    .max(json_u64_field(operand_profile, "operand_slots_required"));
                let block_counts = json_primitive_counts(block, "primitive_counts_total");
                assert_eq!(
                    block_counts,
                    json_primitive_counts(block, "declared_primitive_counts_total"),
                    "arithmetic operation IR block declared totals mismatch"
                );
                for key in primitive_count_keys {
                    *stage_counts.get_mut(key).unwrap() += block_counts[key];
                }
                stage_operation_cursor = json_u64_field(block, "operation_end_exclusive");
            }
            assert_eq!(
                stage_operation_cursor,
                json_u64_field(stage, "operation_end_exclusive"),
                "arithmetic operation IR stage end mismatch"
            );
            assert_eq!(
                json_u64_field(stage, "operation_count"),
                json_u64_field(stage, "operation_end_exclusive")
                    - json_u64_field(stage, "operation_start"),
                "arithmetic operation IR stage operation count mismatch"
            );
            assert_eq!(
                stage_counts,
                json_primitive_counts(stage, "primitive_counts_total"),
                "arithmetic operation IR stage totals do not reconstruct"
            );
            assert_eq!(
                stage_counts,
                json_primitive_counts(stage, "declared_primitive_counts_total"),
                "arithmetic operation IR stage declared totals mismatch"
            );
            for key in primitive_count_keys {
                *kernel_counts.get_mut(key).unwrap() += stage_counts[key];
            }
            kernel_operation_cursor = json_u64_field(stage, "operation_end_exclusive");
        }
        assert_eq!(
            kernel_operation_cursor,
            json_u64_field(kernel, "operation_count"),
            "arithmetic operation IR kernel operation count mismatch: {opcode}"
        );
        assert_eq!(
            kernel_counts,
            json_primitive_counts(kernel, "primitive_counts_total"),
            "arithmetic operation IR kernel totals do not reconstruct: {opcode}"
        );
        assert_eq!(
            kernel_counts,
            json_primitive_counts(kernel, "declared_primitive_counts_total"),
            "arithmetic operation IR kernel declared totals mismatch: {opcode}"
        );
        assert_eq!(
            kernel_counts["ccx"],
            json_u64_field(kernel, "exact_non_clifford_per_kernel"),
            "arithmetic operation IR kernel non-Clifford mismatch: {opcode}"
        );
        observed_kernel_operation_count += json_u64_field(kernel, "operation_count");
        arithmetic_kernel_lookup.insert(
            opcode,
            (
                json_u64_field(kernel, "operation_count"),
                json_u64_field(kernel, "exact_non_clifford_per_kernel"),
                json_string_field(kernel, "stage_digest_sha256").to_owned(),
            ),
        );
    }
    assert_eq!(
        observed_kernel_count,
        json_u64_field(arithmetic_ir_summary, "kernel_count")
    );
    assert_eq!(
        observed_stage_count,
        json_u64_field(arithmetic_ir_summary, "stage_count")
    );
    assert_eq!(
        observed_block_count,
        json_u64_field(arithmetic_ir_summary, "block_count")
    );
    assert_eq!(
        observed_kernel_operation_count,
        json_u64_field(arithmetic_ir_summary, "kernel_operation_count_total")
    );
    assert_eq!(
        max_block_operand_slots_required,
        json_u64_field(arithmetic_ir_summary, "max_block_operand_slots_required")
    );
    let arithmetic_leaf = json_object_field(arithmetic_operation_ir, "leaf_arithmetic_summary");
    assert_eq!(
        json_u64_field(arithmetic_leaf, "non_clifford_total"),
        family.arithmetic_leaf_non_clifford
    );
    assert_eq!(
        json_primitive_counts(arithmetic_leaf, "primitive_counts_total")["ccx"],
        family.arithmetic_leaf_non_clifford
    );
    assert!(
        json_string_field(arithmetic_leaf, "operation_stream_sha256").len() == 64,
        "arithmetic leaf operation stream digest must be a sha256 hex digest"
    );
    assert!(
        json_array_field(arithmetic_leaf, "non_arithmetic_leaf_opcodes").len() > 0,
        "arithmetic operation IR must explicitly separate non-arithmetic leaf opcodes"
    );
    let mut arithmetic_leaf_counts: BTreeMap<String, u64> = BTreeMap::new();
    for key in primitive_count_keys {
        arithmetic_leaf_counts.insert(key.to_owned(), 0);
    }
    for row in json_array_field(arithmetic_leaf, "rows") {
        let opcode = json_string_field(row, "opcode");
        let primitive_counts = json_primitive_counts(row, "primitive_counts_total");
        let instance_count = json_u64_field(row, "leaf_instance_count");
        let per_instance = json_u64_field(row, "kernel_non_clifford_per_instance");
        let (kernel_operation_count, kernel_non_clifford, kernel_stage_digest) =
            arithmetic_kernel_lookup
                .get(opcode)
                .unwrap_or_else(|| panic!("leaf arithmetic row references unknown kernel: {opcode}"));
        assert_eq!(
            json_u64_field(row, "kernel_operation_count"),
            *kernel_operation_count
        );
        assert_eq!(per_instance, *kernel_non_clifford);
        assert_eq!(
            primitive_counts["ccx"],
            instance_count * per_instance,
            "arithmetic operation IR row does not reconstruct: {opcode}"
        );
        assert_eq!(
            json_string_field(row, "kernel_stage_digest_sha256"),
            kernel_stage_digest.as_str(),
            "arithmetic operation IR row must bind the referenced kernel stage digest"
        );
        for key in primitive_count_keys {
            arithmetic_leaf_counts
                .entry(key.to_owned())
                .and_modify(|value| *value += primitive_counts[key]);
        }
    }
    assert_eq!(
        arithmetic_leaf_counts,
        json_primitive_counts(arithmetic_leaf, "primitive_counts_total")
    );
    assert_eq!(
        arithmetic_leaf_counts["ccx"],
        family.arithmetic_leaf_non_clifford
    );

    let materialized_stream = json_object_field(certificate, "materialized_operation_stream");
    assert_eq!(
        json_string_field(materialized_stream, "family"),
        family.name.as_str()
    );
    let materialized_gate_totals = json_object_field(materialized_stream, "gate_totals");
    assert_eq!(
        json_u64_field(materialized_gate_totals, "ccx"),
        claim.expected_full_oracle_non_clifford
    );
    assert!(
        json_string_field(materialized_stream, "operation_stream_sha256").len() == 64,
        "materialized operation stream digest must be a sha256 hex digest"
    );
    assert!(
        json_string_field(materialized_stream, "segment_merkle_root_sha256").len() == 64,
        "materialized operation stream segment root must be a sha256 hex digest"
    );
    assert!(
        json_u64_field(materialized_stream, "segment_count") > 0,
        "materialized operation stream must have at least one digest segment"
    );
    assert!(
        json_u64_field(materialized_stream, "segment_size") > 0,
        "materialized operation stream segment size must be positive"
    );
    let materialized_checks = json_object_field(materialized_stream, "reconstruction_checks")
        .as_object()
        .expect("materialized stream checks must be an object");
    assert!(
        materialized_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "materialized operation stream contains a failing check"
    );

    let checks = json_object_field(certificate, "checks")
        .as_object()
        .expect("resource certificate checks must be an object");
    assert!(
        checks.values().all(|value| value.as_bool() == Some(true)),
        "resource certificate contains a failing check"
    );
}

fn compiled_leaf_written_registers(leaf: &CompiledLeaf) -> BTreeSet<u64> {
    let mut written = BTreeSet::new();
    for instruction in &leaf.instructions {
        match instruction {
            CompiledInstruction::CompleteA0StreamedTail {
                out_x,
                out_y,
                out_z,
                ..
            }
            | CompiledInstruction::CompleteA0FullyStreamedTail {
                out_x,
                out_y,
                out_z,
                ..
            }
            | CompiledInstruction::CompleteA0AllStreamedTail {
                out_x,
                out_y,
                out_z,
                ..
            } => {
                written.insert(*out_x as u64);
                written.insert(*out_y as u64);
                written.insert(*out_z as u64);
            }
            CompiledInstruction::CompleteA0ReusableChunkTail {
                out_x,
                out_y,
                out_z,
                scratch,
                ..
            } => {
                written.insert(*out_x as u64);
                written.insert(*out_y as u64);
                written.insert(*out_z as u64);
                written.insert(*scratch as u64);
            }
            CompiledInstruction::Copy { dst, .. }
            | CompiledInstruction::BoolFromFlag { dst, .. }
            | CompiledInstruction::ClearBoolFromFlag { dst, .. }
            | CompiledInstruction::FieldMul { dst, .. }
            | CompiledInstruction::FieldMulLookupX { dst, .. }
            | CompiledInstruction::FieldMulLookupY { dst, .. }
            | CompiledInstruction::FieldMulLookupSum { dst, .. }
            | CompiledInstruction::FieldAdd { dst, .. }
            | CompiledInstruction::FieldSub { dst, .. }
            | CompiledInstruction::FieldSubSum { dst, .. }
            | CompiledInstruction::FieldTriple { dst, .. }
            | CompiledInstruction::MulConst { dst, .. }
            | CompiledInstruction::SelectFieldIfFlag { dst, .. } => {
                written.insert(*dst as u64);
            }
        }
    }
    written
}

fn validate_proof_register_contract(contract: &Value, prepared_leaf: &CompiledLeaf) {
    assert_eq!(
        json_string_field(contract, "schema"),
        "compiler-project-proof-register-contract-v1"
    );
    assert!(json_bool_field(contract, "pass"));
    let checks = json_object_field(contract, "checks")
        .as_object()
        .expect("proof register contract checks must be an object");
    assert!(
        checks.values().all(|value| value.as_bool() == Some(true)),
        "proof register contract contains a failing check"
    );
    assert!(
        json_array_field(contract, "unclassified_registers").is_empty(),
        "proof register contract must not contain unclassified registers"
    );
    assert!(
        json_array_field(contract, "unowned_written_quantum_registers").is_empty(),
        "proof register contract must not contain unowned written quantum registers"
    );
    let rows = json_array_field(contract, "register_rows");
    assert_eq!(rows.len(), prepared_leaf.register_count);
    let written = compiled_leaf_written_registers(prepared_leaf);
    let contract_written: BTreeSet<u64> = json_array_field(contract, "written_register_ids")
        .iter()
        .map(|value| value.as_u64().expect("written register id must be u64"))
        .collect();
    assert_eq!(contract_written, written);
    let mut seen_ids = BTreeSet::new();
    let mut semantic_lookup_registers = BTreeSet::new();
    for row in rows {
        let register_id = json_u64_field(row, "register_id");
        assert!(register_id < prepared_leaf.register_count as u64);
        assert!(seen_ids.insert(register_id));
        let is_written = json_bool_field(row, "is_written_by_instruction");
        assert_eq!(is_written, written.contains(&register_id));
        match json_string_field(row, "resource_class") {
            "counted_quantum_wire" => {
                assert!(json_bool_field(row, "quantum_counted"));
                assert!(
                    json_u64_field(row, "qubits") > 0,
                    "counted proof register must carry positive qubit capacity"
                );
                assert!(
                    row.get("owner_id").and_then(Value::as_str).is_some(),
                    "counted proof register must name a resource owner"
                );
            }
            "carried_input_alias" => {
                assert!(!json_bool_field(row, "quantum_counted"));
                assert!(!is_written);
            }
            "semantic_lookup_constant" => {
                assert!(!json_bool_field(row, "quantum_counted"));
                assert!(!is_written);
                semantic_lookup_registers.insert(json_string_field(row, "register").to_owned());
            }
            "lookup_metadata_interface" => {
                assert!(!json_bool_field(row, "quantum_counted"));
            }
            other => panic!("unexpected proof register resource class: {other}"),
        }
    }
    assert_eq!(seen_ids.len(), prepared_leaf.register_count);
    assert!(semantic_lookup_registers.contains("lookup_x"));
    assert!(semantic_lookup_registers.contains("lookup_y"));
}

fn validate_reusable_chunk_lowering(
    certificate: &Value,
    claim: &PreparedClaimSummary,
    family: &PreparedFamilySummary,
) {
    assert_eq!(
        json_string_field(certificate, "schema"),
        "compiler-project-reusable-chunk-lowering-v2"
    );
    assert_eq!(
        json_string_field(certificate, "status"),
        "proven_public_headline"
    );
    assert!(json_bool_field(certificate, "pass"));

    let executable = json_object_field(certificate, "executable_contract");
    assert_eq!(
        json_string_field(executable, "opcode"),
        "complete_a0_reusable_chunk_tail"
    );
    let chunk_contract = json_object_field(executable, "chunk_contract");
    let chunk_bits = json_u64_field(chunk_contract, "chunk_bits");
    let chunk_count = json_u64_field(chunk_contract, "chunk_count");
    assert!(chunk_bits > 0);
    assert!(chunk_count > 0);
    assert!(json_u64_field(chunk_contract, "b3") > 0);
    assert_eq!(
        json_u64_field(chunk_contract, "full_coordinate_lanes_materialized"),
        0
    );

    let stream_plan = json_object_field(certificate, "stream_plan");
    let coordinate_tables = json_array_field(stream_plan, "coordinate_tables");
    assert_eq!(
        json_u64_field(stream_plan, "coordinate_table_count"),
        coordinate_tables.len() as u64
    );
    assert_eq!(json_u64_field(stream_plan, "chunk_bits"), chunk_bits);
    assert_eq!(json_u64_field(stream_plan, "chunk_count"), chunk_count);
    assert_eq!(
        json_u64_field(stream_plan, "chunk_streams_per_leaf"),
        json_u64_field(stream_plan, "coordinate_table_count") * chunk_count
    );
    assert_eq!(
        json_u64_field(stream_plan, "whole_oracle_chunk_streams"),
        json_u64_field(stream_plan, "leaf_call_count_total")
            * json_u64_field(stream_plan, "chunk_streams_per_leaf")
    );
    assert_eq!(
        json_u64_field(stream_plan, "leaf_call_count_total"),
        claim.leaf_call_count_total as u64
    );
    let qroam_model = json_object_field(certificate, "standard_qroamclean_k1_model");
    assert_eq!(json_u64_field(qroam_model, "block_size"), 1);
    assert_eq!(
        json_u64_field(qroam_model, "target_register_qubits"),
        chunk_bits
    );
    assert_eq!(
        json_u64_field(qroam_model, "junk_register_qubits"),
        (json_u64_field(qroam_model, "block_size") - 1)
            * json_u64_field(qroam_model, "target_register_qubits")
    );
    assert_eq!(
        json_u64_field(qroam_model, "target_plus_junk_qubits"),
        json_u64_field(qroam_model, "target_register_qubits")
            + json_u64_field(qroam_model, "junk_register_qubits")
    );
    assert_eq!(
        json_u64_field(qroam_model, "per_stream_non_clifford"),
        json_u64_field(qroam_model, "lookup_compute_non_clifford")
            + json_u64_field(qroam_model, "measured_uncompute_non_clifford")
    );
    let stream_rows = json_array_field(stream_plan, "rows");
    assert_eq!(
        stream_rows.len() as u64,
        json_u64_field(stream_plan, "chunk_streams_per_leaf")
    );
    for row in stream_rows {
        assert_eq!(json_u64_field(row, "full_coordinate_lane_materialized"), 0);
        assert_eq!(
            json_u64_field(row, "live_target_qubits"),
            json_u64_field(qroam_model, "target_register_qubits")
        );
        assert_eq!(
            json_u64_field(row, "junk_register_qubits"),
            json_u64_field(qroam_model, "junk_register_qubits")
        );
    }
    let qroam_primitive = json_object_field(certificate, "qroam_primitive_certificate");
    assert_eq!(
        json_string_field(qroam_primitive, "schema"),
        "compiler-project-qroam-k1-primitive-certificate-v1"
    );
    assert!(json_bool_field(qroam_primitive, "pass"));
    let qroam_primitive_checks = json_object_field(qroam_primitive, "checks")
        .as_object()
        .expect("QROAM primitive certificate checks must be an object");
    assert!(
        qroam_primitive_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "QROAM primitive certificate contains a failing check"
    );
    let qroam_parameters = json_object_field(qroam_primitive, "parameters");
    assert_eq!(
        json_u64_field(qroam_parameters, "domain_size"),
        json_u64_field(qroam_model, "domain_size")
    );
    assert_eq!(
        json_u64_field(qroam_parameters, "target_bits"),
        json_u64_field(qroam_model, "target_register_qubits")
    );
    assert_eq!(
        json_u64_field(qroam_parameters, "block_size"),
        json_u64_field(qroam_model, "block_size")
    );
    let qroam_traversed = json_object_field(qroam_primitive, "traversed_counts");
    assert_eq!(
        json_u64_field(qroam_traversed, "lookup_compute_non_clifford"),
        json_u64_field(qroam_model, "lookup_compute_non_clifford")
    );
    assert_eq!(
        json_u64_field(qroam_traversed, "measured_uncompute_non_clifford"),
        json_u64_field(qroam_model, "measured_uncompute_non_clifford")
    );
    assert_eq!(
        json_u64_field(qroam_traversed, "per_stream_non_clifford"),
        json_u64_field(qroam_model, "per_stream_non_clifford")
    );
    assert_eq!(
        json_u64_field(qroam_traversed, "target_register_qubits"),
        json_u64_field(qroam_model, "target_register_qubits")
    );
    assert_eq!(
        json_u64_field(qroam_traversed, "junk_register_qubits"),
        json_u64_field(qroam_model, "junk_register_qubits")
    );
    assert_eq!(
        json_u64_field(qroam_traversed, "target_plus_junk_qubits"),
        json_u64_field(qroam_model, "target_plus_junk_qubits")
    );
    let qroam_wire_catalog = json_object_field(qroam_primitive, "wire_catalog");
    assert_eq!(
        json_u64_field(
            json_object_field(qroam_wire_catalog, "target_register"),
            "qubits"
        ),
        json_u64_field(qroam_model, "target_register_qubits")
    );
    assert_eq!(
        json_u64_field(
            json_object_field(qroam_wire_catalog, "junk_registers"),
            "qubits"
        ),
        json_u64_field(qroam_model, "junk_register_qubits")
    );
    let qroam_operation_stream = json_object_field(qroam_primitive, "operation_stream");
    let qroam_segments = json_array_field(qroam_operation_stream, "segments");
    assert_eq!(
        json_u64_field(qroam_operation_stream, "segment_count"),
        qroam_segments.len() as u64
    );
    assert_eq!(
        json_string_field(qroam_operation_stream, "segment_merkle_root_sha256").len(),
        64
    );
    let mut qroam_compute_ccx = 0u64;
    let mut qroam_cleanup_ccx = 0u64;
    for segment in qroam_segments {
        assert_eq!(json_string_field(segment, "sha256").len(), 64);
        assert_eq!(
            json_u64_field(segment, "operation_count"),
            json_u64_field(segment, "end_address_exclusive")
                - json_u64_field(segment, "start_address")
        );
        assert_eq!(
            json_u64_field(segment, "ccx"),
            json_u64_field(segment, "operation_count")
        );
        match json_string_field(segment, "phase") {
            "compute" => qroam_compute_ccx += json_u64_field(segment, "ccx"),
            "measured_uncompute" => qroam_cleanup_ccx += json_u64_field(segment, "ccx"),
            other => panic!("unexpected QROAM primitive phase: {other}"),
        }
    }
    assert_eq!(
        qroam_compute_ccx,
        json_u64_field(qroam_traversed, "lookup_compute_non_clifford")
    );
    assert_eq!(
        qroam_cleanup_ccx,
        json_u64_field(qroam_traversed, "measured_uncompute_non_clifford")
    );

    let qroam_reference = json_object_field(certificate, "qroam_reference_crosscheck");
    assert_eq!(
        json_string_field(qroam_reference, "schema"),
        "compiler-project-qroam-reference-crosscheck-v1"
    );
    assert!(json_bool_field(qroam_reference, "pass"));
    let qroam_reference_checks = json_object_field(qroam_reference, "checks")
        .as_object()
        .expect("QROAM reference cross-check checks must be an object");
    assert!(
        qroam_reference_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "QROAM reference cross-check contains a failing check"
    );
    let qroam_reference_selected = json_object_field(qroam_reference, "selected_reference");
    let qroam_reference_ledger_selected =
        json_object_field(qroam_reference, "ledger_selected_reference");
    assert_qroam_reference_cost(qroam_reference_selected);
    assert_qroam_reference_cost(qroam_reference_ledger_selected);
    assert_eq!(
        json_u64_field(qroam_reference_selected, "domain_size"),
        json_u64_field(qroam_model, "domain_size")
    );
    assert_eq!(
        json_u64_field(qroam_reference_selected, "target_bits"),
        json_u64_field(qroam_model, "target_register_qubits")
    );
    assert_eq!(
        json_u64_field(qroam_reference_selected, "block_size"),
        json_u64_field(qroam_model, "block_size")
    );
    assert_eq!(
        json_u64_field(qroam_reference_selected, "lookup_compute_non_clifford"),
        json_u64_field(qroam_model, "lookup_compute_non_clifford")
    );
    assert_eq!(
        json_u64_field(qroam_reference_selected, "measured_uncompute_non_clifford"),
        json_u64_field(qroam_model, "measured_uncompute_non_clifford")
    );
    assert_eq!(
        json_u64_field(qroam_reference_selected, "per_stream_non_clifford"),
        json_u64_field(qroam_model, "per_stream_non_clifford")
    );
    assert_eq!(
        json_u64_field(qroam_reference_selected, "target_plus_junk_qubits"),
        json_u64_field(qroam_model, "target_plus_junk_qubits")
    );
    assert!(
        json_u64_field(qroam_reference_ledger_selected, "target_bits")
            >= json_u64_field(qroam_reference_selected, "target_bits")
    );
    assert_eq!(
        json_u64_field(qroam_reference_ledger_selected, "domain_size"),
        json_u64_field(qroam_reference_selected, "domain_size")
    );
    assert_eq!(
        json_u64_field(qroam_reference_ledger_selected, "block_size"),
        json_u64_field(qroam_reference_selected, "block_size")
    );

    let modular_certificate = json_object_field(certificate, "modular_arithmetic_certificate");
    assert_eq!(
        json_string_field(modular_certificate, "schema"),
        "compiler-project-modular-arithmetic-certificate-v1"
    );
    assert!(json_bool_field(modular_certificate, "pass"));
    let modular_checks = json_object_field(modular_certificate, "checks")
        .as_object()
        .expect("modular arithmetic certificate checks must be an object");
    assert!(
        modular_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "modular arithmetic certificate contains a failing check"
    );
    let secp_parameters = json_object_field(modular_certificate, "secp256k1_parameters");
    assert_eq!(
        json_u64_field(secp_parameters, "field_bits"),
        claim.field_bits as u64
    );
    assert_eq!(json_u64_field(secp_parameters, "shift"), 32);
    assert_eq!(json_u64_field(secp_parameters, "low_term"), 977);
    assert_eq!(
        json_u64_field(secp_parameters, "canonical_subtract_passes"),
        2
    );
    assert_eq!(
        json_string_field(secp_parameters, "modulus_hex"),
        "fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f"
    );
    let opcode_certificate = json_object_field(modular_certificate, "opcode_count_certificate");
    assert!(json_bool_field(opcode_certificate, "opcode_counts_match"));
    let chain = json_array_field(opcode_certificate, "mul_const_21_addition_chain");
    let expected_chain = [1_u64, 2, 4, 8, 16, 20, 21];
    assert_eq!(chain.len(), expected_chain.len());
    for (index, expected_value) in expected_chain.iter().enumerate() {
        assert_eq!(chain[index].as_u64(), Some(*expected_value));
    }
    let expected_opcode_counts = json_object_field(opcode_certificate, "expected_non_clifford_per_opcode")
        .as_object()
        .expect("expected opcode counts must be an object");
    let observed_opcode_counts = json_object_field(opcode_certificate, "observed_non_clifford_per_opcode")
        .as_object()
        .expect("observed opcode counts must be an object");
    assert_eq!(expected_opcode_counts.len(), observed_opcode_counts.len());
    let field_mul_stage =
        json_object_field(modular_certificate, "field_mul_stage_count_certificate");
    assert!(json_bool_field(field_mul_stage, "stage_counts_match"));
    let modular_add_cost = 2 * (claim.field_bits as u64 - 1);
    let field_mul_cost = json_u64_field(field_mul_stage, "expected_total_ccx");
    let expected_opcode_costs = BTreeMap::from([
        ("field_add", modular_add_cost),
        ("field_sub", modular_add_cost),
        ("field_sub_sum", 2 * modular_add_cost),
        ("field_triple", 2 * modular_add_cost),
        ("mul_const", 6 * modular_add_cost),
        ("field_mul", field_mul_cost),
    ]);
    for (opcode, expected_cost) in expected_opcode_costs {
        assert_eq!(
            expected_opcode_counts.get(opcode).and_then(Value::as_u64),
            Some(expected_cost)
        );
        assert_eq!(
            observed_opcode_counts.get(opcode).and_then(Value::as_u64),
            Some(expected_cost)
        );
    }
    let expected_stage_ccx = json_object_field(field_mul_stage, "expected_stage_ccx")
        .as_object()
        .expect("expected_stage_ccx must be an object");
    let observed_stage_ccx = json_object_field(field_mul_stage, "observed_stage_ccx")
        .as_object()
        .expect("observed_stage_ccx must be an object");
    assert_eq!(expected_stage_ccx.len(), observed_stage_ccx.len());
    let mut expected_total_ccx = 0u64;
    let mut observed_total_ccx = 0u64;
    for (stage_name, expected_value) in expected_stage_ccx {
        let expected_ccx = expected_value
            .as_u64()
            .expect("expected field_mul stage count must be u64");
        let observed_ccx = observed_stage_ccx
            .get(stage_name)
            .and_then(Value::as_u64)
            .expect("observed field_mul stage count must be u64");
        assert_eq!(observed_ccx, expected_ccx);
        expected_total_ccx += expected_ccx;
        observed_total_ccx += observed_ccx;
    }
    assert_eq!(
        expected_total_ccx,
        json_u64_field(field_mul_stage, "expected_total_ccx")
    );
    assert_eq!(
        observed_total_ccx,
        json_u64_field(field_mul_stage, "observed_total_ccx")
    );
    assert_eq!(
        json_u64_field(field_mul_stage, "observed_total_ccx"),
        json_u64_field(field_mul_stage, "expected_total_ccx")
    );
    for row in json_array_field(modular_certificate, "reduced_width_exhaustive_cases") {
        assert!(json_bool_field(row, "pass"));
        assert_eq!(
            json_u64_field(row, "rows_checked"),
            json_u64_field(row, "modulus") * json_u64_field(row, "modulus")
        );
        assert!(
            json_array_field(row, "failures").is_empty(),
            "reduced-width modular arithmetic case must not contain failures"
        );
    }

    let primitive_contract =
        json_object_field(certificate, "chunked_multiplier_primitive_contract");
    let chunk_effective_bits = json_array_field(primitive_contract, "chunk_effective_bits");
    assert_eq!(chunk_effective_bits.len() as u64, chunk_count);
    let mut expected_effective_bits = Vec::new();
    for chunk_index in 0..chunk_count {
        let consumed_bits = chunk_bits * chunk_index;
        let remaining_bits = (claim.field_bits as u64).saturating_sub(consumed_bits);
        expected_effective_bits.push(chunk_bits.min(remaining_bits));
    }
    for (index, expected_bits) in expected_effective_bits.iter().enumerate() {
        assert_eq!(chunk_effective_bits[index].as_u64(), Some(*expected_bits));
    }
    assert_eq!(
        json_u64_field(
            primitive_contract,
            "table_multiplier_partial_products_per_leaf"
        ),
        json_array_field(primitive_contract, "table_multiplier_rows")
            .iter()
            .map(|row| json_u64_field(row, "chunked_partial_product_non_clifford"))
            .sum::<u64>()
    );
    assert_eq!(
        json_u64_field(
            primitive_contract,
            "inherited_table_multiplier_partial_products_per_leaf"
        ),
        json_array_field(primitive_contract, "table_multiplier_rows")
            .iter()
            .map(|row| json_u64_field(row, "inherited_full_width_partial_product_non_clifford"))
            .sum::<u64>()
    );
    assert_eq!(
        json_u64_field(
            primitive_contract,
            "table_multiplier_partial_products_per_leaf"
        ),
        json_u64_field(
            primitive_contract,
            "inherited_table_multiplier_partial_products_per_leaf"
        )
    );
    let conservatism = json_object_field(primitive_contract, "arithmetic_base_conservatism");
    assert!(json_bool_field(
        conservatism,
        "inherited_base_without_streamed_qroam_is_valid_for_chunked_contract"
    ));
    assert!(json_bool_field(
        conservatism,
        "table_multiplier_partial_products_equal_inherited_full_width"
    ));
    for row in json_array_field(primitive_contract, "table_multiplier_rows") {
        let chunks = json_array_field(row, "chunk_rows");
        assert_eq!(chunks.len() as u64, chunk_count);
        let mut chunk_partial_products = 0u64;
        for (index, chunk) in chunks.iter().enumerate() {
            assert_eq!(json_u64_field(chunk, "target_capacity_bits"), chunk_bits);
            assert_eq!(
                json_u64_field(chunk, "effective_constant_bits"),
                expected_effective_bits[index]
            );
            assert_eq!(
                json_u64_field(chunk, "zero_padded_target_bits"),
                chunk_bits - expected_effective_bits[index]
            );
            chunk_partial_products += json_u64_field(chunk, "partial_product_non_clifford");
        }
        assert_eq!(
            chunk_partial_products,
            json_u64_field(row, "chunked_partial_product_non_clifford")
        );
        assert!(json_bool_field(row, "partial_product_count_is_exact_match"));
        assert!(json_bool_field(
            row,
            "single_modular_reduction_after_chunk_accumulation"
        ));
        assert_eq!(json_u64_field(row, "extra_chunk_combine_non_clifford"), 0);
        assert_eq!(
            json_u64_field(row, "chunked_non_qroam_field_mul_bound_non_clifford"),
            json_u64_field(row, "inherited_non_qroam_field_mul_non_clifford")
        );
    }

    let non_clifford = json_object_field(certificate, "non_clifford_derivation");
    assert_eq!(
        json_u64_field(non_clifford, "candidate_total_non_clifford"),
        claim.expected_full_oracle_non_clifford
    );
    assert_eq!(
        json_u64_field(non_clifford, "qroam_chunk_streams"),
        json_u64_field(stream_plan, "whole_oracle_chunk_streams")
    );
    assert_eq!(
        json_u64_field(non_clifford, "qroam_chunk_non_clifford"),
        json_u64_field(non_clifford, "qroam_chunk_streams")
            * json_u64_field(non_clifford, "per_chunk_stream_non_clifford")
    );

    let qubits = json_object_field(certificate, "qubit_derivation");
    assert_eq!(
        json_u64_field(qubits, "field_bits"),
        claim.field_bits as u64
    );
    assert_eq!(
        json_u64_field(qubits, "arithmetic_slot_count"),
        family.arithmetic_slot_count as u64
    );
    assert_eq!(
        json_u64_field(qubits, "lookup_workspace_qubits"),
        family.lookup_workspace_qubits as u64
    );
    assert_eq!(
        json_u64_field(qubits, "candidate_total_logical_qubits"),
        claim.expected_total_logical_qubits
    );

    let counted_ir = json_object_field(certificate, "counted_resource_ir");
    assert_eq!(
        json_string_field(counted_ir, "schema"),
        "compiler-project-reusable-chunk-counted-resource-ir-v1"
    );
    assert!(json_bool_field(counted_ir, "pass"));
    let counted_ir_checks = json_object_field(counted_ir, "checks")
        .as_object()
        .expect("counted_resource_ir checks must be an object");
    assert!(
        counted_ir_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "counted_resource_ir contains a failing check"
    );
    let mut ir_non_clifford_total = 0u64;
    let mut ir_qroam_term_count = 0u64;
    for term in json_array_field(counted_ir, "non_clifford_terms") {
        let instances = json_u64_field(term, "instances");
        let per_instance = json_u64_field(term, "per_instance_non_clifford");
        let total = json_u64_field(term, "total_non_clifford");
        assert_eq!(instances * per_instance, total);
        match json_string_field(term, "category") {
            "arithmetic_control_and_phase_base" => {
                assert_eq!(instances, 1);
                assert_eq!(
                    per_instance,
                    json_u64_field(non_clifford, "base_non_clifford_without_streamed_qroam")
                );
            }
            "qroam_chunk_stream" => {
                ir_qroam_term_count += 1;
                assert_eq!(
                    instances,
                    json_u64_field(stream_plan, "leaf_call_count_total")
                );
                assert_eq!(
                    per_instance,
                    json_u64_field(non_clifford, "per_chunk_stream_non_clifford")
                );
            }
            other => panic!("unexpected counted_resource_ir non-Clifford category: {other}"),
        }
        ir_non_clifford_total += total;
    }
    assert_eq!(
        ir_qroam_term_count,
        json_u64_field(stream_plan, "chunk_streams_per_leaf")
    );
    assert_eq!(
        ir_non_clifford_total,
        claim.expected_full_oracle_non_clifford
    );
    assert_eq!(
        json_u64_field(counted_ir, "recomputed_total_non_clifford"),
        ir_non_clifford_total
    );
    let counted_intervals = json_array_field(counted_ir, "liveness_intervals");
    assert_eq!(
        counted_intervals.len(),
        json_array_field(
            json_object_field(certificate, "executable_liveness"),
            "intervals"
        )
        .len()
    );
    let mut counted_peak_live_qubits = 0u64;
    let mut counted_peak_interval_id = "";
    for interval in counted_intervals {
        let total = json_u64_field(interval, "total_live_qubits");
        if total > counted_peak_live_qubits {
            counted_peak_live_qubits = total;
            counted_peak_interval_id = json_string_field(interval, "interval_id");
        }
    }
    assert_eq!(
        counted_peak_live_qubits,
        claim.expected_total_logical_qubits
    );
    assert_eq!(
        json_u64_field(counted_ir, "recomputed_peak_live_qubits"),
        counted_peak_live_qubits
    );
    assert_eq!(
        json_string_field(counted_ir, "peak_interval_id"),
        counted_peak_interval_id
    );
    let counted_wire_catalog = json_object_field(counted_ir, "wire_catalog")
        .as_object()
        .expect("counted_resource_ir wire_catalog must be an object");
    let mut owner_peak_from_wire_catalog: BTreeMap<String, u64> = BTreeMap::new();
    for interval in counted_intervals {
        let mut seen_live_wires = BTreeSet::new();
        let mut owner_totals: BTreeMap<String, u64> = BTreeMap::new();
        for wire_value in json_array_field(interval, "live_wire_ids") {
            let wire_id = wire_value
                .as_str()
                .expect("counted_resource_ir live wire id must be a string");
            assert!(
                seen_live_wires.insert(wire_id.to_owned()),
                "counted_resource_ir interval double-counts a live wire"
            );
            let wire = counted_wire_catalog
                .get(wire_id)
                .unwrap_or_else(|| panic!("counted_resource_ir live wire missing from catalog: {wire_id}"));
            let owner_id = json_string_field(wire, "owner_id").to_owned();
            let qubits = json_u64_field(wire, "qubits");
            *owner_totals.entry(owner_id).or_insert(0) += qubits;
        }
        let interval_total = owner_totals.values().sum::<u64>();
        assert_eq!(
            interval_total,
            json_u64_field(interval, "total_live_qubits")
        );
        let observed_owner_totals = json_object_field(interval, "owner_live_qubits")
            .as_object()
            .expect("counted_resource_ir interval owner_live_qubits must be an object");
        assert_eq!(observed_owner_totals.len(), owner_totals.len());
        for (owner_id, qubits) in &owner_totals {
            assert_eq!(
                observed_owner_totals
                    .get(owner_id)
                    .and_then(Value::as_u64)
                    .expect("counted_resource_ir interval missing owner total"),
                *qubits
            );
            let current = owner_peak_from_wire_catalog.entry(owner_id.clone()).or_insert(0);
            *current = (*current).max(*qubits);
        }
    }
    let counted_resource_engine = json_object_field(certificate, "counted_resource_engine");
    assert_eq!(
        json_string_field(counted_resource_engine, "schema"),
        "compiler-project-counted-resource-ir-engine-v1"
    );
    assert!(json_bool_field(counted_resource_engine, "pass"));
    assert_eq!(
        json_string_field(counted_resource_engine, "input_schema"),
        json_string_field(counted_ir, "schema")
    );
    assert_eq!(
        json_string_field(counted_resource_engine, "counted_resource_ir_sha256").len(),
        64
    );
    assert_eq!(
        json_u64_field(counted_resource_engine, "term_count"),
        json_array_field(counted_ir, "non_clifford_terms").len() as u64
    );
    assert_eq!(
        json_u64_field(counted_resource_engine, "wire_count"),
        counted_wire_catalog.len() as u64
    );
    assert_eq!(
        json_u64_field(counted_resource_engine, "interval_count"),
        counted_intervals.len() as u64
    );
    assert_eq!(
        json_u64_field(counted_resource_engine, "non_clifford_total_from_terms"),
        ir_non_clifford_total
    );
    assert_eq!(
        json_u64_field(counted_resource_engine, "peak_live_qubits_from_intervals"),
        counted_peak_live_qubits
    );
    assert_eq!(
        json_string_field(counted_resource_engine, "peak_interval_id_from_intervals"),
        counted_peak_interval_id
    );
    assert!(json_array_field(counted_resource_engine, "malformed_term_ids").is_empty());
    assert!(json_array_field(counted_resource_engine, "unknown_live_wire_refs").is_empty());
    assert!(json_array_field(counted_resource_engine, "duplicate_live_wire_refs").is_empty());
    assert!(json_array_field(counted_resource_engine, "interval_sum_mismatches").is_empty());
    let engine_checks = json_object_field(counted_resource_engine, "checks")
        .as_object()
        .expect("counted_resource_engine checks must be an object");
    assert!(
        engine_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "counted_resource_engine contains a failing check"
    );
    let engine_owner_peak = json_object_field(
        counted_resource_engine,
        "owner_peak_live_qubits_from_intervals",
    )
    .as_object()
    .expect("counted_resource_engine owner peaks must be an object");
    assert_eq!(engine_owner_peak.len(), owner_peak_from_wire_catalog.len());
    for (owner_id, qubits) in &owner_peak_from_wire_catalog {
        assert_eq!(
            engine_owner_peak
                .get(owner_id)
                .and_then(Value::as_u64)
                .expect("counted_resource_engine missing owner peak"),
            *qubits
        );
    }

    let owner_capacity = json_object_field(certificate, "owner_capacity");
    assert_eq!(
        json_u64_field(owner_capacity, "required_global_peak_qubits"),
        claim.expected_total_logical_qubits
    );
    assert_eq!(
        json_u64_field(owner_capacity, "capacity_global_peak_qubits"),
        claim.expected_total_logical_qubits
    );
    let mut owner_ids = BTreeSet::new();
    let mut required_peak_total = 0u64;
    let mut capacity_peak_total = 0u64;
    for row in json_array_field(owner_capacity, "rows") {
        let owner_id = json_string_field(row, "owner_id");
        owner_ids.insert(owner_id.to_owned());
        let capacity = json_u64_field(row, "logical_qubits");
        let required = json_u64_field(row, "required_peak_qubits");
        assert!(json_bool_field(row, "capacity_pass"));
        assert!(capacity >= required);
        required_peak_total += required;
        capacity_peak_total += capacity;
    }
    assert_eq!(
        owner_ids,
        BTreeSet::from([
            "arithmetic_slot_register_file".to_owned(),
            "control_slot_register_file".to_owned(),
            "lookup_workspace".to_owned(),
            "phase_shell_live_register".to_owned(),
        ])
    );
    assert_eq!(required_peak_total, claim.expected_total_logical_qubits);
    assert_eq!(capacity_peak_total, claim.expected_total_logical_qubits);

    let executable_liveness = json_object_field(certificate, "executable_liveness");
    assert_eq!(
        json_string_field(executable_liveness, "schema"),
        "compiler-project-reusable-chunk-executable-liveness-v1"
    );
    assert!(json_bool_field(executable_liveness, "pass"));
    let liveness_checks = json_object_field(executable_liveness, "checks")
        .as_object()
        .expect("executable liveness checks must be an object");
    assert!(
        liveness_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "executable liveness contains a failing check"
    );
    assert!(json_bool_field(
        json_object_field(executable_liveness, "checks"),
        "qroam_target_and_qchunk_are_concurrently_live"
    ));
    assert!(json_bool_field(
        json_object_field(executable_liveness, "checks"),
        "no_full_coordinate_lane_wire_is_live"
    ));
    assert_eq!(
        json_u64_field(executable_liveness, "global_peak_live_qubits"),
        claim.expected_total_logical_qubits
    );
    assert!(
        json_array_field(executable_liveness, "duplicate_owner_wires").is_empty(),
        "executable liveness must not assign a wire to multiple owners"
    );
    assert!(
        json_array_field(executable_liveness, "unknown_owner_wires").is_empty(),
        "executable liveness must not use unknown owners"
    );
    assert!(
        json_array_field(executable_liveness, "over_capacity_owners").is_empty(),
        "executable liveness owner peaks must fit capacity"
    );
    let liveness_owner_capacity = json_object_field(executable_liveness, "owner_capacity_qubits")
        .as_object()
        .expect("executable liveness owner_capacity_qubits must be an object");
    let liveness_owner_peak = json_object_field(executable_liveness, "owner_peak_live_qubits")
        .as_object()
        .expect("executable liveness owner_peak_live_qubits must be an object");
    assert_eq!(liveness_owner_capacity.len(), owner_ids.len());
    assert_eq!(liveness_owner_peak.len(), owner_ids.len());
    for row in json_array_field(owner_capacity, "rows") {
        let owner_id = json_string_field(row, "owner_id");
        let capacity = json_u64_field(row, "logical_qubits");
        assert_eq!(
            liveness_owner_capacity
                .get(owner_id)
                .and_then(Value::as_u64),
            Some(capacity)
        );
        assert_eq!(
            liveness_owner_peak.get(owner_id).and_then(Value::as_u64),
            Some(capacity)
        );
    }
    let wire_catalog = json_object_field(executable_liveness, "wire_catalog")
        .as_object()
        .expect("executable liveness wire_catalog must be an object");
    assert_eq!(
        counted_wire_catalog, wire_catalog,
        "counted_resource_ir and executable_liveness must use the same wire catalog"
    );
    let executable_intervals = json_array_field(executable_liveness, "intervals");
    assert_eq!(
        counted_intervals.len(),
        executable_intervals.len(),
        "counted_resource_ir and executable_liveness must have the same interval count"
    );
    for (counted_interval, executable_interval) in counted_intervals.iter().zip(executable_intervals) {
        assert_eq!(
            json_string_field(counted_interval, "interval_id"),
            json_string_field(executable_interval, "interval_id")
        );
        assert_eq!(
            json_array_field(counted_interval, "live_wire_ids"),
            json_array_field(executable_interval, "live_wire_ids")
        );
        assert_eq!(
            json_object_field(counted_interval, "owner_live_qubits"),
            json_object_field(executable_interval, "owner_live_qubits")
        );
        assert_eq!(
            json_u64_field(counted_interval, "total_live_qubits"),
            json_u64_field(executable_interval, "total_live_qubits")
        );
    }
    for (wire_id, wire) in wire_catalog {
        assert_eq!(json_string_field(wire, "wire_id"), wire_id);
        let owner_id = json_string_field(wire, "owner_id");
        let qubits = json_u64_field(wire, "qubits");
        assert!(owner_ids.contains(owner_id));
        assert!(qubits > 0);
        assert!(
            wire_id != "lookup_x" && wire_id != "lookup_y" && wire_id != "lookup_x_plus_y",
            "full lookup coordinate lanes must not be live"
        );
    }
    let mut recomputed_owner_peak: BTreeMap<String, u64> = BTreeMap::new();
    let mut peak_total = 0u64;
    let mut peak_interval_id = String::new();
    let mut qchunk_qroam_concurrent = false;
    for interval in json_array_field(executable_liveness, "intervals") {
        let interval_id = json_string_field(interval, "interval_id");
        let mut seen_live_wires = BTreeSet::new();
        let mut interval_owner_live: BTreeMap<String, u64> = BTreeMap::new();
        let mut interval_total = 0u64;
        let mut interval_has_qchunk = false;
        let mut interval_has_qroam_target = false;
        for wire_id_value in json_array_field(interval, "live_wire_ids") {
            let wire_id = wire_id_value
                .as_str()
                .expect("live_wire_ids entries must be strings");
            assert!(
                seen_live_wires.insert(wire_id.to_owned()),
                "executable_liveness interval double-counts a live wire"
            );
            let wire = wire_catalog
                .get(wire_id)
                .expect("live_wire_ids entry must exist in wire_catalog");
            let owner_id = json_string_field(wire, "owner_id");
            let qubits = json_u64_field(wire, "qubits");
            if wire_id == "qchunk" {
                interval_has_qchunk = true;
                assert_eq!(qubits, claim.field_bits as u64);
            }
            if wire_id.starts_with("qroam_chunk_target__") {
                interval_has_qroam_target = true;
                assert_eq!(
                    qubits,
                    json_u64_field(qroam_model, "target_register_qubits")
                );
            }
            *interval_owner_live.entry(owner_id.to_owned()).or_insert(0) += qubits;
            interval_total += qubits;
        }
        let recorded_owner_live = json_object_field(interval, "owner_live_qubits")
            .as_object()
            .expect("interval owner_live_qubits must be an object");
        assert_eq!(recorded_owner_live.len(), interval_owner_live.len());
        for (owner_id, live_qubits) in &interval_owner_live {
            assert_eq!(
                recorded_owner_live.get(owner_id).and_then(Value::as_u64),
                Some(*live_qubits)
            );
            let entry = recomputed_owner_peak.entry(owner_id.clone()).or_insert(0);
            *entry = (*entry).max(*live_qubits);
        }
        assert_eq!(
            json_u64_field(interval, "total_live_qubits"),
            interval_total
        );
        if interval_total > peak_total {
            peak_total = interval_total;
            peak_interval_id = interval_id.to_owned();
        }
        qchunk_qroam_concurrent |= interval_has_qchunk && interval_has_qroam_target;
    }
    assert!(qchunk_qroam_concurrent);
    assert_eq!(peak_total, claim.expected_total_logical_qubits);
    assert_eq!(
        json_string_field(executable_liveness, "global_peak_interval_id"),
        peak_interval_id
    );
    for owner_id in &owner_ids {
        let capacity = liveness_owner_capacity
            .get(owner_id)
            .and_then(Value::as_u64)
            .expect("missing executable liveness owner capacity");
        assert_eq!(recomputed_owner_peak.get(owner_id).copied(), Some(capacity));
    }

    let resource_contract_engine = json_object_field(certificate, "resource_contract_engine");
    assert_eq!(
        json_string_field(resource_contract_engine, "schema"),
        "compiler-project-resource-contract-engine-v1"
    );
    assert!(json_bool_field(resource_contract_engine, "pass"));
    assert_eq!(
        json_u64_field(resource_contract_engine, "wire_count"),
        wire_catalog.len() as u64
    );
    assert_eq!(
        json_u64_field(resource_contract_engine, "interval_count"),
        executable_intervals.len() as u64
    );
    assert_eq!(
        json_u64_field(resource_contract_engine, "peak_live_qubits"),
        claim.expected_total_logical_qubits
    );
    assert_eq!(
        json_string_field(resource_contract_engine, "peak_interval_id"),
        json_string_field(executable_liveness, "global_peak_interval_id")
    );
    assert!(json_array_field(resource_contract_engine, "over_capacity_owners").is_empty());
    assert!(json_array_field(resource_contract_engine, "missing_capacity_owners").is_empty());
    assert!(json_array_field(resource_contract_engine, "stale_required_owner_rows").is_empty());
    let contract_checks = json_object_field(resource_contract_engine, "checks")
        .as_object()
        .expect("resource_contract_engine checks must be an object");
    assert!(
        contract_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "resource_contract_engine contains a failing check"
    );
    let contract_owner_peaks = json_object_field(resource_contract_engine, "owner_peak_live_qubits")
        .as_object()
        .expect("resource_contract_engine owner peaks must be an object");
    let contract_owner_capacity = json_object_field(resource_contract_engine, "owner_capacity_qubits")
        .as_object()
        .expect("resource_contract_engine owner capacity must be an object");
    assert_eq!(contract_owner_peaks, liveness_owner_peak);
    assert_eq!(contract_owner_capacity, liveness_owner_capacity);

    let checks = json_object_field(certificate, "checks")
        .as_object()
        .expect("reusable chunk lowering checks must be an object");
    assert!(
        checks.values().all(|value| value.as_bool() == Some(true)),
        "reusable chunk lowering contains a failing check"
    );
}

pub fn run_prepared_attestation(input: &PreparedAttestationInput) -> PublicValues {
    assert_eq!(input.schema, "compiler-project-zkp-attestation-input-v5");
    assert_eq!(input.document_digest_scheme, DIGEST_SCHEME);

    validate_committed_value_document(
        &input.claim_document,
        "attestation_claim",
        &input.claim_sha256,
    );
    validate_committed_value_document(
        &input.leaf_document,
        if input.selected_family_name.contains("reusable_chunk") {
            "reusable_chunk_tail_leaf"
        } else {
            "streamed_lookup_tail_leaf"
        },
        &input.leaf_sha256,
    );
    validate_committed_value_document(
        &input.family_document,
        "compiler_family_summary",
        &input.family_sha256,
    );
    validate_committed_value_document(
        &input.case_corpus_document,
        "pointadd_case_corpus",
        &input.case_corpus_sha256,
    );
    validate_committed_value_document(
        &input.resource_certificate_document,
        if input.selected_family_name.contains("reusable_chunk") {
            "reusable_chunk_lowering"
        } else {
            "resource_liveness_certificate"
        },
        &input.resource_certificate_sha256,
    );
    validate_committed_value_document(
        &input.compiler_parameters_document,
        "compiler_parameters",
        &input.compiler_parameters_sha256,
    );
    let compiler_parameters = &input.compiler_parameters_document.payload.0;
    assert_eq!(
        json_string_field(compiler_parameters, "schema"),
        "compiler-project-parameters-v1"
    );
    assert!(json_bool_field(compiler_parameters, "pass"));
    assert_eq!(
        json_string_field(compiler_parameters, "parameter_digest_sha256").len(),
        64
    );
    let compiler_parameter_checks = json_object_field(compiler_parameters, "checks")
        .as_object()
        .expect("compiler parameter checks must be an object");
    assert!(
        compiler_parameter_checks
            .values()
            .all(|value| value.as_bool() == Some(true)),
        "compiler parameter document contains a failing check"
    );

    let claim_document: ClaimDocument = decode_committed_payload(&input.claim_document);
    let leaf_document: LeafDocument = decode_committed_payload(&input.leaf_document);
    let family_document: FamilyDocument = decode_committed_payload(&input.family_document);
    let case_corpus_document: CaseCorpusDocument =
        decode_committed_payload(&input.case_corpus_document);

    assert_eq!(
        input.claim_summary,
        claim_summary_from_claim(&claim_document)
    );
    assert_eq!(
        input.family_summary,
        family_summary_from_family(&family_document)
    );
    assert_eq!(
        input.prepared_case_corpus,
        prepared_case_corpus_from_case_corpus(&case_corpus_document)
    );
    assert_eq!(input.prepared_leaf, compile_leaf(&leaf_document));
    validate_proof_register_contract(&input.proof_register_contract.0, &input.prepared_leaf);
    assert_eq!(claim_document.selected_family_name, family_document.name);
    assert_eq!(
        claim_document.expected_case_count,
        case_corpus_document.case_count
    );

    let claim = &input.claim_summary;
    let family = &input.family_summary;
    if input.resource_certificate_document.document_type == "reusable_chunk_lowering" {
        validate_reusable_chunk_lowering(
            &input.resource_certificate_document.payload.0,
            claim,
            family,
        );
    } else {
        validate_resource_certificate(
            &input.resource_certificate_document.payload.0,
            claim,
            family,
        );
    }
    let case_corpus = &input.prepared_case_corpus;
    let compiled_cases = compile_prepared_case_corpus(case_corpus);

    assert_eq!(input.selected_family_name, family.name);
    assert_eq!(claim.expected_case_count, case_corpus.case_count);

    assert_eq!(
        claim.non_clifford_formula.arithmetic_leaf_non_clifford,
        family.arithmetic_leaf_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.per_leaf_lookup_non_clifford,
        family.per_leaf_lookup_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.direct_seed_non_clifford,
        family.direct_seed_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.leaf_call_count_total,
        claim.leaf_call_count_total
    );
    assert_eq!(
        claim.non_clifford_formula.arithmetic_component,
        family.arithmetic_leaf_non_clifford * claim.leaf_call_count_total as u64
    );
    assert_eq!(
        claim.non_clifford_formula.lookup_component,
        family.per_leaf_lookup_non_clifford * claim.leaf_call_count_total as u64
    );
    assert_eq!(
        claim.non_clifford_formula.reconstructed_total,
        claim.non_clifford_formula.arithmetic_component
            + claim.non_clifford_formula.lookup_component
            + family.direct_seed_non_clifford
    );
    assert_eq!(
        claim.non_clifford_formula.reconstructed_total,
        family.full_oracle_non_clifford
    );
    assert_eq!(
        claim.expected_full_oracle_non_clifford,
        family.full_oracle_non_clifford
    );

    assert_eq!(claim.logical_qubit_formula.field_bits, claim.field_bits);
    assert_eq!(
        claim.logical_qubit_formula.arithmetic_slot_count,
        family.arithmetic_slot_count
    );
    assert_eq!(
        claim.logical_qubit_formula.control_slot_count,
        family.control_slot_count
    );
    assert_eq!(
        claim.logical_qubit_formula.borrowed_interface_qubits,
        family.borrowed_interface_qubits
    );
    assert_eq!(
        claim.logical_qubit_formula.lookup_workspace_qubits,
        family.lookup_workspace_qubits
    );
    assert_eq!(
        claim.logical_qubit_formula.live_phase_bits,
        family.live_phase_bits
    );
    assert_eq!(
        claim.logical_qubit_formula.arithmetic_component,
        claim.field_bits as u64 * family.arithmetic_slot_count as u64
    );
    assert_eq!(
        claim.logical_qubit_formula.reconstructed_total,
        claim.logical_qubit_formula.arithmetic_component
            + family.control_slot_count as u64
            + family.borrowed_interface_qubits as u64
            + family.lookup_workspace_qubits as u64
            + family.live_phase_bits as u64
    );
    assert_eq!(
        claim.logical_qubit_formula.reconstructed_total,
        family.total_logical_qubits
    );
    assert_eq!(
        claim.expected_total_logical_qubits,
        family.total_logical_qubits
    );

    let modulus = parse_hex_uint(&case_corpus.field_modulus_hex);
    let mut passed_case_count = 0u32;
    for case in &compiled_cases {
        let observed = execute_leaf(
            &input.prepared_leaf,
            case.accumulator.clone(),
            case.lookup.clone(),
            &modulus,
        );
        let reference =
            add_affine_projective(case.accumulator.clone(), case.lookup.clone(), &modulus);
        assert!(
            projective_matches_affine(&reference, &case.expected, &modulus),
            "expected group-law output mismatch on {}",
            case.case_id
        );
        assert!(
            projective_matches_affine(&observed, &case.expected, &modulus),
            "leaf output mismatch on {}",
            case.case_id
        );
        passed_case_count += 1;
    }
    assert_eq!(passed_case_count, case_corpus.case_count);

    PublicValues {
        schema: "compiler-project-zkp-attestation-public-v2".to_owned(),
        document_digest_scheme: input.document_digest_scheme.clone(),
        selected_family_name: family.name.clone(),
        claim_sha256: input.claim_sha256.clone(),
        leaf_sha256: input.leaf_sha256.clone(),
        family_sha256: input.family_sha256.clone(),
        case_corpus_sha256: input.case_corpus_sha256.clone(),
        resource_certificate_sha256: input.resource_certificate_sha256.clone(),
        expected_full_oracle_non_clifford: claim.expected_full_oracle_non_clifford,
        expected_total_logical_qubits: claim.expected_total_logical_qubits,
        case_count: case_corpus.case_count,
        passed_case_count,
    }
}

pub fn public_values_bytes(values: &PublicValues) -> Vec<u8> {
    serde_json::to_vec(values).expect("failed to serialize public values")
}

pub fn public_values_from_bytes(bytes: &[u8]) -> PublicValues {
    serde_json::from_slice(bytes).expect("failed to deserialize public values")
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixtureArtifactMetadata {
    pub path: String,
    pub sha256: String,
    pub size_bytes: u64,
}

pub fn fixture_json(
    public_values: &PublicValues,
    verifying_key: &str,
    proof_hex: Option<&str>,
    system: &str,
    input_artifact: Option<&FixtureArtifactMetadata>,
    proof_artifact: Option<&FixtureArtifactMetadata>,
    verifier_key_artifact: Option<&FixtureArtifactMetadata>,
) -> String {
    serde_json::to_string_pretty(&serde_json::json!({
        "schema": "compiler-project-zkp-attestation-fixture-v1",
        "proof_system": system,
        "verification_key": verifying_key,
        "public_values": public_values,
        "input_path": input_artifact.map(|metadata| metadata.path.clone()),
        "input_sha256": input_artifact.map(|metadata| metadata.sha256.clone()),
        "input_size_bytes": input_artifact.map(|metadata| metadata.size_bytes),
        "proof": proof_hex,
        "proof_path": proof_artifact.map(|metadata| metadata.path.clone()),
        "proof_sha256": proof_artifact.map(|metadata| metadata.sha256.clone()),
        "proof_size_bytes": proof_artifact.map(|metadata| metadata.size_bytes),
        "verifier_key_path": verifier_key_artifact.map(|metadata| metadata.path.clone()),
        "verifier_key_sha256": verifier_key_artifact.map(|metadata| metadata.sha256.clone()),
        "verifier_key_size_bytes": verifier_key_artifact.map(|metadata| metadata.size_bytes),
    }))
    .expect("failed to serialize proof fixture")
}

#[cfg(test)]
mod tests {
    use super::{
        fixture_json, run_prepared_attestation, semantic_payload_sha256, FixtureArtifactMetadata,
        PreparedAttestationInput,
    };

    fn checked_input() -> PreparedAttestationInput {
        serde_json::from_str(include_str!(
            "../../../artifacts/zkp_attestation_input.json"
        ))
        .expect("failed to parse checked-in prepared attestation input")
    }

    fn checked_reusable_chunk_input() -> PreparedAttestationInput {
        serde_json::from_str(include_str!(
            "../../../artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json"
        ))
        .expect("failed to parse checked-in reusable-chunk prepared attestation input")
    }

    fn refresh_resource_certificate_digest(input: &mut PreparedAttestationInput) {
        let digest = semantic_payload_sha256(
            &input.resource_certificate_document.document_type,
            &input.resource_certificate_document.payload,
        );
        input.resource_certificate_document.sha256 = digest.clone();
        input.resource_certificate_sha256 = digest;
    }

    #[test]
    fn native_run_prepared_attestation_matches_checked_in_input_shape() {
        let input = checked_input();
        let public_values = run_prepared_attestation(&input);
        assert_eq!(
            public_values.schema,
            "compiler-project-zkp-attestation-public-v2"
        );
        assert_eq!(public_values.case_count, 8);
        assert_eq!(public_values.passed_case_count, 8);
    }

    #[test]
    fn native_run_prepared_attestation_accepts_reusable_chunk_candidate() {
        let input = checked_reusable_chunk_input();
        let public_values = run_prepared_attestation(&input);
        assert_eq!(
            public_values.selected_family_name,
            "folded_standard_qroam_reusable_chunked_coordinate_v1__reusable_chunk_tail_leaf_v1__semiclassical_qft_v1"
        );
        assert_eq!(
            public_values.expected_full_oracle_non_clifford,
            input.claim_summary.expected_full_oracle_non_clifford
        );
        assert_eq!(
            public_values.expected_total_logical_qubits,
            input.claim_summary.expected_total_logical_qubits
        );
        assert_eq!(public_values.case_count, 8);
        assert_eq!(public_values.passed_case_count, 8);
    }

    #[test]
    fn bincode_roundtrip_checked_in_prepared_input_preserves_attestation_behavior() {
        let input = checked_input();
        let bytes = bincode::serialize(&input)
            .expect("failed to bincode-serialize prepared attestation input");
        let roundtrip: PreparedAttestationInput = bincode::deserialize(&bytes)
            .expect("failed to bincode-deserialize prepared attestation input");
        let original_public_values = run_prepared_attestation(&input);
        let roundtrip_public_values = run_prepared_attestation(&roundtrip);
        assert_eq!(
            serde_json::to_value(original_public_values)
                .expect("failed to serialize original public values"),
            serde_json::to_value(roundtrip_public_values)
                .expect("failed to serialize roundtrip public values"),
        );
    }

    #[test]
    fn json_roundtrip_checked_in_prepared_input_preserves_shape() {
        let input = checked_input();
        let json =
            serde_json::to_string(&input).expect("failed to serialize prepared attestation input");
        let roundtrip: PreparedAttestationInput =
            serde_json::from_str(&json).expect("failed to deserialize prepared attestation input");
        assert_eq!(
            serde_json::to_value(&input).expect("failed to serialize original prepared input"),
            serde_json::to_value(&roundtrip).expect("failed to serialize roundtrip prepared input"),
        );
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_stale_claim_digest() {
        let mut input = checked_input();
        input.claim_sha256 = "00".repeat(32);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_stale_leaf_digest() {
        let mut input = checked_input();
        input.leaf_sha256 = "00".repeat(32);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_stale_family_digest() {
        let mut input = checked_input();
        input.family_sha256 = "00".repeat(32);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_stale_case_corpus_digest() {
        let mut input = checked_input();
        input.case_corpus_sha256 = "00".repeat(32);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_stale_resource_certificate_digest() {
        let mut input = checked_input();
        input.resource_certificate_sha256 = "00".repeat(32);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_stale_compiler_parameters_digest() {
        let mut input = checked_input();
        input.compiler_parameters_sha256 = "00".repeat(32);
        run_prepared_attestation(&input);
    }

    #[test]
    fn fixture_json_binds_prepared_input_artifact() {
        let input = checked_reusable_chunk_input();
        let public_values = run_prepared_attestation(&input);
        let input_artifact = FixtureArtifactMetadata {
            path: "compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json".to_owned(),
            sha256: "a".repeat(64),
            size_bytes: 123,
        };
        let fixture = serde_json::from_str::<serde_json::Value>(&fixture_json(
            &public_values,
            "0x00",
            None,
            "core",
            Some(&input_artifact),
            None,
            None,
        ))
        .expect("fixture JSON must parse");
        assert_eq!(fixture["input_path"], input_artifact.path);
        assert_eq!(fixture["input_sha256"], input_artifact.sha256);
        assert_eq!(fixture["input_size_bytes"], input_artifact.size_bytes);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_mutated_committed_claim_payload() {
        let mut input = checked_input();
        input.claim_document.payload.0["expected_total_logical_qubits"] = serde_json::json!(1045);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_mutated_prepared_leaf() {
        let mut input = checked_input();
        input.prepared_leaf.register_count += 1;
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_forged_proof_register_contract() {
        let mut input = checked_reusable_chunk_input();
        input.proof_register_contract.0["register_rows"][7]["resource_class"] =
            serde_json::json!("semantic_lookup_constant");
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_mutated_prepared_case_corpus() {
        let mut input = checked_input();
        input.prepared_case_corpus.cases[0].case_id = "forged_case".to_owned();
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_mutated_resource_leaf_sigma() {
        let mut input = checked_input();
        input.resource_certificate_document.payload.0["primitive_oracle_ir"]["leaf_sigma"][0]
            ["primitive_counts_total"]["ccx"] = serde_json::json!(0);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_forged_arithmetic_operation_ir() {
        let mut input = checked_input();
        input.resource_certificate_document.payload.0["arithmetic_operation_ir"]
            ["leaf_arithmetic_summary"]["rows"][0]["primitive_counts_total"]["ccx"] =
            serde_json::json!(0);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_forged_arithmetic_operation_ir_block_total() {
        let mut input = checked_input();
        input.resource_certificate_document.payload.0["arithmetic_operation_ir"]["kernels"][0]
            ["stages"][0]["blocks"][0]["primitive_counts_total"]["ccx"] =
            serde_json::json!(0);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_underprovisioned_owner_capacity() {
        let mut input = checked_input();
        input.resource_certificate_document.payload.0["derived_owner_capacity"]["rows"][0]
            ["capacity_qubits"] = serde_json::json!(767);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_liveness_false_check() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["executable_liveness"]["checks"]
            ["qroam_target_and_qchunk_are_concurrently_live"] = serde_json::json!(false);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_counted_resource_ir_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["counted_resource_ir"]
            ["non_clifford_terms"][1]["total_non_clifford"] = serde_json::json!(65_535);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_resource_engine_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["counted_resource_engine"]
            ["peak_live_qubits_from_intervals"] = serde_json::json!(1198);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_interval_double_count() {
        let mut input = checked_reusable_chunk_input();
        let first_wire = input.resource_certificate_document.payload.0["counted_resource_ir"]
            ["liveness_intervals"][0]["live_wire_ids"][0]
            .clone();
        input.resource_certificate_document.payload.0["counted_resource_ir"]
            ["liveness_intervals"][0]["live_wire_ids"]
            .as_array_mut()
            .expect("live_wire_ids must be an array")
            .push(first_wire);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_counted_executable_liveness_drift() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["counted_resource_ir"]
            ["liveness_intervals"][0]["live_wire_ids"]
            .as_array_mut()
            .expect("live_wire_ids must be an array")
            .push(serde_json::json!("folded_lookup_control_workspace"));
        input.resource_certificate_document.payload.0["counted_resource_ir"]
            ["liveness_intervals"][0]["owner_live_qubits"]["lookup_workspace"] =
            serde_json::json!(18);
        input.resource_certificate_document.payload.0["counted_resource_ir"]
            ["liveness_intervals"][0]["total_live_qubits"] = serde_json::json!(787);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_qroam_primitive_count_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["qroam_primitive_certificate"]
            ["traversed_counts"]["per_stream_non_clifford"] = serde_json::json!(65_535);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_qroam_primitive_workspace_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["qroam_primitive_certificate"]
            ["wire_catalog"]["target_register"]["qubits"] = serde_json::json!(154);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_qroam_reference_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["qroam_reference_crosscheck"]
            ["selected_reference"]["target_plus_junk_qubits"] = serde_json::json!(154);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_qroam_reference_formula_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["qroam_reference_crosscheck"]
            ["ledger_selected_reference"]["junk_register_qubits"] = serde_json::json!(1);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_proof_register_contract_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.proof_register_contract.0["register_rows"][0]["resource_class"] =
            serde_json::json!("unclassified");
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_modular_stage_count_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["modular_arithmetic_certificate"]
            ["field_mul_stage_count_certificate"]["observed_total_ccx"] = serde_json::json!(71_491);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_modular_opcode_count_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["modular_arithmetic_certificate"]
            ["opcode_count_certificate"]["observed_non_clifford_per_opcode"]["field_add"] =
            serde_json::json!(255);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_modular_reduced_case_forgery() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["modular_arithmetic_certificate"]
            ["reduced_width_exhaustive_cases"][0]["pass"] = serde_json::json!(false);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }

    #[test]
    #[should_panic]
    fn prepared_attestation_rejects_reusable_chunk_liveness_underreported_qroam_target() {
        let mut input = checked_reusable_chunk_input();
        input.resource_certificate_document.payload.0["executable_liveness"]["wire_catalog"]
            ["qroam_chunk_target__lookup_x__chunk_0"]["qubits"] = serde_json::json!(154);
        input.resource_certificate_document.payload.0["executable_liveness"]["intervals"][3]
            ["owner_live_qubits"]["lookup_workspace"] = serde_json::json!(172);
        input.resource_certificate_document.payload.0["executable_liveness"]["intervals"][3]
            ["total_live_qubits"] = serde_json::json!(1198);
        refresh_resource_certificate_digest(&mut input);
        run_prepared_attestation(&input);
    }
}
