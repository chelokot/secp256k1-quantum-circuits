use num_bigint::BigUint;
use num_traits::{Num, One, ToPrimitive, Zero};
use serde::{
    de::Deserializer,
    ser::{SerializeSeq, SerializeStruct, Serializer},
    Deserialize, Serialize,
};
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NonCliffordFormula {
    pub arithmetic_leaf_non_clifford: u64,
    pub per_leaf_lookup_non_clifford: u64,
    pub direct_seed_non_clifford: u64,
    pub leaf_call_count_total: u32,
    pub arithmetic_component: u64,
    pub lookup_component: u64,
    pub reconstructed_total: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogicalQubitFormula {
    pub field_bits: u32,
    pub arithmetic_slot_count: u32,
    pub control_slot_count: u32,
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
    pub instructions: Vec<Instruction>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct Instruction {
    pub pc: u32,
    pub op: String,
    pub comment: Option<String>,
    pub dst: Option<String>,
    pub src: Option<InstructionSource>,
    pub flag: Option<String>,
    pub const_value: Option<u64>,
}

#[derive(Debug, Clone)]
pub enum InstructionSource {
    Register(String),
    Pair([String; 2]),
    FlagBit { flags: String, bit: u64 },
    Lookup { table: String, key: String },
}

#[derive(Serialize, Deserialize)]
#[serde(untagged)]
enum HumanInstructionSource {
    Register(String),
    Pair([String; 2]),
    FlagBit { flags: String, bit: u64 },
    Lookup { table: String, key: String },
}

#[derive(Serialize, Deserialize)]
enum BinaryInstructionSource {
    Register(String),
    Pair([String; 2]),
    FlagBit { flags: String, bit: u64 },
    Lookup { table: String, key: String },
}

#[derive(Serialize, Deserialize)]
struct HumanInstruction {
    pc: u32,
    op: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    comment: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    dst: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    src: Option<InstructionSource>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    flag: Option<String>,
    #[serde(rename = "const", default, skip_serializing_if = "Option::is_none")]
    const_value: Option<u64>,
}

#[derive(Serialize, Deserialize)]
struct BinaryInstruction {
    pc: u32,
    op: String,
    comment: Option<String>,
    dst: Option<String>,
    src: Option<InstructionSource>,
    flag: Option<String>,
    const_value: Option<u64>,
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
                InstructionSource::Register(register) => BinaryInstructionSource::Register(register.clone()),
                InstructionSource::Pair(pair) => BinaryInstructionSource::Pair(pair.clone()),
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
                HumanInstructionSource::FlagBit { flags, bit } => InstructionSource::FlagBit { flags, bit },
                HumanInstructionSource::Lookup { table, key } => InstructionSource::Lookup { table, key },
            })
        } else {
            let source = BinaryInstructionSource::deserialize(deserializer)?;
            Ok(match source {
                BinaryInstructionSource::Register(register) => InstructionSource::Register(register),
                BinaryInstructionSource::Pair(pair) => InstructionSource::Pair(pair),
                BinaryInstructionSource::FlagBit { flags, bit } => InstructionSource::FlagBit { flags, bit },
                BinaryInstructionSource::Lookup { table, key } => InstructionSource::Lookup { table, key },
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PointAddCase {
    pub case_id: String,
    pub category: String,
    pub accumulator: Option<AffineEncoding>,
    pub lookup: Option<AffineEncoding>,
    pub expected: Option<AffineEncoding>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AffineEncoding {
    pub x_hex: String,
    pub y_hex: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreparedClaimSummary {
    pub field_bits: u32,
    pub leaf_call_count_total: u32,
    pub expected_full_oracle_non_clifford: u64,
    pub expected_total_logical_qubits: u64,
    pub expected_case_count: u32,
    pub non_clifford_formula: NonCliffordFormula,
    pub logical_qubit_formula: LogicalQubitFormula,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreparedFamilySummary {
    pub name: String,
    pub arithmetic_leaf_non_clifford: u64,
    pub direct_seed_non_clifford: u64,
    pub per_leaf_lookup_non_clifford: u64,
    pub full_oracle_non_clifford: u64,
    pub arithmetic_slot_count: u32,
    pub control_slot_count: u32,
    pub lookup_workspace_qubits: u32,
    pub live_phase_bits: u32,
    pub total_logical_qubits: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    pub expected_full_oracle_non_clifford: u64,
    pub expected_total_logical_qubits: u64,
    pub case_count: u32,
    pub passed_case_count: u32,
}

type PointAffine = Option<(BigUint, BigUint)>;
type PointProj = (BigUint, BigUint, BigUint);
type RegisterId = usize;

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    instructions: Vec<CompiledInstruction>,
}

#[derive(Debug, Clone)]
pub enum CompiledInstruction {
    Copy { dst: RegisterId, src: RegisterId },
    BoolFromFlag { dst: RegisterId, flags: RegisterId, bit: u64 },
    ClearBoolFromFlag { dst: RegisterId, flags: RegisterId, bit: u64 },
    FieldMul { dst: RegisterId, left: RegisterId, right: RegisterId },
    FieldAdd { dst: RegisterId, left: RegisterId, right: RegisterId },
    FieldSub { dst: RegisterId, left: RegisterId, right: RegisterId },
    MulConst { dst: RegisterId, src: RegisterId, constant: u64 },
    SelectFieldIfFlag {
        dst: RegisterId,
        flag: RegisterId,
        when_nonzero: RegisterId,
        when_zero: RegisterId,
    },
}

#[derive(Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum HumanCompiledInstruction {
    Copy { dst: RegisterId, src: RegisterId },
    BoolFromFlag { dst: RegisterId, flags: RegisterId, bit: u64 },
    ClearBoolFromFlag { dst: RegisterId, flags: RegisterId, bit: u64 },
    FieldMul { dst: RegisterId, left: RegisterId, right: RegisterId },
    FieldAdd { dst: RegisterId, left: RegisterId, right: RegisterId },
    FieldSub { dst: RegisterId, left: RegisterId, right: RegisterId },
    MulConst { dst: RegisterId, src: RegisterId, constant: u64 },
    SelectFieldIfFlag {
        dst: RegisterId,
        flag: RegisterId,
        when_nonzero: RegisterId,
        when_zero: RegisterId,
    },
}

#[derive(Serialize, Deserialize)]
enum BinaryCompiledInstruction {
    Copy { dst: RegisterId, src: RegisterId },
    BoolFromFlag { dst: RegisterId, flags: RegisterId, bit: u64 },
    ClearBoolFromFlag { dst: RegisterId, flags: RegisterId, bit: u64 },
    FieldMul { dst: RegisterId, left: RegisterId, right: RegisterId },
    FieldAdd { dst: RegisterId, left: RegisterId, right: RegisterId },
    FieldSub { dst: RegisterId, left: RegisterId, right: RegisterId },
    MulConst { dst: RegisterId, src: RegisterId, constant: u64 },
    SelectFieldIfFlag {
        dst: RegisterId,
        flag: RegisterId,
        when_nonzero: RegisterId,
        when_zero: RegisterId,
    },
}

impl From<&CompiledInstruction> for HumanCompiledInstruction {
    fn from(value: &CompiledInstruction) -> Self {
        match value {
            CompiledInstruction::Copy { dst, src } => Self::Copy { dst: *dst, src: *src },
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
        }
    }
}

impl From<HumanCompiledInstruction> for CompiledInstruction {
    fn from(value: HumanCompiledInstruction) -> Self {
        match value {
            HumanCompiledInstruction::Copy { dst, src } => Self::Copy { dst, src },
            HumanCompiledInstruction::BoolFromFlag { dst, flags, bit } => Self::BoolFromFlag { dst, flags, bit },
            HumanCompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                Self::ClearBoolFromFlag { dst, flags, bit }
            }
            HumanCompiledInstruction::FieldMul { dst, left, right } => Self::FieldMul { dst, left, right },
            HumanCompiledInstruction::FieldAdd { dst, left, right } => Self::FieldAdd { dst, left, right },
            HumanCompiledInstruction::FieldSub { dst, left, right } => Self::FieldSub { dst, left, right },
            HumanCompiledInstruction::MulConst { dst, src, constant } => Self::MulConst { dst, src, constant },
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
        }
    }
}

impl From<&CompiledInstruction> for BinaryCompiledInstruction {
    fn from(value: &CompiledInstruction) -> Self {
        match HumanCompiledInstruction::from(value) {
            HumanCompiledInstruction::Copy { dst, src } => Self::Copy { dst, src },
            HumanCompiledInstruction::BoolFromFlag { dst, flags, bit } => Self::BoolFromFlag { dst, flags, bit },
            HumanCompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                Self::ClearBoolFromFlag { dst, flags, bit }
            }
            HumanCompiledInstruction::FieldMul { dst, left, right } => Self::FieldMul { dst, left, right },
            HumanCompiledInstruction::FieldAdd { dst, left, right } => Self::FieldAdd { dst, left, right },
            HumanCompiledInstruction::FieldSub { dst, left, right } => Self::FieldSub { dst, left, right },
            HumanCompiledInstruction::MulConst { dst, src, constant } => Self::MulConst { dst, src, constant },
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
        }
    }
}

impl From<BinaryCompiledInstruction> for CompiledInstruction {
    fn from(value: BinaryCompiledInstruction) -> Self {
        match value {
            BinaryCompiledInstruction::Copy { dst, src } => Self::Copy { dst, src },
            BinaryCompiledInstruction::BoolFromFlag { dst, flags, bit } => Self::BoolFromFlag { dst, flags, bit },
            BinaryCompiledInstruction::ClearBoolFromFlag { dst, flags, bit } => {
                Self::ClearBoolFromFlag { dst, flags, bit }
            }
            BinaryCompiledInstruction::FieldMul { dst, left, right } => Self::FieldMul { dst, left, right },
            BinaryCompiledInstruction::FieldAdd { dst, left, right } => Self::FieldAdd { dst, left, right },
            BinaryCompiledInstruction::FieldSub { dst, left, right } => Self::FieldSub { dst, left, right },
            BinaryCompiledInstruction::MulConst { dst, src, constant } => Self::MulConst { dst, src, constant },
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
    pub claim_summary: PreparedClaimSummary,
    pub family_summary: PreparedFamilySummary,
    pub prepared_leaf: CompiledLeaf,
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
        semantic_hash_field(hasher, "arithmetic_leaf_non_clifford", &self.arithmetic_leaf_non_clifford);
        semantic_hash_field(hasher, "direct_seed_non_clifford", &self.direct_seed_non_clifford);
        semantic_hash_field(hasher, "leaf_call_count_total", &self.leaf_call_count_total);
        semantic_hash_field(hasher, "lookup_component", &self.lookup_component);
        semantic_hash_field(hasher, "per_leaf_lookup_non_clifford", &self.per_leaf_lookup_non_clifford);
        semantic_hash_field(hasher, "reconstructed_total", &self.reconstructed_total);
    }
}

impl SemanticHash for LogicalQubitFormula {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 7);
        semantic_hash_field(hasher, "arithmetic_component", &self.arithmetic_component);
        semantic_hash_field(hasher, "arithmetic_slot_count", &self.arithmetic_slot_count);
        semantic_hash_field(hasher, "control_slot_count", &self.control_slot_count);
        semantic_hash_field(hasher, "field_bits", &self.field_bits);
        semantic_hash_field(hasher, "live_phase_bits", &self.live_phase_bits);
        semantic_hash_field(hasher, "lookup_workspace_qubits", &self.lookup_workspace_qubits);
        semantic_hash_field(hasher, "reconstructed_total", &self.reconstructed_total);
    }
}

impl SemanticHash for ClaimDocument {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 11);
        semantic_hash_field(hasher, "expected_case_count", &self.expected_case_count);
        semantic_hash_field(hasher, "expected_full_oracle_non_clifford", &self.expected_full_oracle_non_clifford);
        semantic_hash_field(hasher, "expected_total_logical_qubits", &self.expected_total_logical_qubits);
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
        semantic_hash_object_start(hasher, 11);
        semantic_hash_field(hasher, "arithmetic_slots", &self.arithmetic_slots);
        semantic_hash_field(hasher, "b3", &self.b3);
        semantic_hash_field(hasher, "curve", &self.curve);
        semantic_hash_field(hasher, "curve_b", &self.curve_b);
        semantic_hash_field(hasher, "field_modulus_hex", &self.field_modulus_hex);
        semantic_hash_field(hasher, "instructions", &self.instructions);
        semantic_hash_field(hasher, "interface_wires", &self.interface_wires);
        semantic_hash_field(hasher, "lookup_interface_slots", &self.lookup_interface_slots);
        semantic_hash_field(hasher, "notes", &self.notes);
        semantic_hash_field(hasher, "schema", &self.schema);
        semantic_hash_field(hasher, "variant", &self.variant);
    }
}

