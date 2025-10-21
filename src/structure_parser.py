import re
from typing import Dict, Any
from .utils import split_options, has_likely_options

# 将原始题目文本解析为结构化字段：
# - 提取题号（例/练习/数字/括号数字等样式）；
# - 判断并拆分选择题选项 A-D；
# - 在原文中浅匹配一个候选答案；
# 返回字典：{"number", "text", "options", "answer"}。

def parse_question(raw_text:str)->Dict[str,Any]:
    text=raw_text.strip(); number=None
    m=re.match(r"^((?:例|练习)\s*\d+|\d+\s*[\.、)]|\(\d+\)|[（(]\s*\d+\s*[）)])", text)
    if m: number=m.group(1).strip(); text=text[m.end():].strip()
    options=split_options(text) if has_likely_options(text) else None
    answer=None; ans=re.search(r"(答案|解|选项)\s*[:：]?\s*([A-D]|[0-9]+|[①-⑩])", raw_text)
    if ans: answer=ans.group(2)
    return {"number":number,"text":text,"options":options,"answer":answer}


def parse_question_v2(raw_text: str) -> Dict[str, Any]:
    """增强版题目解析：更全面的题头与答案样式。
    - 题头：【例1】/【练习2】/【题3】/第4题/1. / 1、 / （1）/ (2)
    - 答案：【答案】D / 参考答案：D / 答案：12 / 答案：√/×/对/错
    """
    text = raw_text.strip()
    number = None

    # 题头（取整段起始标记作为题号保留）
    header_pat = re.compile(
        r"^\s*(?:"
        r"【\s*(?:例|练习|题|变式)\s*\d*】|"   # 【例1】/【题2】/【变式】
        r"第\s*\d+\s*题|"                      # 第1题
        r"(?:例|练习)\s*\d+\s*[\.、．)]|"     # 例1. / 练习2、
        r"\d+\s*[\.、．)]|"                     # 1. / 2、 / 3．
        r"[（(]\s*\d+\s*[）)]"                  # （1） / (2)
        r")",
        re.UNICODE,
    )
    m = header_pat.match(text)
    if m:
        number = m.group(0).strip()
        text = text[m.end():].lstrip()

    # 选项解析
    options = split_options(text) if has_likely_options(text) else None

    # 答案解析（优先匹配“参考答案/答案”）
    answer = None
    answer_pats = [
        r"【?\s*(?:参考答案|答案)\s*】?\s*[:：]?\s*([A-H])\b",
        r"【?\s*(?:参考答案|答案)\s*】?\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?)",
        r"【?\s*(?:参考答案|答案)\s*】?\s*[:：]?\s*(√|×|对|错)",
        r"选项\s*[:：]?\s*([A-H])\b",
    ]
    for pat in answer_pats:
        ans = re.search(pat, raw_text)
        if ans:
            answer = ans.group(1)
            break

    return {"number": number, "text": text, "options": options, "answer": answer}
