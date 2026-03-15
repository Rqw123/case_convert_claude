"""
Text normalization and semantic enhancement for test case steps.
Covers: synonym replacement, position aliases, range expansion,
negation handling, and enum value semantics.
"""
import re
from typing import Dict, List, Optional
from app.schemas.schemas import NormalizedCaseSemantics

# ---- Action synonyms ----
ACTION_OPEN = ["打开", "开启", "启动", "接通", "使能", "激活", "开"]
ACTION_CLOSE = ["关闭", "关掉", "关断", "断开", "停止", "禁用", "去激活", "关"]
ACTION_LOCK = ["锁止", "锁定", "上锁"]
ACTION_UNLOCK = ["解锁", "解除锁定"]
ACTION_ALL_OPEN = set(ACTION_OPEN)
ACTION_ALL_CLOSE = set(ACTION_CLOSE)

CANONICAL_ACTION = {}
for a in ACTION_OPEN:
    CANONICAL_ACTION[a] = "打开"
for a in ACTION_CLOSE:
    CANONICAL_ACTION[a] = "关闭"
for a in ACTION_LOCK:
    CANONICAL_ACTION[a] = "锁止"
for a in ACTION_UNLOCK:
    CANONICAL_ACTION[a] = "解锁"

# ---- Position synonyms ----
POSITION_ALIASES: Dict[str, List[str]] = {
    "主驾": ["主驾", "左前", "驾驶员", "驾驶位", "driver"],
    "副驾": ["副驾", "右前", "副驾驶", "乘客位", "passenger"],
    "左后": ["左后", "后排左", "后左"],
    "右后": ["右后", "后排右", "后右"],
}

# ---- Range expansion rules ----
RANGE_EXPANSION: Dict[str, List[str]] = {
    "左侧": ["左前", "左后"],
    "左边": ["左前", "左后"],
    "右侧": ["右前", "右后"],
    "右边": ["右前", "右后"],
    "前方": ["左前", "右前"],
    "前侧": ["左前", "右前"],
    "前排": ["左前", "右前"],
    "前部": ["左前", "右前"],
    "后方": ["左后", "右后"],
    "后侧": ["左后", "右后"],
    "后排": ["左后", "右后"],
    "后部": ["左后", "右后"],
    "尾部": ["左后", "右后"],
    "两侧": ["左前", "左后", "右前", "右后"],
    "四门": ["左前", "右前", "左后", "右后"],
    "全部": ["左前", "右前", "左后", "右后"],
    "所有": ["左前", "右前", "左后", "右后"],
    "整车": ["左前", "右前", "左后", "右后"],
    "全车": ["左前", "右前", "左后", "右后"],
    "驾驶位这一侧": ["左前", "左后"],
    "副驾这一侧": ["右前", "右后"],
}

# ---- Negation rules ----
NEGATION_WORDS = ["未", "不", "不是", "无", "没有", "未处于", "不处于", "未进入"]
NEGATION_ANTONYM: Dict[str, str] = {
    "打开": "关闭",
    "开启": "关闭",
    "接通": "断开",
    "使能": "禁用",
    "激活": "未激活",
    "关闭": "打开",
    "断开": "接通",
    "锁止": "解锁",
    "解锁": "锁止",
    "禁用": "使能",
}

NEGATION_PATTERNS = [
    (r"未打开|未开启|不是开启状态|没有打开", "关闭"),
    (r"未关闭|不是关闭状态|没有关闭", "打开"),
    (r"未接通|未连接", "断开"),
    (r"未使能|未激活", "禁用"),
    (r"未锁止|未上锁", "解锁"),
    (r"未解锁", "锁止"),
    (r"不处于激活状态|不是激活状态", "未激活"),
    (r"不处于开启状态|不是开启", "关闭"),
]

# ---- Enum value semantics ----
ENUM_LEVEL_PATTERNS = [
    (r"[一1]档|[一1]级|level\s*1", "Level1", "1"),
    (r"[二2]档|[二2]级|level\s*2", "Level2", "2"),
    (r"[三3]档|[三3]级|level\s*3", "Level3", "3"),
    (r"[四4]档|[四4]级|level\s*4", "Level4", "4"),
    (r"高档|高级|high", "High", None),
    (r"中档|中级|medium|middle", "Medium", None),
    (r"低档|低级|low", "Low", None),
    (r"最大|最高|最强|max|maximum", "__MAX__", None),
    (r"最小|最低|最弱|min(?!imum)", "__MIN__", None),
]


