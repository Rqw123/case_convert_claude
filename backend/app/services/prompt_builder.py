"""
Prompt construction service for DeepSeek LLM matching.
"""
import json
from typing import List, Tuple
from app.schemas.schemas import FlatSignal, NormalizedCaseSemantics

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是一个汽车信号匹配专家。你的任务是根据自然语言测试用例描述，在提供的候选信号列表中找到最匹配的CAN信号。

## 核心规则
1. 你只能从提供的候选信号列表中查找匹配项，严禁虚构任何信号名、报文ID、信号值或信号描述。
2. 一条测试用例可能对应多个信号，必须全部找出。
3. 如果在候选信号中找不到合适匹配，必须明确返回 matched=false，并说明原因，严禁猜测。
4. 输出必须严格遵守JSON格式，不得包含任何额外文字。

## 语义理解规则

### 位置等价关系
- 主驾 = 左前 = 驾驶员侧
- 副驾 = 右前 = 乘客侧
- 左侧 = 左前 + 左后（需展开为多个信号）
- 右侧 = 右前 + 右后（需展开为多个信号）
- 前排 = 左前 + 右前（需展开为多个信号）
- 后排 = 左后 + 右后（需展开为多个信号）
- 全部/所有/整车 = 左前+右前+左后+右后（需展开为多个信号）

### 动作同义词
- 打开类：打开、开启、启动、接通、使能、激活 → 通常对应信号值 ON/1/Enable
- 关闭类：关闭、关掉、关断、断开、停止、禁用 → 通常对应信号值 OFF/0/Disable

### 否定式转换
- 未打开 = 关闭
- 未关闭 = 打开
- 未接通 = 断开
- 未使能 = 禁用
- 不处于激活状态 = 未激活
- 不是开启状态 = 关闭

### 枚举值语义
- 1档/一级/Level1 → 枚举值 Level1 对应的key
- 2档/二级/Level2 → 枚举值 Level2 对应的key
- 高档/High → 枚举中的 High
- 中档/Medium/Middle → 枚举中的 Medium/Middle
- 低档/Low → 枚举中的 Low
- 最大/最高/最强 → 枚举集合中数值最高的有效等级
- 最小/最低/最弱 → 枚举集合中最低的有效非关闭等级（注意区分Off和Level1）

## 输出格式
严格按以下JSON格式输出，不要加任何解释或markdown代码块：
{
  "case_id": "用例ID",
  "case_step": "原始用例步骤",
  "matched": true或false,
  "case_info": [
    {
      "signal_name": "信号名",
      "msg_id": "报文ID十六进制",
      "signal_desc": "信号描述",
      "signal_val": "目标信号值（枚举key）",
      "info_str": "【msg_id, signal_name, signal_val】",
      "match_reason": "匹配原因简述"
    }
  ],
  "unmatched_reason": "未匹配原因（matched为true时为null）"
}

## Few-shot示例

示例1（直接匹配）：
用例：打开主驾座椅加热
候选信号包含：DrHeatSts（主驾加热状态，values: {"0":"OFF","1":"ON"}，msg_id:0x22A）
输出：
{"case_id":"tc_001","case_step":"打开主驾座椅加热","matched":true,"case_info":[{"signal_name":"DrHeatSts","msg_id":"0x22A","signal_desc":"主驾加热状态","signal_val":"1","info_str":"【0x22A, DrHeatSts, 1】","match_reason":"主驾=左前，打开=ON=1"}],"unmatched_reason":null}

示例2（多信号展开）：
用例：关闭左侧车窗
候选信号包含：FLWinCtrl（左前车窗，values:{"0":"Close","1":"Open"}），RLWinCtrl（左后车窗，values:{"0":"Close","1":"Open"}）
输出：
{"case_id":"tc_002","case_step":"关闭左侧车窗","matched":true,"case_info":[{"signal_name":"FLWinCtrl","msg_id":"0x100","signal_desc":"左前车窗控制","signal_val":"0","info_str":"【0x100, FLWinCtrl, 0】","match_reason":"左侧展开为左前，关闭=0"},{"signal_name":"RLWinCtrl","msg_id":"0x100","signal_desc":"左后车窗控制","signal_val":"0","info_str":"【0x100, RLWinCtrl, 0】","match_reason":"左侧展开为左后，关闭=0"}],"unmatched_reason":null}

示例3（否定式）：
用例：主驾车窗未关闭
输出：matched=true，找主驾车窗对应信号，signal_val对应"Open/1"，match_reason说明"未关闭=打开"

示例4（枚举值）：
用例：空调风量调到2档
候选信号包含FanSpeed，values:{"0":"Off","1":"Level1","2":"Level2","3":"Level3"}
输出：signal_val="2"，match_reason="2档=Level2，key为2"

示例5（未匹配）：
用例：打开天窗遮阳
候选信号中无天窗遮阳相关信号
输出：{"case_id":"tc_005","case_step":"打开天窗遮阳","matched":false,"case_info":[],"unmatched_reason":"候选信号中未找到天窗遮阳相关信号"}
"""


def build_user_prompt(
    case_id: str,
    case_step: str,
    semantics: NormalizedCaseSemantics,
    candidates: List[Tuple[FlatSignal, float, List[str]]],
) -> str:
    lines = []
    lines.append(f"## 当前测试用例")
    lines.append(f"用例ID：{case_id}")
    lines.append(f"用例步骤：{case_step}")
    lines.append("")

    if semantics.normalized_text and semantics.normalized_text != case_step:
        lines.append(f"## 语义归一化说明")
        lines.append(f"归一化后：{semantics.normalized_text}")

    if semantics.expanded_steps and semantics.expanded_steps != [case_step]:
        lines.append(f"展开子步骤：{' | '.join(semantics.expanded_steps)}")

    if semantics.enum_value_semantics:
        lines.append(f"值语义映射：{json.dumps(semantics.enum_value_semantics, ensure_ascii=False)}")
    lines.append("")

    lines.append(f"## 候选信号列表（共{len(candidates)}条）")
    for rank, (sig, score, reasons) in enumerate(candidates, 1):
        sig_info = {
            "rank": rank,
            "signal_name": sig.signal_name,
            "msg_id_hex": sig.msg_id_hex,
            "signal_desc": sig.signal_desc or "",
            "message_name": sig.message_name or "",
            "values": sig.values,
            "unit": sig.unit or "",
        }
        lines.append(json.dumps(sig_info, ensure_ascii=False))
    lines.append("")
    lines.append(f"请根据以上信息，严格按照JSON格式输出匹配结果。case_id必须为：{case_id}")

    return "\n".join(lines)
