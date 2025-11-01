from pathlib import Path
from typing import List, Dict, Any
import os
import re

TEX_TPL = r"""\
\documentclass[a4paper,12pt]{article}
% Fonts and CJK setup (XeLaTeX)
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{unicode-math}
\setmainfont{SimSun}
\setCJKmainfont{SimSun}
\setmathfont{XITS Math}
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


def render_tex_item(q: Dict[str, Any], img_rel: str, latex: str = None) -> str:
    """灏嗗崟閬撻鐩覆鏌撲负 LaTeX 鐗囨锛堝寘鍚鍐?Markdown 鍥剧墖锛夈€?
    - 鐢?question 鐜鍖呰９棰樺潡锛?    - 灏嗛骞蹭腑鐨?`![]()` 杞负 `\includegraphics` 骞舵彃鍏ワ紱
    - 瀵归潪鍥剧墖鐗囨鐨勪笅鍒掔嚎杩涜杞箟锛岄伩鍏?LaTeX 鐗规畩瀛楃鍐茬獊銆?    """

    raw_body = q.get("text") or ""

    # 灏嗛骞蹭腑鐨?Markdown 鍥剧墖鏇挎崲涓?LaTeX 鍥剧墖鍧楋紱涓洪伩鍏嶈矾寰勪腑涓嬪垝绾胯杞箟锛屽厛鐢ㄥ崰浣嶇鏇挎崲
    img_pat = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    parts: list[str] = []
    placeholders: list[tuple[str, str]] = []
    last = 0
    for m in img_pat.finditer(raw_body):
        parts.append(raw_body[last:m.start()])
        path = (m.group(1) or "").strip()
        idx = len(placeholders)
        token = f"<<IMG{idx}>>"
        block = "\n".join(
            [
                "\\begin{center}",
                f"\\includegraphics[width=0.75\\textwidth]{{{path}}}",
                "\\end{center}",
            ]
        )
        placeholders.append((token, block))
        parts.append(token)
        last = m.end()
    parts.append(raw_body[last:])

    merged = "".join(parts)
    # 转义非图片占位符之外内容的部分特殊字符
    body = merged.replace("_", r"\\_")
    body = body.replace("#", r"\\#")
    body = body.replace("%", r"\\%")
    body = body.replace("&", r"\\&")
    # 还原图片占位符
    for token, block in placeholders:
        body = body.replace(token, block)

    title = q.get("number") or "题目"
    s = [f"\\begin{{question}}[{title}]\n{body}\n"]

    if latex:
        s.append("\n\\par\\textbf{公式 (OCR):} $%s$\n" % latex.replace("\\", "\\\\"))

    if q.get("options"):
        s.append("\\begin{enumerate}[label=\\Alph*.]")
        for _, opt in q["options"]:
            s.append(f"\\item {opt}")
        s.append("\\end{enumerate}")

    # 鑻ヤ笂娓稿崟鐙彁渚涗簡浠ｈ〃鍥剧墖璺緞涔熶竴骞舵彃鍏ワ紙閬垮厤缂哄浘鍦烘櫙锛?    if img_rel:
        s.append("\\begin{center}")
        s.append(f"\\includegraphics[width=0.75\\textwidth]{{{img_rel}}}")
        s.append("\\end{center}")

    if q.get("answer"):
        s.append(f"\\par\\textit{{参考答案：{q['answer']}}}")

    s.append("\\end{question}\n")
    return "\n".join(s)


def export_latex(
    questions: List[Dict[str, Any]],
    img_paths: List[Path],
    latex_list,
    out_dir: Path,
) -> Path:
    """鎵归噺瀵煎嚭 LaTeX 鏂囦欢 `worksheet.tex`銆?
    - 閫愰璋冪敤 `render_tex_item` 鐢熸垚鍧楋紝鎻掑叆鍒版ā鏉?`%__QUESTIONS__` 鍗犱綅绗︺€?    - 鍥剧墖璺緞浼樺厛浣跨敤棰樺共鍐?Markdown 鍥剧墖锛涜嫢鍚屾椂鎻愪緵 `img_paths`锛屼篃浼氶澶栨彃鍏ヤ唬琛ㄥ浘銆?    """

    out_tex = out_dir / "worksheet.tex"
    blocks: list[str] = []
    out_dir_resolved = out_dir.resolve()
    for (q, img, latex) in zip(questions, img_paths, latex_list):
        rel_str = ""
        if img:
            try:
                rel_path = Path(img).resolve().relative_to(out_dir_resolved)
                rel_str = rel_path.as_posix()
            except Exception:
                rel_str = os.path.relpath(str(img), str(out_dir)).replace("\\", "/")
        blocks.append(render_tex_item(q, rel_str, latex))
    tex = TEX_TPL.replace("%__QUESTIONS__", "\n\n".join(blocks))
    out_tex.write_text(tex, encoding="utf-8")
    return out_tex


