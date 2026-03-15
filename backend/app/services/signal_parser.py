"""
Signal parser service - adapted from legacy signal_extractor.py
Supports DBC and Excel signal matrix files.
"""
import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

from app.core.logger import logger
from app.schemas.schemas import FlatSignal


class SignalDatabaseExtractor:
    _MESSAGE_COLUMN_ALIASES = {
        "message_id": (
            "message_id", "msg_id", "msgid", "frame_id", "can_id", "bo", "id",
            "message identifier", "frame identifier",
            "报文id", "消息id", "报文标识符", "帧id",
        ),
        "message_name": (
            "message_name", "msg_name", "frame_name", "message",
            "报文名", "消息名", "报文名称", "帧名称",
        ),
        "message_size": (
            "message_size", "dlc", "length", "frame_length", "message_length",
            "报文长度", "帧长度", "字节数",
        ),
        "node_name": (
            "node_name", "sender", "transmitter", "tx_node",
            "发送节点", "发送器", "发送方", "节点",
        ),
    }

    _SIGNAL_COLUMN_ALIASES = {
        "signal_name": ("signal_name", "sig_name", "signal", "name", "信号名", "信号名称"),
        "raw_start_bit": ("raw_start_bit", "start_bit", "bit_start", "起始位", "开始位", "startbit"),
        "signal_size": ("signal_size", "bit_length", "signal_length", "length_bit", "位长", "信号长度", "长度"),
        "byte_order": ("byte_order", "endian", "endianness", "motorola_intel", "intel_motorola", "字节序", "端序"),
        "value_type": ("value_type", "sign", "signedness", "data_type", "值类型", "数据类型", "符号类型"),
        "factor": ("factor", "resolution", "scale", "比例因子", "系数"),
        "offset": ("offset", "偏移", "偏移量"),
        "min_value": ("min_value", "minimum", "min", "物理最小值", "最小值"),
        "max_value": ("max_value", "maximum", "max", "物理最大值", "最大值"),
        "unit": ("unit", "单位"),
        "receiver": ("receiver", "receivers", "rx_node", "接收节点", "接收器", "接收方"),
        "default_value": ("default_value", "initial_value", "start_value", "默认值", "初始值"),
        "send_type": ("send_type", "signal_send_type", "发送类型", "发送方式"),
        "cycle_time": ("cycle_time", "period", "周期", "周期时间", "发送周期"),
        "values": ("values", "value_table", "enum", "enumeration", "取值表", "枚举值", "值描述"),
        "comment": ("comment", "description", "desc", "备注", "描述"),
    }

    def parse(self, source_file: str, sheet_name: Optional[Any] = None) -> Dict[str, Any]:
        if not source_file or not os.path.exists(source_file):
            raise FileNotFoundError(f"Signal file not found: {source_file}")
        ext = os.path.splitext(source_file)[1].lower()
        if ext == ".dbc":
            return self.parse_dbc(source_file)
        elif ext in (".xls", ".xlsx", ".xlsm"):
            return self.parse_excel(source_file, sheet_name=sheet_name)
        else:
            raise ValueError(f"Unsupported signal file type: {ext}")

    def parse_dbc(self, dbc_file: str) -> Dict[str, Any]:
        messages = {}
        signal_count = 0
        current_message = None
        current_msg_id = None
        value_descs = {}  # msg_id -> signal_name -> {val: desc}

        with open(dbc_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # BO_ message
            if line.startswith("BO_ "):
                parts = line.split()
                if len(parts) >= 4:
                    msg_id_raw = parts[1]
                    msg_name = parts[2].rstrip(":")
                    msg_size = parts[3]
                    try:
                        msg_id_int = int(msg_id_raw) & 0x1FFFFFFF
                        msg_id = str(msg_id_int)
                    except Exception:
                        msg_id = msg_id_raw
                    current_msg_id = msg_id
                    current_message = {
                        "message_id": msg_id,
                        "message_id_hex": hex(int(msg_id)) if msg_id.isdigit() else None,
                        "message_name": msg_name,
                        "message_size": msg_size,
                        "node_name": parts[4] if len(parts) > 4 else None,
                        "signals": {}
                    }
                    messages[msg_id] = current_message

            # SG_ signal
            elif line.strip().startswith("SG_ ") and current_message is not None:
                sig_line = line.strip()
                m = re.match(
                    r'SG_\s+(\S+)\s*(?:M|m\d+)?\s*:\s*'
                    r'(\d+)\|(\d+)@([01])([+-])\s*'
                    r'\(([-\d.Ee+]+),([-\d.Ee+]+)\)\s*'
                    r'\[([-\d.Ee+]*),([-\d.Ee+]*)\]\s*'
                    r'"([^"]*)"\s*(.*)',
                    sig_line
                )
                if m:
                    sig_name = m.group(1)
                    start_bit = m.group(2)
                    sig_size = m.group(3)
                    byte_order = "intel" if m.group(4) == "1" else "motorola"
                    value_type = "signed" if m.group(5) == "-" else "unsigned"
                    factor = m.group(6)
                    offset = m.group(7)
                    min_val = m.group(8)
                    max_val = m.group(9)
                    unit = m.group(10)
                    receivers = [r.strip() for r in m.group(11).split(",") if r.strip()]
                    current_message["signals"][sig_name] = {
                        "signal_name": sig_name,
                        "raw_start_bit": start_bit,
                        "signal_size": sig_size,
                        "byte_order": byte_order,
                        "value_type": value_type,
                        "factor": factor,
                        "offset": offset,
                        "min_value": min_val,
                        "max_value": max_val,
                        "unit": unit,
                        "receiver": receivers,
                        "values": {},
                        "comment": None,
                    }
                    signal_count += 1

            # CM_ comment
            elif line.startswith("CM_ SG_"):
                m = re.match(r'CM_ SG_\s+(\d+)\s+(\S+)\s+"(.*)"', line, re.DOTALL)
                if not m:
                    # multi-line comment
                    full = line
                    while i + 1 < len(lines) and '";' not in lines[i]:
                        i += 1
                        full += lines[i]
                    m = re.match(r'CM_ SG_\s+(\d+)\s+(\S+)\s+"(.*)"', full.replace("\n", " "), re.DOTALL)
                if m:
                    msg_id = str(int(m.group(1)) & 0x1FFFFFFF)
                    sig_name = m.group(2)
                    comment = m.group(3).strip()
                    if msg_id in messages and sig_name in messages[msg_id]["signals"]:
                        messages[msg_id]["signals"][sig_name]["comment"] = comment

            # VAL_ value descriptions
            elif line.startswith("VAL_"):
                parts = line.rstrip(";").split()
                if len(parts) >= 4:
                    try:
                        msg_id = str(int(parts[1]) & 0x1FFFFFFF)
                        sig_name = parts[2]
                        vals = {}
                        j = 3
                        while j + 1 < len(parts):
                            vals[parts[j]] = parts[j + 1].strip('"')
                            j += 2
                        if msg_id in messages and sig_name in messages[msg_id]["signals"]:
                            messages[msg_id]["signals"][sig_name]["values"] = vals
                    except Exception:
                        pass

            i += 1

        return {
            "source_file": os.path.basename(dbc_file),
            "source_type": "dbc",
            "message_count": len(messages),
            "signal_count": signal_count,
            "sheet_names": [],
            "messages": messages
        }

    def parse_excel(self, excel_file: str, sheet_name: Optional[Any] = None) -> Dict[str, Any]:
        if pd is None:
            raise ImportError("pandas is required to parse Excel signal matrix files")
        workbook = pd.read_excel(
            excel_file,
            sheet_name=sheet_name if sheet_name is not None else None,
            dtype=str
        )
        if not isinstance(workbook, dict):
            workbook = {str(sheet_name) if sheet_name is not None else "Sheet1": workbook}

        messages = {}
        parsed_sheets = []

        for current_sheet, dataframe in workbook.items():
            parsed = self._parse_excel_sheet(dataframe)
            if not parsed:
                continue
            parsed_sheets.append(current_sheet)
            for msg_id, message in parsed.items():
                if msg_id not in messages:
                    messages[msg_id] = message
                else:
                    messages[msg_id]["signals"].update(message.get("signals", {}))

        if not messages:
            raise ValueError(f"No valid message/signal data found in: {excel_file}")

        signal_count = sum(len(m.get("signals", {})) for m in messages.values())
        return {
            "source_file": os.path.basename(excel_file),
            "source_type": "excel",
            "message_count": len(messages),
            "signal_count": signal_count,
            "sheet_names": parsed_sheets,
            "messages": messages
        }

    def _parse_excel_sheet(self, dataframe) -> Dict[str, Dict[str, Any]]:
        dataframe = dataframe.dropna(how="all")
        if dataframe.empty:
            return {}
        rename_map = self._match_excel_columns(dataframe.columns)
        if "message_id" not in rename_map.values() or "signal_name" not in rename_map.values():
            return {}
        dataframe = dataframe.rename(columns=rename_map).copy()
        normalized_columns = set(rename_map.values())
        for key in ("message_id", "message_name", "message_size", "node_name"):
            if key in normalized_columns:
                dataframe[key] = dataframe[key].ffill()

        messages = {}
        for _, row in dataframe.iterrows():
            msg_id = self._norm_msg_id(row.get("message_id"))
            sig_name = self._norm_text(row.get("signal_name"))
            if not msg_id or not sig_name:
                continue
            message = messages.setdefault(msg_id, {
                "message_id": msg_id,
                "message_id_hex": self._fmt_hex(msg_id),
                "message_name": self._norm_text(row.get("message_name")),
                "message_size": self._norm_num(row.get("message_size")),
                "node_name": self._norm_text(row.get("node_name")),
                "signals": {}
            })
            sig_data = {"signal_name": sig_name}
            for field in self._SIGNAL_COLUMN_ALIASES:
                if field == "signal_name" or field not in dataframe.columns:
                    continue
                val = self._norm_excel_val(field, row.get(field))
                if val is not None:
                    sig_data[field] = val
            message["signals"][sig_name] = sig_data
        return messages

    def _match_excel_columns(self, columns):
        alias_map = {}
        all_a = {}
        all_a.update(self._MESSAGE_COLUMN_ALIASES)
        all_a.update(self._SIGNAL_COLUMN_ALIASES)
        for canonical, aliases in all_a.items():
            for a in aliases:
                alias_map[self._norm_col(a)] = canonical
        return {col: alias_map[self._norm_col(col)] for col in columns if self._norm_col(col) in alias_map}

    @staticmethod
    def _norm_col(col):
        return str(col).strip().lower().replace("\n", "").replace("\r", "").replace(" ", "").replace("_", "")

    @staticmethod
    def _norm_text(val):
        if val is None:
            return None
        s = str(val).strip()
        return None if s.lower() == "nan" or not s else s

    @staticmethod
    def _norm_num(val):
        t = SignalDatabaseExtractor._norm_text(val)
        if t is None:
            return None
        try:
            n = float(t)
            return str(int(n)) if n.is_integer() else str(n)
        except ValueError:
            return t

    @staticmethod
    def _norm_msg_id(val):
        t = SignalDatabaseExtractor._norm_text(val)
        if t is None:
            return None
        low = t.lower()
        try:
            if low.startswith("0x"):
                return str(int(low, 16))
            if low.endswith("h"):
                return str(int(low[:-1], 16))
            n = float(low)
            return str(int(n)) if n.is_integer() else t
        except ValueError:
            return t

    @staticmethod
    def _fmt_hex(msg_id):
        try:
            return hex(int(str(msg_id)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _norm_excel_val(field, val):
        t = SignalDatabaseExtractor._norm_text(val)
        if t is None:
            return None
        if field in ("message_size", "raw_start_bit", "signal_size", "cycle_time",
                     "factor", "offset", "min_value", "max_value", "default_value"):
            return SignalDatabaseExtractor._norm_num(t)
        if field == "values":
            return SignalDatabaseExtractor._parse_value_map(t)
        if field == "receiver":
            return [x.strip() for x in t.replace(";", ",").split(",") if x.strip()]
        return t

    @staticmethod
    def _parse_value_map(text):
        try:
            v = json.loads(text)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
        pairs = {}
        for part in text.replace("\n", ";").split(";"):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                k, v = part.split(":", 1)
            elif "=" in part:
                k, v = part.split("=", 1)
            else:
                return text
            pairs[k.strip()] = v.strip()
        return pairs if pairs else text


def build_flat_signals(parsed_data: Dict[str, Any]) -> List[FlatSignal]:
    """Convert parsed signal data to flat list."""
    result = []
    source_type = parsed_data.get("source_type", "unknown")
    for msg_id, message in parsed_data.get("messages", {}).items():
        for sig_name, sig in message.get("signals", {}).items():
            values_raw = sig.get("values", {})
            if isinstance(values_raw, str):
                try:
                    values_raw = json.loads(values_raw)
                except Exception:
                    values_raw = {}
            if not isinstance(values_raw, dict):
                values_raw = {}
            desc = sig.get("comment") or sig.get("signal_desc") or ""
            result.append(FlatSignal(
                msg_id=message.get("message_id"),
                msg_id_hex=message.get("message_id_hex"),
                message_name=message.get("message_name"),
                signal_name=sig_name,
                signal_desc=desc,
                values={str(k): str(v) for k, v in values_raw.items()},
                unit=sig.get("unit"),
                node_name=message.get("node_name"),
                source_type=source_type,
            ))
    return result
