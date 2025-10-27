from pathlib import Path
from typing import List, Dict, Any
import json
from PIL import Image
import re


def image_to_single_pdf(img_path: Path) -> Path:
    """将单张图片转为单页 PDF 并返回 PDF 路径。

    用途：
    - 当后续流程更偏好或仅接受 PDF 输入时，将图片临时封装为单页 PDF。

    参数：
    - img_path: 源图片路径。

    返回：
    - 生成的 PDF 文件路径（与图片同名，后缀改为 .pdf）。
    """
    pdf_path = img_path.with_suffix(".pdf")
    img = Image.open(img_path).convert("RGB")
    img.save(pdf_path, "PDF", resolution=300.0)
    return pdf_path


from .mineru_helper import MinerUHelper


def run_mineru_on_file(input_path: Path, work_dir: Path) -> Dict[str, Any] | None:
    """对单个文件（图片/PDF）调用 MinerU 并返回解析结构。

    行为：
    - 首选通过 `MinerUHelper.run_parse` 调用 MinerU，自动适配新旧 CLI 语法；
    - 若未得到结果，则在 `work_dir` 下递归兜底查找 `*.md` 或 `*.json` 文件：
      - 发现 Markdown：包装为 {"blocks": [{"type": "markdown", "text": ...}]} 返回；
      - 发现 JSON：读取为字典返回；
    - 若仍无可用输出，返回 None。

    参数：
    - input_path: 输入图片或 PDF 路径。
    - work_dir: MinerU 工作/输出目录（应可写）。
    """
    res = MinerUHelper.run_parse(input_path, work_dir)
    if res:
        return res

    # 兼容兜底：递归查找 md/json 输出
    try:
        md_files = sorted(work_dir.rglob("*.md"))
    except Exception:
        md_files = []
    if md_files:
        try:
            return {"blocks": [{"type": "markdown", "text": md_files[0].read_text(encoding="utf-8")}]} 
        except Exception:
            pass

    try:
        json_files = sorted(work_dir.rglob("*.json"))
    except Exception:
        json_files = []
    for jf in json_files:
        try:
            return json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue

    return None