def normalize_case(case_id: str, text: str) -> NormalizedCaseSemantics:
    """
    Normalize a single test case step text and expand semantics.
    """
    sem = NormalizedCaseSemantics(case_id=case_id, original_text=text)

    # 1. Apply negation transformation
    neg_text = text
    neg_patterns_found = []
    for pattern, replacement in NEGATION_PATTERNS:
        if re.search(pattern, neg_text):
            neg_patterns_found.append(f"{pattern} → {replacement}")
            neg_text = re.sub(pattern, replacement, neg_text)
    sem.negative_patterns = neg_patterns_found
    sem.normalized_text = neg_text

    # 2. Extract action
    action_found = None
    for action in sorted(CANONICAL_ACTION.keys(), key=len, reverse=True):
        if action in neg_text:
            action_found = CANONICAL_ACTION[action]
            break
    sem.action = action_found

    # 3. Extract positions
    positions_found = []
    for pos_key, pos_aliases in POSITION_ALIASES.items():
        for alias in pos_aliases:
            if alias in neg_text and alias not in positions_found:
                positions_found.append(pos_key)
                break
    sem.positions = list(set(positions_found))

    # 4. Range expansion - identify range words and objects
    expanded = [neg_text]
    for range_word, sub_positions in RANGE_EXPANSION.items():
        if range_word in neg_text:
            # Try to find object in text
            obj = _extract_object(neg_text, range_word)
            action_str = _extract_action_str(neg_text)
            new_steps = []
            for sub_pos in sub_positions:
                if obj:
                    step = f"{sub_pos}{obj}{action_str}" if action_str else f"{sub_pos}{obj}"
                else:
                    step = neg_text.replace(range_word, sub_pos)
                new_steps.append(step)
            if new_steps and new_steps != [neg_text]:
                expanded = new_steps
                break
    sem.expanded_steps = list(dict.fromkeys(expanded))  # dedup preserving order

    # 5. Enum value semantics
    enum_semantics = {}
    for pattern, canonical, num_val in ENUM_LEVEL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            matched = re.search(pattern, text, re.IGNORECASE).group(0)
            enum_semantics[matched] = canonical
    sem.enum_value_semantics = enum_semantics

    return sem


def _extract_action_str(text: str) -> str:
    for action in sorted(CANONICAL_ACTION.keys(), key=len, reverse=True):
        if action in text:
            return action
    return ""


def _extract_object(text: str, range_word: str) -> str:
    """Try to extract the controlled object from the text."""
    # Remove range word to find the object
    cleaned = text.replace(range_word, "").strip()
    # Remove action words
    for action in sorted(CANONICAL_ACTION.keys(), key=len, reverse=True):
        cleaned = cleaned.replace(action, "")
    cleaned = cleaned.strip()
    return cleaned if cleaned else ""


def resolve_enum_value(text_val: str, signal_values: Dict[str, str]) -> Optional[str]:
    """
    Try to resolve a natural language value description to an enum key.
    Returns the key (e.g. "2") if found, else None.
    """
    if not signal_values:
        return None

    text_lower = text_val.lower().strip()

    # 1. Direct match by value label
    for k, v in signal_values.items():
        if v.lower() == text_lower:
            return k

    # 2. Level pattern
    for pattern, canonical, num_val in ENUM_LEVEL_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if canonical == "__MAX__":
                # Return the key with highest numeric value
                numeric_keys = []
                for k in signal_values:
                    try:
                        numeric_keys.append((int(k), k))
                    except ValueError:
                        pass
                if numeric_keys:
                    return max(numeric_keys)[1]
                return None
            elif canonical == "__MIN__":
                # Return lowest non-zero key
                numeric_keys = []
                for k in signal_values:
                    try:
                        n = int(k)
                        if n > 0:
                            numeric_keys.append((n, k))
                    except ValueError:
                        pass
                if numeric_keys:
                    return min(numeric_keys)[1]
                # fallback: lowest
                numeric_keys2 = []
                for k in signal_values:
                    try:
                        numeric_keys2.append((int(k), k))
                    except ValueError:
                        pass
                return min(numeric_keys2)[1] if numeric_keys2 else None
            else:
                # canonical like "Level2", "High" etc - match by value label
                for k, v in signal_values.items():
                    if canonical.lower() == v.lower():
                        return k
                    if num_val and v.lower() == f"level{num_val}":
                        return k
                # Try numeric
                if num_val:
                    if num_val in signal_values:
                        return num_val

    return None