impl SemanticHash for FamilyDocument {
    fn semantic_hash(&self, hasher: &mut Sha256) {
        semantic_hash_object_start(hasher, 22);
        semantic_hash_field(hasher, "arithmetic_kernel_family", &self.arithmetic_kernel_family);
        semantic_hash_field(hasher, "arithmetic_leaf_non_clifford", &self.arithmetic_leaf_non_clifford);
        semantic_hash_field(hasher, "arithmetic_slot_count", &self.arithmetic_slot_count);
        semantic_hash_field(hasher, "control_slot_count", &self.control_slot_count);
        semantic_hash_field(hasher, "direct_seed_non_clifford", &self.direct_seed_non_clifford);
        semantic_hash_field(hasher, "full_oracle_non_clifford", &self.full_oracle_non_clifford);
        semantic_hash_field(hasher, "gate_set", &self.gate_set);
        semantic_hash_field(hasher, "live_phase_bits", &self.live_phase_bits);
        semantic_hash_field(hasher, "lookup_family", &self.lookup_family);
        semantic_hash_field(hasher, "lookup_workspace_qubits", &self.lookup_workspace_qubits);
        semantic_hash_field(hasher, "name", &self.name);
        semantic_hash_field(hasher, "notes", &self.notes);
        semantic_hash_field(hasher, "per_leaf_lookup_non_clifford", &self.per_leaf_lookup_non_clifford);
        semantic_hash_field(hasher, "phase_shell", &self.phase_shell);
        semantic_hash_field(hasher, "phase_shell_hadamards", &self.phase_shell_hadamards);
        semantic_hash_field(hasher, "phase_shell_measurements", &self.phase_shell_measurements);
        semantic_hash_field(hasher, "phase_shell_rotation_depth", &self.phase_shell_rotation_depth);
        semantic_hash_field(hasher, "phase_shell_rotations", &self.phase_shell_rotations);
        semantic_hash_field(hasher, "slot_allocation_family", &self.slot_allocation_family);
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
    point.as_ref().map(|value| (parse_hex_uint(&value.x_hex), parse_hex_uint(&value.y_hex)))
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
                    &((&numerator * mod_sub(&((&x1 * &denominator_sq) % modulus), &x3_numer, modulus)) % modulus),
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
                    &((&delta_y * mod_sub(&((&x1 * &delta_x_sq) % modulus), &x3_numer, modulus)) % modulus),
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
    for name in ["Q.X", "Q.Y", "Q.Z", "k", "lookup_x", "lookup_y", "lookup_meta", "qx", "qy", "qz"] {
        let next_id = register_ids.len();
        register_ids.insert(name.to_owned(), next_id);
    }
    let mut defined = BTreeSet::new();
    for name in ["Q.X", "Q.Y", "Q.Z", "k", "lookup_x", "lookup_y", "lookup_meta"] {
        defined.insert(name.to_owned());
    }
    let mut sorted_instructions = leaf.instructions.clone();
    sorted_instructions.sort_by_key(|instruction| instruction.pc);
    let mut compiled = Vec::with_capacity(sorted_instructions.len());
    for instruction in sorted_instructions {
        let dst_name = instruction.dst.as_ref().expect("missing instruction destination");
        let dst = if let Some(existing) = register_ids.get(dst_name) {
            *existing
        } else {
            let next_id = register_ids.len();
            register_ids.insert(dst_name.clone(), next_id);
            next_id
        };
        let compiled_instruction = match instruction.op.as_str() {
            "load_input" => {
                let src_name = source_as_register(instruction.src.as_ref().expect("missing load_input source"));
                let src = ensure_defined_register(&mut register_ids, &defined, src_name, "load_input source");
                CompiledInstruction::Copy { dst, src }
            }
            "lookup_affine_x" => {
                let (table, key) = source_as_lookup(instruction.src.as_ref().expect("missing lookup_affine_x source"));
                assert_eq!(table, "T.x");
                assert_eq!(key, "k");
                CompiledInstruction::Copy {
                    dst,
                    src: register_id(&register_ids, "lookup_x"),
                }
            }
            "lookup_affine_y" => {
                let (table, key) = source_as_lookup(instruction.src.as_ref().expect("missing lookup_affine_y source"));
                assert_eq!(table, "T.y");
                assert_eq!(key, "k");
                CompiledInstruction::Copy {
                    dst,
                    src: register_id(&register_ids, "lookup_y"),
                }
            }
            "lookup_meta" => {
                let (table, key) = source_as_lookup(instruction.src.as_ref().expect("missing lookup_meta source"));
                assert_eq!(table, "T.meta");
                assert_eq!(key, "k");
                CompiledInstruction::Copy {
                    dst,
                    src: register_id(&register_ids, "lookup_meta"),
                }
            }
            "bool_from_flag" => {
                let (flags_name, bit) = source_as_flag(instruction.src.as_ref().expect("missing bool_from_flag source"));
                let flags = ensure_defined_register(&mut register_ids, &defined, flags_name, "bool_from_flag flags");
                CompiledInstruction::BoolFromFlag { dst, flags, bit }
            }
            "clear_bool_from_flag" => {
                assert!(defined.contains(dst_name), "missing clear_bool_from_flag destination register: {dst_name}");
                let (flags_name, bit) = source_as_flag(instruction.src.as_ref().expect("missing clear_bool_from_flag source"));
                let flags = ensure_defined_register(&mut register_ids, &defined, flags_name, "clear_bool_from_flag flags");
                CompiledInstruction::ClearBoolFromFlag { dst, flags, bit }
            }
            "field_mul" => {
                let (left_name, right_name) = source_as_pair(instruction.src.as_ref().expect("missing field_mul source"));
                let left = ensure_defined_register(&mut register_ids, &defined, left_name, "field_mul lhs");
                let right = ensure_defined_register(&mut register_ids, &defined, right_name, "field_mul rhs");
                CompiledInstruction::FieldMul { dst, left, right }
            }
            "field_add" => {
                let (left_name, right_name) = source_as_pair(instruction.src.as_ref().expect("missing field_add source"));
                let left = ensure_defined_register(&mut register_ids, &defined, left_name, "field_add lhs");
                let right = ensure_defined_register(&mut register_ids, &defined, right_name, "field_add rhs");
                CompiledInstruction::FieldAdd { dst, left, right }
            }
            "field_sub" => {
                let (left_name, right_name) = source_as_pair(instruction.src.as_ref().expect("missing field_sub source"));
                let left = ensure_defined_register(&mut register_ids, &defined, left_name, "field_sub lhs");
                let right = ensure_defined_register(&mut register_ids, &defined, right_name, "field_sub rhs");
                CompiledInstruction::FieldSub { dst, left, right }
            }
            "mul_const" => {
                let src_name = source_as_register(instruction.src.as_ref().expect("missing mul_const source"));
                let src = ensure_defined_register(&mut register_ids, &defined, src_name, "mul_const source");
                let constant = instruction.const_value.expect("missing mul_const constant");
                CompiledInstruction::MulConst { dst, src, constant }
            }
            "select_field_if_flag" => {
                let flag_name = instruction.flag.as_ref().expect("missing select_field_if_flag flag");
                let flag = ensure_defined_register(&mut register_ids, &defined, flag_name, "select_field_if_flag flag");
                let (when_nonzero_name, when_zero_name) =
                    source_as_pair(instruction.src.as_ref().expect("missing select_field_if_flag source"));
                let when_nonzero =
                    ensure_defined_register(&mut register_ids, &defined, when_nonzero_name, "select_field_if_flag nonzero source");
                let when_zero =
                    ensure_defined_register(&mut register_ids, &defined, when_zero_name, "select_field_if_flag zero source");
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
        defined.insert(dst_name.clone());
    }
    for output in ["qx", "qy", "qz"] {
        assert!(defined.contains(output), "missing output register: {output}");
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

fn execute_leaf(leaf: &CompiledLeaf, accumulator: PointAffine, lookup: PointAffine, modulus: &BigUint) -> PointProj {
    let (qx, qy, qz) = affine_to_proj(accumulator);
    let lookup_x = lookup.as_ref().map(|(x, _)| x.clone()).unwrap_or_else(BigUint::zero);
    let lookup_y = lookup.as_ref().map(|(_, y)| y.clone()).unwrap_or_else(BigUint::zero);
    let lookup_meta = if lookup.is_none() { BigUint::one() } else { BigUint::zero() };
    let mut registers = vec![BigUint::zero(); leaf.register_count];
    registers[leaf.input_qx] = qx;
    registers[leaf.input_qy] = qy;
    registers[leaf.input_qz] = qz;
    registers[leaf.input_k] = if lookup.is_none() { BigUint::zero() } else { BigUint::one() };
    registers[leaf.input_lookup_x] = lookup_x;
    registers[leaf.input_lookup_y] = lookup_y;
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
            CompiledInstruction::FieldAdd { dst, left, right } => {
                registers[*dst] = (&registers[*left] + &registers[*right]) % modulus;
            }
            CompiledInstruction::FieldSub { dst, left, right } => {
                registers[*dst] = mod_sub(&registers[*left], &registers[*right], modulus);
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
    assert_eq!(input.leaf_document.document_type, "lookup_fed_leaf");
    assert_eq!(input.family_document.document_type, "compiler_family_summary");
    assert_eq!(input.case_corpus_document.document_type, "pointadd_case_corpus");
    assert_eq!(input.claim.digest_scheme, DIGEST_SCHEME);
    assert_eq!(input.leaf_document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(input.family_document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(input.case_corpus_document.digest_scheme, DIGEST_SCHEME);
    assert_eq!(
        semantic_payload_sha256(&input.claim.document_type, &input.claim.payload),
        input.claim.sha256
    );
    assert_eq!(
        semantic_payload_sha256(&input.leaf_document.document_type, &input.leaf_document.payload),
        input.leaf_document.sha256
    );
    assert_eq!(
        semantic_payload_sha256(&input.family_document.document_type, &input.family_document.payload),
        input.family_document.sha256
    );
    assert_eq!(
        semantic_payload_sha256(&input.case_corpus_document.document_type, &input.case_corpus_document.payload),
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

    assert_eq!(claim.non_clifford_formula.arithmetic_leaf_non_clifford, family.arithmetic_leaf_non_clifford);
    assert_eq!(claim.non_clifford_formula.per_leaf_lookup_non_clifford, family.per_leaf_lookup_non_clifford);
    assert_eq!(claim.non_clifford_formula.direct_seed_non_clifford, family.direct_seed_non_clifford);
    assert_eq!(claim.non_clifford_formula.leaf_call_count_total, claim.leaf_call_count_total);
    assert_eq!(claim.non_clifford_formula.arithmetic_component, family.arithmetic_leaf_non_clifford * claim.leaf_call_count_total as u64);
    assert_eq!(claim.non_clifford_formula.lookup_component, family.per_leaf_lookup_non_clifford * claim.leaf_call_count_total as u64);
    assert_eq!(
        claim.non_clifford_formula.reconstructed_total,
        claim.non_clifford_formula.arithmetic_component
            + claim.non_clifford_formula.lookup_component
            + family.direct_seed_non_clifford
    );
    assert_eq!(claim.non_clifford_formula.reconstructed_total, family.full_oracle_non_clifford);
    assert_eq!(claim.expected_full_oracle_non_clifford, family.full_oracle_non_clifford);

    assert_eq!(claim.logical_qubit_formula.field_bits, claim.field_bits);
    assert_eq!(claim.logical_qubit_formula.arithmetic_slot_count, family.arithmetic_slot_count);
    assert_eq!(claim.logical_qubit_formula.control_slot_count, family.control_slot_count);
    assert_eq!(claim.logical_qubit_formula.lookup_workspace_qubits, family.lookup_workspace_qubits);
    assert_eq!(claim.logical_qubit_formula.live_phase_bits, family.live_phase_bits);
    assert_eq!(
        claim.logical_qubit_formula.arithmetic_component,
        claim.field_bits as u64 * family.arithmetic_slot_count as u64
    );
    assert_eq!(
        claim.logical_qubit_formula.reconstructed_total,
        claim.logical_qubit_formula.arithmetic_component
            + family.control_slot_count as u64
            + family.lookup_workspace_qubits as u64
            + family.live_phase_bits as u64
    );
    assert_eq!(claim.logical_qubit_formula.reconstructed_total, family.total_logical_qubits);
    assert_eq!(claim.expected_total_logical_qubits, family.total_logical_qubits);

    let modulus = parse_hex_uint(&case_corpus.field_modulus_hex);
    let mut passed_case_count = 0u32;
    for case in &compiled_cases {
        let observed = execute_leaf(&compiled_leaf, case.accumulator.clone(), case.lookup.clone(), &modulus);
        let reference = add_affine_projective(case.accumulator.clone(), case.lookup.clone(), &modulus);
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
        expected_full_oracle_non_clifford: claim.expected_full_oracle_non_clifford,
        expected_total_logical_qubits: claim.expected_total_logical_qubits,
        case_count: case_corpus.case_count,
        passed_case_count,
    }
}

pub fn run_prepared_attestation(input: &PreparedAttestationInput) -> PublicValues {
    assert_eq!(input.schema, "compiler-project-zkp-attestation-input-v3");
    assert_eq!(input.document_digest_scheme, DIGEST_SCHEME);

    let claim = &input.claim_summary;
    let family = &input.family_summary;
    let case_corpus = &input.prepared_case_corpus;
    let compiled_cases = compile_prepared_case_corpus(case_corpus);

    assert_eq!(input.selected_family_name, family.name);
    assert_eq!(claim.expected_case_count, case_corpus.case_count);

    assert_eq!(claim.non_clifford_formula.arithmetic_leaf_non_clifford, family.arithmetic_leaf_non_clifford);
    assert_eq!(claim.non_clifford_formula.per_leaf_lookup_non_clifford, family.per_leaf_lookup_non_clifford);
    assert_eq!(claim.non_clifford_formula.direct_seed_non_clifford, family.direct_seed_non_clifford);
    assert_eq!(claim.non_clifford_formula.leaf_call_count_total, claim.leaf_call_count_total);
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
    assert_eq!(claim.non_clifford_formula.reconstructed_total, family.full_oracle_non_clifford);
    assert_eq!(claim.expected_full_oracle_non_clifford, family.full_oracle_non_clifford);

    assert_eq!(claim.logical_qubit_formula.field_bits, claim.field_bits);
    assert_eq!(claim.logical_qubit_formula.arithmetic_slot_count, family.arithmetic_slot_count);
    assert_eq!(claim.logical_qubit_formula.control_slot_count, family.control_slot_count);
    assert_eq!(claim.logical_qubit_formula.lookup_workspace_qubits, family.lookup_workspace_qubits);
    assert_eq!(claim.logical_qubit_formula.live_phase_bits, family.live_phase_bits);
    assert_eq!(
        claim.logical_qubit_formula.arithmetic_component,
        claim.field_bits as u64 * family.arithmetic_slot_count as u64
    );
    assert_eq!(
        claim.logical_qubit_formula.reconstructed_total,
        claim.logical_qubit_formula.arithmetic_component
            + family.control_slot_count as u64
            + family.lookup_workspace_qubits as u64
            + family.live_phase_bits as u64
    );
    assert_eq!(claim.logical_qubit_formula.reconstructed_total, family.total_logical_qubits);
    assert_eq!(claim.expected_total_logical_qubits, family.total_logical_qubits);

    let modulus = parse_hex_uint(&case_corpus.field_modulus_hex);
    let mut passed_case_count = 0u32;
    for case in &compiled_cases {
        let observed = execute_leaf(
            &input.prepared_leaf,
            case.accumulator.clone(),
            case.lookup.clone(),
            &modulus,
        );
        let reference = add_affine_projective(case.accumulator.clone(), case.lookup.clone(), &modulus);
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

pub fn fixture_json(
    public_values: &PublicValues,
    verifying_key: &str,
    proof_hex: Option<&str>,
    system: &str,
) -> String {
    serde_json::to_string_pretty(&serde_json::json!({
        "schema": "compiler-project-zkp-attestation-fixture-v1",
        "proof_system": system,
        "verification_key": verifying_key,
        "public_values": public_values,
        "proof": proof_hex,
    }))
    .expect("failed to serialize proof fixture")
}

#[cfg(test)]
mod tests {
    use super::{run_prepared_attestation, PreparedAttestationInput};

    #[test]
    fn native_run_prepared_attestation_matches_checked_in_input_shape() {
        let input: PreparedAttestationInput =
            serde_json::from_str(include_str!("../../../artifacts/zkp_attestation_input.json"))
                .expect("failed to parse checked-in prepared attestation input");
        let public_values = run_prepared_attestation(&input);
        assert_eq!(public_values.schema, "compiler-project-zkp-attestation-public-v2");
        assert_eq!(public_values.case_count, 8);
        assert_eq!(public_values.passed_case_count, 8);
    }

    #[test]
    fn bincode_roundtrip_checked_in_prepared_input_preserves_attestation_behavior() {
        let input: PreparedAttestationInput =
            serde_json::from_str(include_str!("../../../artifacts/zkp_attestation_input.json"))
                .expect("failed to parse checked-in prepared attestation input");
        let bytes = bincode::serialize(&input).expect("failed to bincode-serialize prepared attestation input");
        let roundtrip: PreparedAttestationInput =
            bincode::deserialize(&bytes).expect("failed to bincode-deserialize prepared attestation input");
        let original_public_values = run_prepared_attestation(&input);
        let roundtrip_public_values = run_prepared_attestation(&roundtrip);
        assert_eq!(
            serde_json::to_value(original_public_values).expect("failed to serialize original public values"),
            serde_json::to_value(roundtrip_public_values).expect("failed to serialize roundtrip public values"),
        );
    }

    #[test]
    fn json_roundtrip_checked_in_prepared_input_preserves_shape() {
        let input: PreparedAttestationInput =
            serde_json::from_str(include_str!("../../../artifacts/zkp_attestation_input.json"))
                .expect("failed to parse checked-in prepared attestation input");
        let json = serde_json::to_string(&input).expect("failed to serialize prepared attestation input");
        let roundtrip: PreparedAttestationInput =
            serde_json::from_str(&json).expect("failed to deserialize prepared attestation input");
        assert_eq!(
            serde_json::to_value(&input).expect("failed to serialize original prepared input"),
            serde_json::to_value(&roundtrip).expect("failed to serialize roundtrip prepared input"),
        );
    }
}