def extract_question_blocks(mineru_struct: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 MinerU 的结构化输出里，基于“题号”样式粗切分题目文本块。

    策略：
    - 合并 blocks/data 下各元素的文本字段（text/markdown/content）。
    - 使用匹配“例/练习/数字/括号数字”等题号样式的正则进行切分。
    - 过滤空段，返回 [{"type": "question_text", "text": "..."}] 列表。

    参数：
    - mineru_struct: MinerU 的解析结果（dict）。

    返回：
    - 题目文本块列表，可能为空。
    """
    import re

    qre= re.compile(
        r"(?m)^\s*(?:>\s*)*"
        r"("  # 捕获用于命名的标签文本
        r"(?:"
        r"\d+[．.]|\d+[)]|"                     # 1. / 1) / 1．
        r"【例\d+】|【练习\d+】|【变式\d*-*\d*】|" # 【例1】/【练习1】/【变式1-1】
        r"例\d+|练习\d+|变式\d+|"
        r"【答案】|【解析】|【详解】|【参考答案】|"
        r"答案[:：]?|解析[:：]?|详解[:：]?|参考答案[:：]?"
        r")"
        r")\s*"
    )
    
    blocks = mineru_struct.get("blocks") or mineru_struct.get("data") or []
    texts: List[str] = []
    for blk in blocks:
        t = blk.get("text") or blk.get("markdown") or blk.get("content") or ""
        if isinstance(t, str):
            texts.append(t)
    raw = "\n\n".join(texts).strip()
    if not raw:
        return []

    pieces = qre.split(raw)
    merged: List[str] = []
    buf = ""
    i = 0
    while i < len(pieces):
        seg = pieces[i]
        if i + 2 < len(pieces) and qre.match(pieces[i] + pieces[i + 1]):
            if buf.strip():
                merged.append(buf.strip())
            buf = (pieces[i + 1] + (pieces[i + 2] or "")).strip()
            i += 3
        else:
            buf += (seg or "")
            i += 1
    if buf.strip():
        merged.append(buf.strip())

    return [{"type": "question_text", "text": m} for m in merged if m.strip()]


def robust_question_blocks(mineru_struct: Dict[str, Any]) -> List[Dict[str, Any]]:
    """改进版题块切分：
    - 支持：【例1】/【变式】/【题1】/第1题/1. /（1）等题头；
    - 忽略 噪声标题：模型/题型展示/方法点拨/目录/答案/解析/详解/参考答案；
    - 未命中题头时，返回整段文本一个题块。
    """
    import re
    blocks = mineru_struct.get("blocks") or mineru_struct.get("data") or []
    texts: List[str] = []
    for blk in blocks:
        t = blk.get("text") or blk.get("markdown") or blk.get("content") or ""
        if isinstance(t, str):
            texts.append(t)
    raw = "\n\n".join(texts).strip()
    if not raw:
        return []

    head_pat = re.compile(
        r"(?m)^\s*(?:>\s*)*(?:#+\s*)?(?:"
        r"【\s*(?:例|练习|题|变式)\s*\d*】|"
        r"第\s*\d+\s*题|"
        r"(?:例|练习)\s*\d+\s*[\.、．)]|"
        r"\d+\s*[\.、．)]|"
        r"[（(]\s*\d+\s*[）)]"
        r")"
    )
    noise_pat = re.compile(r"模型|题型展示|方法点拨|目录|参考答案|答案|解析|详解")

    starts: List[int] = []
    for m in head_pat.finditer(raw):
        token = m.group(0)
        if noise_pat.search(token):
            continue
        starts.append(m.start())

    if not starts:
        return [{"type": "question_text", "text": raw}]

    starts.sort()
    out: List[str] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(raw)
        seg = raw[s:e].strip()
        if seg:
            out.append(seg)

    return [{"type": "question_text", "text": s} for s in out]

def mineru_parse_to_questions(page_path: Path, tmp_dir: Path) -> List[Dict[str, Any]]:
    """对单个页面文件调用 MinerU 并提取题目块列表。

    行为：
    - 直接将输入图片或 PDF 交给 MinerU（其内部已支持图片转 PDF），避免我们重复转换；
    - 使用传入的 `tmp_dir` 作为 MinerU 工作目录（会创建）；
    - 解析 MinerU 输出并切分为题目文本块后返回。

    参数：
    - page_path: 输入单页图片或 PDF 路径。
    - tmp_dir: MinerU 的工作临时目录。

    返回：
    - 题目块字典列表（可能为空列表）。
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    input_path = page_path  # MinerU 原生支持图片，内部会自行处理为 PDF
    work_subdir = tmp_dir / input_path.stem
    work_subdir.mkdir(parents=True, exist_ok=True)
    res = run_mineru_on_file(input_path, work_subdir)
    if not res:
        return []
    # 回撤跨页合并：仅使用基于文本的稳健切分
    return robust_question_blocks(res)


# ---------------------------
# 跨页合并（基于 *_middle.json）
# ---------------------------

def _find_middle_json(work_dir: Path) -> Path | None:
    try:
        cands = sorted(work_dir.rglob("*_middle.json"))
        return cands[0] if cands else None
    except Exception:
        return None


def _extract_blocks_from_pdf_info(pdf_info: List[Dict[str, Any]]) -> tuple[list[dict], dict[int, float]]:
    """从 middle.json 的 pdf_info 中抽取顺序块和每页高度。
    返回：
    - blocks: [{page_idx,x0,y0,x1,y1,text,type}]
    - page_heights: {page_idx: height}
    """
    blocks: list[dict] = []
    page_heights: dict[int, float] = {}

    def _gather_text(blk: Dict[str, Any]) -> str:
        tparts: list[str] = []
        # 常见结构：lines -> spans -> content/html/image_path
        for line in blk.get("lines", []) or []:
            for sp in line.get("spans", []) or []:
                if isinstance(sp, dict):
                    if sp.get("type") == "table" and sp.get("image_path"):
                        # 以图片形式插入表格快照
                        tparts.append(f"![](images/{sp['image_path']})")
                    elif "content" in sp and isinstance(sp["content"], str):
                        tparts.append(sp["content"])
        # table 块也可能通过 spans.html 提供 HTML，这里不做复杂解析
        return "\n".join([p for p in tparts if str(p).strip()])

    for page in pdf_info:
        pidx = int(page.get("page_idx") or page.get("page_index") or 0)
        ps = page.get("page_size") or [0, 0]
        if isinstance(ps, (list, tuple)) and len(ps) >= 2:
            page_heights[pidx] = float(ps[1])
        else:
            page_heights[pidx] = 1000.0

        # 优先使用 para_blocks，其次 preproc_blocks
        seq = page.get("para_blocks") or page.get("preproc_blocks") or []
        for blk in seq:
            bbox = blk.get("bbox") or [0, 0, 0, 0]
            x0, y0, x1, y1 = [float(b) for b in bbox[:4]] if len(bbox) >= 4 else (0.0, 0.0, 0.0, 0.0)
            text = _gather_text(blk)
            btype = str(blk.get("type") or "text")
            blocks.append({
                "page_idx": pidx,
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "text": (text or "").strip(),
                "type": btype,
            })

    # 排序：页、y、x
    blocks.sort(key=lambda b: (b["page_idx"], b["y0"], b["x0"]))
    return blocks, page_heights


_HEAD_PAT = re.compile(
    r"(?m)^\s*(?:>\s*)*(?:#+\s*)?(?:"
    r"【\s*(?:例|练习|题|变式)\s*\d*】|"
    r"第\s*\d+\s*题|"
    r"(?:例|练习)\s*\d+\s*[\.、．)]|"
    r"\d+\s*[\.、．)]\s+(?:如图|已知|设|第|题|证明|求|解|若|函数|计算|在)\S.*|"
    r"[（(]\s*\d+\s*[）)]"
    r")"
)
_SUBQ_PAT = re.compile(r"^\s*[（(]\s*\d+\s*[）)]")
_SOLUTION_PAT = re.compile(r"^\s*(?:【?\s*(?:答案|解析|详解|参考答案)\s*】?|解法\s*(?:\d+|[一二三四五六七八九十]+)\s*[:：]?)")


def _x_overlap_ratio(a: dict, b: dict) -> float:
    a0, a1 = a["x0"], a["x1"]
    b0, b1 = b["x0"], b["x1"]
    left = max(a0, b0)
    right = min(a1, b1)
    inter = max(0.0, right - left)
    aw, bw = max(1.0, a1 - a0), max(1.0, b1 - b0)
    base = min(aw, bw)
    return inter / base if base > 0 else 0.0


def build_questions_from_middle_json(work_dir: Path) -> List[Dict[str, Any]]:
    mid = _find_middle_json(work_dir)
    if not mid or not mid.exists():
        return []
    data = json.loads(mid.read_text(encoding="utf-8", errors="ignore"))
    pdf_info = data.get("pdf_info")
    if not isinstance(pdf_info, list) or not pdf_info:
        return []

    blocks, page_heights = _extract_blocks_from_pdf_info(pdf_info)
    if not blocks:
        return []

    BOTTOM_RATIO = 0.88
    X_OVERLAP_REQ = 0.5

    out: list[Dict[str, Any]] = []
    buf: list[str] = []
    buf_has_head = False
    prev: dict | None = None

    def flush():
        nonlocal buf, buf_has_head
        txt = "\n\n".join([t for t in buf if t.strip()]).strip()
        if txt:
            out.append({"type": "question_text", "text": txt})
        buf = []
        buf_has_head = False

    for cur in blocks:
        text = cur.get("text") or ""
        if not text and cur.get("type") not in ("title",):
            prev = cur
            continue

        is_head = (cur.get("type") == "title") or bool(_HEAD_PAT.match(text))
        is_subq = bool(_SUBQ_PAT.match(text))
        is_sol = bool(_SOLUTION_PAT.match(text))

        if is_head:
            # 强信号：起新题
            flush()
            buf.append(text)
            buf_has_head = True
            prev = cur
            continue

        if prev is None:
            buf.append(text)
            prev = cur
            continue

        # 跨页合并判断
        should_merge = True
        if cur["page_idx"] != prev["page_idx"]:
            ph = page_heights.get(prev["page_idx"], 1000.0)
            near_bottom = (prev["y1"] >= BOTTOM_RATIO * ph)
            xol = _x_overlap_ratio(prev, cur)
            # 跨页时：靠近页底 + 非标题，且水平重叠满足；或 小问延续且已有题头
            should_merge = (near_bottom and (not is_head) and (xol >= X_OVERLAP_REQ)) or (is_subq and buf_has_head)

        # 非跨页也允许合并，除非这是一个强标题（上面已处理）
        if should_merge:
            buf.append(text)
        else:
            flush()
            buf.append(text)
        prev = cur

    flush()
    return out
