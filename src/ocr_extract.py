from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import os
from .utils import detect_gpu_type

def _ocr_with_paddle(img_path: Path) -> Optional[str]:
    """使用 PaddleOCR 识别通用中英文文本。

    - 自动根据 `detect_gpu_type()` 选择是否启用 GPU；失败时回退 CPU。
    - 将识别到的行文本按行拼接为一个字符串返回。

    返回：识别到的文本，失败返回 None。
    """
    try:
        from paddleocr import PaddleOCR
    except Exception:
        return None
    gpu=(detect_gpu_type()=="nvidia")
    try:
        ocr=PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=gpu)
    except Exception:
        ocr=PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False)
    res=ocr.ocr(str(img_path), cls=True)
    lines=[]
    for page in res:
        for line in page: lines.append(line[1][0])
    return "\n".join(lines).strip()

def _ocr_with_tesseract(img_path: Path) -> Optional[str]:
    """使用 Tesseract 识别中文简体+英文，作为 PaddleOCR 的备选方案。"""
    try:
        import pytesseract
        return pytesseract.image_to_string(Image.open(img_path), lang="chi_sim+eng")
    except Exception:
        return None

_pix2tex_model=None

def _ocr_formula_with_pix2tex(img_path: Path) -> Optional[str]:
    """使用本地 pix2tex 模型识别公式为 LaTeX。

    - 懒加载并缓存 `LatexOCR` 模型到 `_pix2tex_model`，避免重复初始化开销。
    - 返回识别到的 LaTeX 字符串；失败返回 None。
    """
    global _pix2tex_model
    try:
        from pix2tex.cli import LatexOCR
        if _pix2tex_model is None: _pix2tex_model=LatexOCR()
        img=Image.open(img_path).convert("RGB")
        return (_pix2tex_model(img) or "").strip()
    except Exception as e:
        print("[WARN] pix2tex failed:", e); return None

def _ocr_formula_with_mathpix(img_path: Path) -> Optional[str]:
    """调用 MathPix API 识别公式为 LaTeX（需要环境变量凭据）。

    需要设置：`MATHPIX_APP_ID` 与 `MATHPIX_APP_KEY`；若缺失直接返回 None。
    优先返回 `latex_styled` 字段，其次回退到 `latex`。
    """
    app_id=os.getenv("MATHPIX_APP_ID"); app_key=os.getenv("MATHPIX_APP_KEY")
    if not (app_id and app_key): return None
    try:
        import base64, requests
        with open(img_path,"rb") as f: b64=base64.b64encode(f.read()).decode()
        headers={"app_id":app_id,"app_key":app_key}
        data={"src":f"data:image/png;base64,{b64}","formats":["latex_styled"]}
        r=requests.post("https://api.mathpix.com/v3/text", headers=headers, json=data, timeout=20)
        if r.ok:
            js=r.json(); return (js.get("latex_styled") or js.get("latex") or "").strip() or None
    except Exception as e:
        print("[WARN] MathPix failed:", e)
    return None

def run_ocr(img_path: Path, use_pix2tex: bool=True) -> Dict[str, Any]:
    """对单张图片执行文本 OCR 与公式 OCR。

    流程：
    - 文本：优先 PaddleOCR，其次 Tesseract；
    - 公式：若 `use_pix2tex=True`，先试 pix2tex，失败再试 MathPix；否则直接试 MathPix。

    返回：{"text": 文本字符串, "latex": 公式 LaTeX 或 None}
    """
    text=_ocr_with_paddle(img_path) or _ocr_with_tesseract(img_path) or ""
    latex=_ocr_formula_with_pix2tex(img_path) if use_pix2tex else None
    if latex is None: latex=_ocr_formula_with_mathpix(img_path)
    return {"text": text, "latex": latex}
