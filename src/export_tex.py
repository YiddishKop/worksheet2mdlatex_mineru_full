\
from pathlib import Path
from typing import List, Dict, Any
import os, re
import os
TEX_TPL=r"""\
\documentclass[a4paper,12pt]{article}
\usepackage{ctex}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{enumitem}
\usepackage{geometry}
\geometry{margin=2cm}
\newenvironment{question}[1][]{\par\noindent\textbf{#1}\quad}{\par}
\begin{document}
\section*{讲义题目（自动导出）}
%__QUESTIONS__
\end{document}
"""

def render_tex_item(q:Dict[str,Any], img_rel:str, latex:str=None)->str:
    """将单道题目渲染为 LaTeX 环境片段。

    说明：
    - 以自定义环境 `question` 包裹题目，包含：题号/标题、题干正文、可选项、有图则插图、可选的参考答案。
    - 当 `latex` 存在时，在题干后增加一行“公式(OCR)”并以内联数学模式 `$...$` 展示。
    - 为避免 LaTeX 特殊字符冲突，对题干中的下划线进行转义处理。

    参数：
    - q: 题目结构字典，键同 Markdown 渲染函数。
    - img_rel: 图片相对路径（相对于最终 `.tex` 所在目录）。
    - latex: OCR 识别出的题内 LaTeX 公式字符串。

    返回：
    - 可直接拼接到文档模板中的 LaTeX 文本片段。
    """
    raw_body = q.get("text") or ""
    # 移除题干中的 Markdown 图片，避免噪音
    if raw_body:
        raw_body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", raw_body)
    title=q.get("number") or "题目"; body=(raw_body).replace("_", r"\_")
    s=[f"\\begin{{question}}[{title}]\n{body}\n"]
    if latex: s.append("\n\\par\\textbf{公式(OCR):} $%s$\n" % latex.replace("\\","\\\\"))
    if q.get("options"):
        s.append("\\begin{enumerate}[label=\\Alph*.]")
        for _,opt in q["options"]: s.append(f"\\item {opt}")
        s.append("\\end{enumerate}")
    if img_rel:
        s.append("\\begin{center}")
        s.append(f"\\includegraphics[width=0.75\\textwidth]{{{img_rel}}}")
        s.append("\\end{center}")
    if q.get("answer"): s.append(f"\\par\\textit{{参考答案：{q['answer']}}}")
    s.append("\\end{question}\n"); return "\n".join(s)

def export_latex(questions:List[Dict[str,Any]], img_paths:List[Path], latex_list, out_dir:Path)->Path:
    """批量导出 LaTeX 文件 `worksheet.tex`。

    说明：
    - 逐题调用 `render_tex_item` 生成块，插入到 `TEX_TPL` 模板占位符 `%__QUESTIONS__`。
    - 输出文件位于 `out_dir/worksheet.tex`，图片以 `images/<文件名>` 相对路径引用。

    参数：
    - questions: 题目结构化列表。
    - img_paths: 图片路径列表，与题目一一对应。
    - latex_list: 每题公式字符串列表。
    - out_dir: 输出目录。

    返回：
    - 生成的 `.tex` 文件路径。
    """
    out_tex=out_dir/"worksheet.tex"; blocks=[]
    out_dir_resolved = out_dir.resolve()
    for (q,img,latex) in zip(questions,img_paths,latex_list):
        rel_str = ""
        if img:
            try:
                rel_path = Path(img).resolve().relative_to(out_dir_resolved)
                rel_str = rel_path.as_posix()
            except Exception:
                rel_str = os.path.relpath(str(img), str(out_dir)).replace("\\", "/")
        blocks.append(render_tex_item(q, rel_str, latex))
    tex=TEX_TPL.replace("%__QUESTIONS__", "\n\n".join(blocks))
    out_tex.write_text(tex, encoding="utf-8"); return out_tex
