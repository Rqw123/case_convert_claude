from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# -------- Signal schemas --------

class FlatSignal(BaseModel):
    msg_id: Optional[str] = None
    msg_id_hex: Optional[str] = None
    message_name: Optional[str] = None
    signal_name: str
    signal_desc: Optional[str] = None
    values: Dict[str, str] = {}
    unit: Optional[str] = None
    node_name: Optional[str] = None
    source_type: Optional[str] = None


class SignalParseResponse(BaseModel):
    signal_session_id: str
    source_type: str
    message_count: int
    signal_count: int
    signals_preview: List[FlatSignal] = []


# -------- Case schemas --------

class CaseItemSchema(BaseModel):
    row_index: int
    case_id: str
    case_step: str
    raw_row: Dict[str, Any] = {}


class CaseParseResponse(BaseModel):
    case_session_id: str
    case_count: int
    cases_preview: List[CaseItemSchema] = []


# -------- Semantics --------

class NormalizedCaseSemantics(BaseModel):
    case_id: str
    original_text: str
    normalized_text: Optional[str] = None
    action: Optional[str] = None
    targets: List[str] = []
    positions: List[str] = []
    expanded_steps: List[str] = []
    negative_patterns: List[str] = []
    enum_value_semantics: Dict[str, str] = {}


# -------- Match schemas --------

class ModelConfigSchema(BaseModel):
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.0
    timeout_seconds: int = 60
    max_retries: int = 2


class MatchRunRequest(BaseModel):
    signal_session_id: str
    case_session_id: str
    model_config: ModelConfigSchema = ModelConfigSchema()


class SignalCandidate(BaseModel):
    signal_desc: Optional[str] = None
    msg_id: Optional[str] = None
    signal_name: str
    signal_val: Optional[str] = None
    info_str: Optional[str] = None
    match_reason: Optional[str] = None


class CaseMatchResultSchema(BaseModel):
    case_id: str
    case_step: str
    matched: bool
    case_info: List[SignalCandidate] = []
    unmatched_reason: Optional[str] = None


class MatchResponse(BaseModel):
    task_id: str
    results: List[CaseMatchResultSchema] = []
    total: int = 0
    matched_count: int = 0
    unmatched_count: int = 0


# -------- Prompt preview --------

class PromptPreviewRequest(BaseModel):
    signal_session_id: str
    case_session_id: str
    case_index: int = 0


class PromptPreviewResponse(BaseModel):
    system_prompt: str
    user_prompt: str
    case_id: str
    case_step: str


# -------- Export --------

class ExportRequest(BaseModel):
    task_id: str


# -------- Task info --------

class TaskInfo(BaseModel):
    task_id: str
    task_code: str
    status: str
    case_count: int
    matched_case_count: int
    unmatched_case_count: int
    created_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
