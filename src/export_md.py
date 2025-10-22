from pathlib import Path
from typing import List, Dict, Any
import os
import re

MD_HEADER = "# 讲义题目（自动导出）\n"


def render_md_item(q: Dict[str, Any], img_rel: str, latex: str = None) -> str:
    """将单道题目渲染为 Markdown 片段。

    - 不输出整题题号（无任何标题级别）。
    - 保留题内小题号，但若被写成 Markdown 标题（如 "### 1"、"## （1）"），去掉开头的 #。
    """
    title = q.get("number") or ""
    body = q.get("text") or ""

    if body:
        def _strip_subq_heading(m: re.Match) -> str:
            num = m.group(1)
            rest = m.group(2) or ""
            return f"{num} {rest}".rstrip()

        # 仅移除行首的 Markdown 级别符号，保留小题号
        body = re.sub(
            r"(?m)^\s*#{1,6}\s*((?:\(\d+\)|（\d+）|\d+[、．\.）]))\s*(.*)$",
            _strip_subq_heading,
            body,
        )

    # 不使用任何 Markdown 级别为题号加样式，只输出纯文本题号一行
    s = ([f"{title}\n"] if title else []) + [body, "\n"]

    if latex:
        s.append(f"**LaTeX 公式（OCR）**: `{latex}`\n")

    if q.get("options"):
        for label, opt in q["options"]:
            s.append(f"- **{label}** {opt}")
        s.append("")

    if img_rel:
        alt = title or ""
        s.append(f"![{alt}]({img_rel})\n")

    if q.get("answer"):
        s.append(f"> 参考答案：{q['answer']}\n")

    return "\n".join(s)


def export_markdown(
    questions: List[Dict[str, Any]],
    img_paths: List[Path],
    latex_list,
    out_dir: Path,
) -> Path:
    """批量生成 `worksheet.md` 文件。"""
    out_md = out_dir / "worksheet.md"
    lines = [MD_HEADER]
    out_dir_resolved = out_dir.resolve()
    for (q, img, latex) in zip(questions, img_paths, latex_list):
        rel_str = ""
        if img:
            try:
                # Prefer a path relative to the output directory
                rel_path = Path(img).resolve().relative_to(out_dir_resolved)
                rel_str = rel_path.as_posix()
            except Exception:
                # Fallback to os.path.relpath in case img is on a different drive
                rel_str = os.path.relpath(str(img), str(out_dir)).replace("\\", "/")
        lines.append(render_md_item(q, rel_str, latex))
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_md
