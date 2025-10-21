# 工程运行流程（ASCII 绘图）

本文档用 ASCII 图解释本工程从输入到输出的整体数据流与关键模块职责。

## 总览

```
┌──────────────────────────────────────────────────────────────┐
│                   scripts/run_*.bat / .sh                    │
│  → 调用 python -m src.pipeline --images_dir --out_dir ...   │
└───────────────┬──────────────────────────────────────────────┘
                │
                v
        ┌───────────────────────┐
        │       pipeline        │ 解析 CLI 参数并组织流程
        │  --use_mineru?        │
        └─────────┬─────────────┘
                  │
        ┌─────────┴───────────┐
        │                     │
        v                     v
  MinerU 模式              本地 OCR 模式
```

## MinerU 模式（--use_mineru）

输入既可为图片也可为 PDF（放入 `images/`）。

```
images/*.png|*.jpg|*.pdf
          │
          v
┌───────────────────────────────────────────────────────┐
│ mineru_integration.run_mineru_on_file(page, tmp_dir)  │
│  - 调用 MinerUHelper.run_parse()                      │
│  - 自动判断新旧 CLI（是否需要 -p/--path）            │
│  - 输出至 out_dir/_mineru_tmp/<page>/auto             │
└───────────────┬───────────────────────────────────────┘
                │ JSON/Markdown
                v
┌───────────────────────────────────────────────────────┐
│ extract_question_blocks()                              │
│  - 从 MinerU 的 blocks/data 中拼接文本                 │
│  - 用题号样式正则粗切分为题目文本块                   │
└───────────────┬───────────────────────────────────────┘
                │ list[{text}]
                v
┌───────────────────────────────────────────────────────┐
│ structure_parser.parse_question(text)                  │
│  - 提取题号/题干/选项/候选答案                        │
└───────────────┬───────────────────────────────────────┘
                │ questions: List[Dict]
                v
        ┌───────────────┬────────────────┐
        │                                │
        v                                v
┌──────────────────────┐        ┌───────────────────────┐
│ export_md.export_... │        │ export_tex.export_... │
│ → outputs/worksheet.md│       │ → outputs/worksheet.tex│
└──────────────────────┘        └───────────────────────┘
```

备注：
- MinerU 负责版面/段落等结构抽取；本工程再用正则将题目粗切分。
- 当前实现中，插图路径直接指向输入页文件名；如需更精细的题图，可改为引用 `/_mineru_tmp/.../images/*.jpg`。

## 本地 OCR 模式（默认，不带 --use_mineru）

输入为图片（放入 `images/`）。

```
images/*.png|*.jpg|*.jpeg|*.bmp|*.tif|*.tiff
          │
          v
┌────────────────────────────────────────────┐
│ split_questions.cut_questions(page, tmp)   │
│  - OpenCV 去噪/阈值/形态学 + 连通域       │
│  - 输出题块小图：outputs/images/<stem>_q#.png│
└───────────────┬────────────────────────────┘
                │ crops: List[Path]
                v
┌────────────────────────────────────────────┐
│ ocr_extract.run_ocr(crop, use_pix2tex?)    │
│  文本：PaddleOCR（失败→Tesseract）        │
│  公式：pix2tex（失败→MathPix API）        │
└───────────────┬────────────────────────────┘
                │ {text, latex}
                v
┌────────────────────────────────────────────┐
│ structure_parser.parse_question(text)       │
└───────────────┬────────────────────────────┘
                │ questions + latex_list
                v
        ┌───────────────┬────────────────┐
        │                                │
        v                                v
┌──────────────────────┐        ┌───────────────────────┐
│ export_md.export_... │        │ export_tex.export_... │
│ → outputs/worksheet.md│       │ → outputs/worksheet.tex│
└──────────────────────┘        └───────────────────────┘
```

## 关键模块职责

- `src/pipeline.py`
  - 解析参数，组织两种模式的主流程。
  - `--format {md,tex,both}` 控制导出类型。

- `src/mineru_helper.py`
  - 检测 MinerU 版本，判断是否需要 `-p/--path`。
  - 在 PyTorch 2.6+ 环境下注册 `ultralytics` 到 `safe_globals`。

- `src/mineru_integration.py`
  - 调用 MinerU 并解析其输出（JSON/Markdown）。
  - 基于题号样式粗切分题目文本块。

- `src/split_questions.py`
  - OpenCV 版面分析，将整页切分为题块小图。

- `src/ocr_extract.py`
  - 文本 OCR：PaddleOCR 优先，失败回退 Tesseract。
  - 公式 OCR：本地 pix2tex 优先，失败回退 MathPix（需环境变量 `MATHPIX_APP_ID/KEY`）。

- `src/structure_parser.py`
  - 从原始文本解析题号/题干/选项/候选答案。

- `src/export_md.py` / `src/export_tex.py`
  - 将结构化题目与图片/公式渲染为 Markdown/LaTeX 文件。

- `src/utils.py`
  - `ensure_dir`、`detect_gpu_type`、选项切分工具等。

## 常用脚本与命令

- Windows：
  - `scripts\setup_env.bat` 安装依赖
  - `scripts\run_mineru.bat` 使用 MinerU 模式导出（默认 both）
  - `scripts\run_mineru_auto.bat` 自检 + 自动修复后运行

- 跨平台（示例）：
  - `python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru`
  - `python -m src.pipeline --images_dir images --out_dir outputs --format both --use_pix2tex`

## 输出与编译

- 主要输出：
  - `outputs/worksheet.md`
  - `outputs/worksheet.tex`
  - `outputs/images/`（在本地 OCR 模式下存放题块切图）

- LaTeX 编译（可选）：
  - 使用 XeLaTeX：`xelatex outputs/worksheet.tex`（模板内含 `ctex` 适配中文）。

