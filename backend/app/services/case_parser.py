"""
Test case Excel parser service.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None

from app.core.logger import logger
from app.schemas.schemas import CaseItemSchema

# Common column name aliases
_CASE_ID_ALIASES = [
    "case_id", "caseid", "用例编号", "用例id", "测试用例id", "测试用例编号",
    "编号", "序号", "id", "no", "number",
]
_CASE_STEP_ALIASES = [
    "case_step", "casestep", "步骤", "测试步骤", "用例描述", "操作步骤",
    "description", "desc", "step", "steps", "testcase", "test_case",
    "测试描述", "操作", "测试操作",
]


def _norm_col(col: Any) -> str:
    return str(col).strip().lower().replace(" ", "").replace("_", "").replace("\n", "").replace("\r", "")


def _find_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    for col in columns:
        if _norm_col(col) in [_norm_col(a) for a in aliases]:
            return col
    return None


def parse_case_excel(
        file_path: str,
        sheet_name: Optional[Any] = None
) -> Tuple[List[CaseItemSchema], Dict[str, str], List[str]]:
    """
    Returns (case_items, column_mapping, sheet_names).
    """
    if pd is None:
        raise ImportError("pandas is required to parse case Excel files")

    workbook = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
    if not isinstance(workbook, dict):
        workbook = {str(sheet_name) if sheet_name else "Sheet1": workbook}

    all_cases: List[CaseItemSchema] = []
    column_mapping: Dict[str, str] = {}
    sheet_names = list(workbook.keys())

    for sheet, df in workbook.items():
        df = df.dropna(how="all")
        if df.empty:
            continue

        cols = list(df.columns)
        id_col = _find_column(cols, _CASE_ID_ALIASES)
        step_col = _find_column(cols, _CASE_STEP_ALIASES)

        if not step_col:
            logger.warning(f"Sheet '{sheet}': could not identify case step column. Columns: {cols}")
            continue

        if id_col:
            column_mapping["case_id"] = id_col
        column_mapping["case_step"] = step_col

        for idx, row in df.iterrows():
            step = str(row[step_col]).strip() if pd.notna(row[step_col]) else ""
            if not step or step.lower() == "nan":
                continue

            if id_col:
                cid = str(row[id_col]).strip() if pd.notna(row[id_col]) else f"row_{idx}"
                if cid.lower() == "nan":
                    cid = f"row_{idx}"
            else:
                cid = f"row_{idx}"

            raw_row = {str(c): str(row[c]) for c in cols if pd.notna(row[c])}
            all_cases.append(CaseItemSchema(
                row_index=int(idx),
                case_id=cid,
                case_step=step,
                raw_row=raw_row,
            ))

    return all_cases, column_mapping, sheet_names
