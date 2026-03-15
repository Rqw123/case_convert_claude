#! /usr/bin/env python

# ======================================
# author    : Codex
# licence   : www.noboauto.com
# ======================================

"""
Extract all CAN signal information from a DBC file or an Excel signal matrix
and store the normalized result into a json file.
"""

import json
import os
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from common.logger.logger import logger
except (ImportError, ):
    import logging as logger

from common.dbc.dbc import _DBCParser


class SignalDatabaseExtractor:
    """
    Parse DBC or Excel signal matrix files and export all signal information.
    """

    _MESSAGE_COLUMN_ALIASES = {
        "message_id": (
            "message_id", "msg_id", "msgid", "frame_id", "can_id", "bo", "id",
            "message identifier", "frame identifier",
            "\u62a5\u6587id", "\u6d88\u606fid", "\u62a5\u6587\u6807\u8bc6\u7b26", "\u5e27id"
        ),
        "message_name": (
            "message_name", "msg_name", "frame_name", "message",
            "\u62a5\u6587\u540d", "\u6d88\u606f\u540d", "\u62a5\u6587\u540d\u79f0", "\u5e27\u540d\u79f0"
        ),
        "message_size": (
            "message_size", "dlc", "length", "frame_length", "message_length",
            "\u62a5\u6587\u957f\u5ea6", "\u5e27\u957f\u5ea6", "\u5b57\u8282\u6570"
        ),
        "node_name": (
            "node_name", "sender", "transmitter", "tx_node",
            "\u53d1\u9001\u8282\u70b9", "\u53d1\u9001\u5668", "\u53d1\u9001\u65b9", "\u8282\u70b9"
        ),
    }

    _SIGNAL_COLUMN_ALIASES = {
        "signal_name": (
            "signal_name", "sig_name", "signal", "name",
            "\u4fe1\u53f7\u540d", "\u4fe1\u53f7\u540d\u79f0"
        ),
        "raw_start_bit": (
            "raw_start_bit", "start_bit", "bit_start",
            "\u8d77\u59cb\u4f4d", "\u5f00\u59cb\u4f4d", "startbit"
        ),
        "signal_size": (
            "signal_size", "bit_length", "signal_length", "length_bit",
            "\u4f4d\u957f", "\u4fe1\u53f7\u957f\u5ea6", "\u957f\u5ea6"
        ),
        "byte_order": (
            "byte_order", "endian", "endianness", "motorola_intel", "intel_motorola",
            "\u5b57\u8282\u5e8f", "\u7aef\u5e8f"
        ),
        "value_type": (
            "value_type", "sign", "signedness", "data_type",
            "\u503c\u7c7b\u578b", "\u6570\u636e\u7c7b\u578b", "\u7b26\u53f7\u7c7b\u578b"
        ),
        "factor": (
            "factor", "resolution", "scale", "\u6bd4\u4f8b\u56e0\u5b50", "\u7cfb\u6570"
        ),
        "offset": (
            "offset", "\u504f\u79fb", "\u504f\u79fb\u91cf"
        ),
        "min_value": (
            "min_value", "minimum", "min", "\u7269\u7406\u6700\u5c0f\u503c", "\u6700\u5c0f\u503c"
        ),
        "max_value": (
            "max_value", "maximum", "max", "\u7269\u7406\u6700\u5927\u503c", "\u6700\u5927\u503c"
        ),
        "unit": (
            "unit", "\u5355\u4f4d"
        ),
        "receiver": (
            "receiver", "receivers", "rx_node",
            "\u63a5\u6536\u8282\u70b9", "\u63a5\u6536\u5668", "\u63a5\u6536\u65b9"
        ),
        "default_value": (
            "default_value", "initial_value", "start_value", "\u9ed8\u8ba4\u503c", "\u521d\u59cb\u503c"
        ),
        "send_type": (
            "send_type", "signal_send_type", "\u53d1\u9001\u7c7b\u578b", "\u53d1\u9001\u65b9\u5f0f"
        ),
        "cycle_time": (
            "cycle_time", "period", "\u5468\u671f", "\u5468\u671f\u65f6\u95f4", "\u53d1\u9001\u5468\u671f"
        ),
        "values": (
            "values", "value_table", "enum", "enumeration",
            "\u53d6\u503c\u8868", "\u679a\u4e3e\u503c", "\u503c\u63cf\u8ff0"
        ),
        "comment": (
            "comment", "description", "desc", "\u5907\u6ce8", "\u63cf\u8ff0"
        ),
    }

    def parse(
            self,
            source_file: str,
            output_file: Optional[str] = None,
            sheet_name: Optional[Any] = None
    ) -> Dict[str, Any]:
        self._validate_source_file(source_file)
        extension = os.path.splitext(source_file)[1].lower()
        if extension == ".dbc":
            data = self.parse_dbc(source_file)
        elif extension in (".xls", ".xlsx", ".xlsm"):
            data = self.parse_excel(source_file, sheet_name=sheet_name)
        else:
            raise ValueError(f"unsupported signal database file: <{source_file}>")

        output_file = output_file or self.default_output_path(source_file)
        self.write_json(data, output_file)
        return data

    def parse_dbc(self, dbc_file: str) -> Dict[str, Any]:
        self._validate_source_file(dbc_file)
        messages = _DBCParser(dbc_file).messages
        normalized_messages = {}
        signal_count = 0

        for message_id, message in messages.items():
            message_data = dict(message)
            message_data["message_id"] = str(message_data.get("message_id", message_id))
            message_data["message_id_hex"] = self._format_message_id_hex(message_data["message_id"])
            message_data["signals"] = message_data.get("signals", {})
            signal_count += len(message_data["signals"])
            normalized_messages[str(message_data["message_id"])] = message_data

        return self._build_result(
            source_file=dbc_file,
            source_type="dbc",
            messages=normalized_messages,
            sheets=None,
            signal_count=signal_count
        )

    def parse_excel(
            self,
            excel_file: str,
            sheet_name: Optional[Any] = None
    ) -> Dict[str, Any]:
        self._validate_source_file(excel_file)
        if pd is None:
            raise ImportError("pandas is required to parse excel signal matrix files")

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
                logger.debug(f"excel sheet ignored because required columns were not found: <{current_sheet}>")
                continue

            parsed_sheets.append(current_sheet)
            for message_id, message in parsed.items():
                if message_id not in messages:
                    messages[message_id] = message
                    continue

                existing = messages[message_id]
                for key in ("message_name", "message_size", "node_name"):
                    if not existing.get(key) and message.get(key):
                        existing[key] = message[key]
                existing["signals"].update(message.get("signals", {}))

        if not messages:
            raise ValueError(f"no valid message/signal data found in excel file: <{excel_file}>")

        signal_count = sum(len(item.get("signals", {})) for item in messages.values())
        return self._build_result(
            source_file=excel_file,
            source_type="excel",
            messages=messages,
            sheets=parsed_sheets,
            signal_count=signal_count
        )

    def write_json(self, data: Dict[str, Any], output_file: str) -> str:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_file, "w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=4, ensure_ascii=False)
        logger.info(f"signal database json file generated: <{output_file}>")
        return output_file

    @staticmethod
    def default_output_path(source_file: str) -> str:
        base_name, _ = os.path.splitext(source_file)
        return f"{base_name}.signals.json"

    @classmethod
    def _build_result(
            cls,
            source_file: str,
            source_type: str,
            messages: Dict[str, Dict[str, Any]],
            sheets: Optional[List[str]],
            signal_count: int
    ) -> Dict[str, Any]:
        return {
            "source_file": os.path.abspath(source_file),
            "source_type": source_type,
            "message_count": len(messages),
            "signal_count": signal_count,
            "sheet_names": sheets or [],
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
            message_id = self._normalize_message_id(row.get("message_id"))
            signal_name = self._normalize_text(row.get("signal_name"))
            if not message_id or not signal_name:
                continue

            message = messages.setdefault(message_id, {
                "message_id": message_id,
                "message_id_hex": self._format_message_id_hex(message_id),
                "message_name": self._normalize_text(row.get("message_name")),
                "message_size": self._normalize_numeric_text(row.get("message_size")),
                "node_name": self._normalize_text(row.get("node_name")),
                "signals": {}
            })

            if not message.get("message_name"):
                message["message_name"] = self._normalize_text(row.get("message_name"))
            if not message.get("message_size"):
                message["message_size"] = self._normalize_numeric_text(row.get("message_size"))
            if not message.get("node_name"):
                message["node_name"] = self._normalize_text(row.get("node_name"))

            signal_data = {"signal_name": signal_name}
            for field_name in self._SIGNAL_COLUMN_ALIASES.keys():
                if field_name == "signal_name" or field_name not in dataframe.columns:
                    continue
                value = self._normalize_excel_value(field_name, row.get(field_name))
                if value is not None:
                    signal_data[field_name] = value
            message["signals"][signal_name] = signal_data

        return messages

    def _match_excel_columns(self, columns: Iterable[Any]) -> Dict[Any, str]:
        rename_map = {}
        alias_map = self._build_alias_map()
        for column in columns:
            normalized_column = self._normalize_column_name(column)
            if normalized_column in alias_map:
                rename_map[column] = alias_map[normalized_column]
        return rename_map

    @classmethod
    def _build_alias_map(cls) -> Dict[str, str]:
        alias_map = {}
        all_aliases = {}
        all_aliases.update(cls._MESSAGE_COLUMN_ALIASES)
        all_aliases.update(cls._SIGNAL_COLUMN_ALIASES)
        for canonical_name, aliases in all_aliases.items():
            for alias in aliases:
                alias_map[cls._normalize_column_name(alias)] = canonical_name
        return alias_map

    @staticmethod
    def _validate_source_file(source_file: str):
        if not source_file or not os.path.exists(source_file):
            raise FileNotFoundError(f"signal database file not found: <{source_file}>")

    @staticmethod
    def _normalize_column_name(column: Any) -> str:
        return str(column).strip().lower().replace("\n", "").replace("\r", "").replace(" ", "").replace("_", "")

    @staticmethod
    def _normalize_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        if str(value).lower() == "nan":
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_numeric_text(value: Any) -> Optional[str]:
        text = SignalDatabaseExtractor._normalize_text(value)
        if text is None:
            return None
        try:
            number = float(text)
        except ValueError:
            return text
        return str(int(number)) if number.is_integer() else str(number)

    @staticmethod
    def _normalize_message_id(value: Any) -> Optional[str]:
        text = SignalDatabaseExtractor._normalize_text(value)
        if text is None:
            return None
        lowered = text.lower()
        try:
            if lowered.startswith("0x"):
                return str(int(lowered, 16))
            if lowered.endswith("h"):
                return str(int(lowered[:-1], 16))
            number = float(lowered)
            return str(int(number)) if number.is_integer() else text
        except ValueError:
            return text

    @staticmethod
    def _format_message_id_hex(message_id: Any) -> Optional[str]:
        try:
            return hex(int(str(message_id)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_excel_value(field_name: str, value: Any) -> Any:
        text = SignalDatabaseExtractor._normalize_text(value)
        if text is None:
            return None
        if field_name in ("message_size", "raw_start_bit", "signal_size", "cycle_time"):
            return SignalDatabaseExtractor._normalize_numeric_text(text)
        if field_name in ("factor", "offset", "min_value", "max_value", "default_value"):
            return SignalDatabaseExtractor._normalize_numeric_text(text)
        if field_name == "values":
            return SignalDatabaseExtractor._parse_value_mapping(text)
        if field_name == "receiver":
            return [item.strip() for item in text.replace(";", ",").split(",") if item.strip()]
        return text

    @staticmethod
    def _parse_value_mapping(text: str) -> Any:
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
        except (TypeError, ValueError):
            pass

        pairs = {}
        for part in text.replace("\n", ";").split(";"):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                key, value = part.split(":", 1)
            elif "=" in part:
                key, value = part.split("=", 1)
            else:
                return text
            pairs[key.strip()] = value.strip()
        return pairs if pairs else text


def parse_signal_database(
        source_file: str,
        output_file: Optional[str] = None,
        sheet_name: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Parse dbc or excel signal matrix and export a json file.
    """
    return SignalDatabaseExtractor().parse(source_file, output_file=output_file, sheet_name=sheet_name)


def extract_signal_database(
        source_file: str,
        output_file: Optional[str] = None,
        sheet_name: Optional[Any] = None
) -> str:
    """
    Parse dbc or excel signal matrix and return json file path.
    """
    extractor = SignalDatabaseExtractor()
    extractor.parse(source_file, output_file=output_file, sheet_name=sheet_name)
    return output_file or extractor.default_output_path(source_file)


# from common.dbc import parse_signal_database

# data = parse_signal_database(r"D:\demo\vehicle.dbc")
# data = parse_signal_database(r"D:\demo\signal_matrix.xlsx")
# data = parse_signal_database(
#     r"D:\demo\signal_matrix.xlsx",
#     output_file=r"D:\demo\signal_matrix.signals.json",
#     sheet_name=None,
# )
