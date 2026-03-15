from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


def now():
    return datetime.utcnow()


class MatchTask(Base):
    __tablename__ = "match_task"
    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(64), unique=True, index=True)
    status = Column(String(32), default="pending")
    signal_file_id = Column(Integer, ForeignKey("uploaded_file.id"), nullable=True)
    case_file_id = Column(Integer, ForeignKey("uploaded_file.id"), nullable=True)
    signal_source_id = Column(Integer, ForeignKey("signal_source.id"), nullable=True)
    case_batch_id = Column(Integer, ForeignKey("case_batch.id"), nullable=True)
    model_name = Column(String(128), nullable=True)
    model_base_url = Column(String(256), nullable=True)
    temperature = Column(Float, nullable=True)
    case_count = Column(Integer, default=0)
    matched_case_count = Column(Integer, default=0)
    unmatched_case_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class UploadedFile(Base):
    __tablename__ = "uploaded_file"
    id = Column(Integer, primary_key=True, index=True)
    file_type = Column(String(32))  # signal / case
    original_name = Column(String(256))
    stored_name = Column(String(256))
    stored_path = Column(String(512))
    file_ext = Column(String(32))
    file_size = Column(Integer)
    file_hash = Column(String(64), index=True)
    content_type = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=now)


class SignalSource(Base):
    __tablename__ = "signal_source"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    uploaded_file_id = Column(Integer, ForeignKey("uploaded_file.id"))
    source_type = Column(String(32))  # dbc / excel
    source_file_name = Column(String(256))
    sheet_names_json = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    signal_count = Column(Integer, default=0)
    normalized_data_json = Column(Text, nullable=True)
    signals_flatten_json = Column(Text, nullable=True)
    parse_status = Column(String(32), default="success")
    parse_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    signal_items = relationship("SignalItem", back_populates="signal_source")


class SignalItem(Base):
    __tablename__ = "signal_item"
    id = Column(Integer, primary_key=True, index=True)
    signal_source_id = Column(Integer, ForeignKey("signal_source.id"))
    message_id = Column(String(64), index=True)
    message_id_hex = Column(String(32), index=True)
    message_name = Column(String(256), nullable=True)
    signal_name = Column(String(256), index=True)
    signal_desc = Column(Text, nullable=True)
    values_json = Column(Text, nullable=True)
    unit = Column(String(64), nullable=True)
    receiver_json = Column(Text, nullable=True)
    factor = Column(String(64), nullable=True)
    offset = Column(String(64), nullable=True)
    default_value = Column(String(64), nullable=True)
    cycle_time = Column(String(64), nullable=True)
    comment = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    signal_source = relationship("SignalSource", back_populates="signal_items")


class CaseBatch(Base):
    __tablename__ = "case_batch"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    uploaded_file_id = Column(Integer, ForeignKey("uploaded_file.id"))
    sheet_names_json = Column(Text, nullable=True)
    case_count = Column(Integer, default=0)
    column_mapping_json = Column(Text, nullable=True)
    parse_status = Column(String(32), default="success")
    parse_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    case_items = relationship("CaseItem", back_populates="case_batch")


class CaseItem(Base):
    __tablename__ = "case_item"
    id = Column(Integer, primary_key=True, index=True)
    case_batch_id = Column(Integer, ForeignKey("case_batch.id"))
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    row_index = Column(Integer)
    case_id = Column(String(256), index=True)
    case_step = Column(Text)
    raw_row_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    case_batch = relationship("CaseBatch", back_populates="case_items")


class CaseSemantics(Base):
    __tablename__ = "case_semantics"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    case_item_id = Column(Integer, ForeignKey("case_item.id"), index=True)
    original_text = Column(Text)
    normalized_text = Column(Text, nullable=True)
    action = Column(String(128), nullable=True)
    target_objects_json = Column(Text, nullable=True)
    positions_json = Column(Text, nullable=True)
    expanded_steps_json = Column(Text, nullable=True)
    negative_patterns_json = Column(Text, nullable=True)
    enum_value_semantics_json = Column(Text, nullable=True)
    semantic_notes_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)


class CaseCandidateSignal(Base):
    __tablename__ = "case_candidate_signal"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    case_item_id = Column(Integer, ForeignKey("case_item.id"), index=True)
    signal_item_id = Column(Integer, ForeignKey("signal_item.id"), nullable=True)
    candidate_rank = Column(Integer, default=0)
    candidate_score = Column(Float, default=0.0)
    hit_reasons_json = Column(Text, nullable=True)
    expanded_step_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)


class PromptRecord(Base):
    __tablename__ = "prompt_record"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    case_item_id = Column(Integer, ForeignKey("case_item.id"), index=True)
    system_prompt = Column(Text, nullable=True)
    user_prompt = Column(Text, nullable=True)
    prompt_version = Column(String(32), default="v1")
    prompt_hash = Column(String(64), nullable=True)
    candidate_signal_snapshot_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)


class LlmCallRecord(Base):
    __tablename__ = "llm_call_record"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    case_item_id = Column(Integer, ForeignKey("case_item.id"), index=True)
    prompt_record_id = Column(Integer, ForeignKey("prompt_record.id"), nullable=True)
    provider_name = Column(String(64), default="deepseek")
    model_name = Column(String(128), nullable=True)
    request_payload_json = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    token_usage_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)


class CaseMatchResult(Base):
    __tablename__ = "case_match_result"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    case_item_id = Column(Integer, ForeignKey("case_item.id"), index=True)
    llm_call_record_id = Column(Integer, ForeignKey("llm_call_record.id"), nullable=True)
    matched = Column(Boolean, default=False)
    result_json = Column(Text, nullable=True)
    match_count = Column(Integer, default=0)
    info_str_summary = Column(Text, nullable=True)
    unmatched_reason = Column(Text, nullable=True)
    validation_status = Column(String(32), default="ok")
    validation_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)


class ExportRecord(Base):
    __tablename__ = "export_record"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("match_task.id"), nullable=True)
    case_batch_id = Column(Integer, ForeignKey("case_batch.id"), nullable=True)
    export_file_name = Column(String(256), nullable=True)
    export_file_path = Column(String(512), nullable=True)
    export_status = Column(String(32), default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
