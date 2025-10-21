from pathlib import Path
from typing import List, Dict, Any
import os, re
import os
MD_HEADER="# 讲义题目（自动导出）\n"

def render_md_item(q:Dict[str,Any], img_rel:str, latex:str=None)->str:
    """将单道题目渲染为 Markdown 片段。

    说明：
    - 输入结构化题目字典，拼接成含标题、正文、选项、答案和图片的 Markdown。
    - 若提供公式字符串 `latex`，以行内代码形式附加，便于后续排版或校对。

    参数：
    - q: 题目结构字典：`number`(题号)、`text`(题干)、`options`([(标签,文案)] 列表)、`answer`(答案)。
    - img_rel: 图片相对路径，用于 Markdown 图片引用。
    - latex: 题目内公式的 LaTeX 文本，None 表示无。

    返回：
    - Markdown 文本片段（字符串）。
    """
    title=q.get("number") or "题目"; body=q.get("text") or ""
    # 移除题干中的 Markdown 图片，避免引用两次
    if body:
        body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
    s=[f"### {title}\n", body, "\n"]
    if latex: s.append(f"**LaTeX 公式（OCR）**: `{latex}`\n")
    if q.get("options"):
        for label,opt in q["options"]: s.append(f"- **{label}** {opt}")
        s.append("")
    if img_rel: s.append(f"![{title}]({img_rel})\n")
    if q.get("answer"): s.append(f"> 参考答案：{q['answer']}\n")
    return "\n".join(s)

def export_markdown(questions:List[Dict[str,Any]], img_paths:List[Path], latex_list, out_dir:Path)->Path:
    """批量生成 `worksheet.md` 文件。

    说明：
    - 将题目、图片、公式逐一合并渲染成 Markdown，并写入 `out_dir/worksheet.md`。
    - 图片路径统一以 `images/<文件名>` 相对引用，便于与 LaTeX 导出共享同一资源目录。

    参数：
    - questions: 题目结构化列表，与 `img_paths`、`latex_list` 顺序对齐。
    - img_paths: 每道题的图片路径列表。
    - latex_list: 每道题的公式字符串列表（可为 None）。
    - out_dir: 输出目录。

    返回：
    - 生成的 Markdown 文件路径。
    """
    out_md=out_dir/"worksheet.md"; lines=[MD_HEADER]
    out_dir_resolved = out_dir.resolve()
    for (q,img,latex) in zip(questions,img_paths,latex_list):
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
    out_md.write_text("\n".join(lines), encoding="utf-8"); return out_md
