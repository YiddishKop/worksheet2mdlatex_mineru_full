# worksheet2mdlatex_mineru_full

一个将题目图/整页 PDF 解析为 Markdown + LaTeX 的流水线，集成 MinerU、OCR、Pandoc，并提供题目切分与公式/图片的修复与规范化。

入口与产物总览：

- 入口 A（命令行）
  - `venv310\Scripts\python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru`
- 入口 B（批处理）
  - `scripts\run_mineru_auto.bat`

ASCII 流程图（函数/脚本调用路线与最终产物）：

```
                         +----------------------------+
                         |     images/*.pdf/*.jpg     |
                         +-------------+--------------+
                                       |
                                       v
    (入口 A) python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru
                       [soft-fail note] if rc!=0 and outputs/worksheet.md exists -> continue; else fail
                                       |
                      +----------------+----------------+
                      |                                 |
                      v                                 v
         outputs/worksheet.md               outputs/worksheet.tex (MinerU/自导出)
                                                    |
                                                    v
                                     outputs/worksheet_pandoc.tex (Pandoc)

     (入口 B) scripts\run_mineru_auto.bat
        |
        +--> Normalize 题号到一行         (scripts/normalize_md_question_titles.py)
        |
        +--> 在“解析:”“解法<n>:”前换行   (scripts/insert_linebreaks_before_solutions.py)
        |
        +--> 修复图片链接/同步图片库      (scripts/sync_qs_image_db_and_fix_links.py)
        |
        +--> 切分 worksheet.md 为题目片段  (scripts/split_md_to_parts.py)
        |        └─ 输出到 qs_DB/<文档名>/<n>_<文档名>_<标签>.md
        |
        +--> v1 + v2 生成逐题 LaTeX 片段   (scripts/batch_v1_v2_to_latex.py)
        |        ├─ v1: scripts/v1_fix_math_dollor.py  (临时文件, 不落地)
        |        └─ v2: scripts/v2_fix_uni_to_latex.py -> qs_DB/*.latex
        |
        └--> Pandoc 导出 (scripts/pandoc_export.bat) -> outputs/worksheet_pandoc.tex[/.pdf]
```

主要目标：
- 快速生成 `outputs/worksheet.md` 与 `outputs/worksheet.tex`/`outputs/worksheet_pandoc.tex`
- 将 `worksheet.md` 切分为逐题 `qs_DB/*.md`
- 对逐题 MD 串联 v1/v2 处理，直接产出可嵌入的 `qs_DB/*.latex`
- 统一图片资源库路径，修复带空格/中文路径的渲染兼容性

## 快速开始（Windows）

1) 初始化环境（创建并使用本项目自带 venv）：
- 运行：`scripts\setup_env.bat`

2) 放置输入：
- 将图片或 PDF 放入 `images/`

3) 一键运行流水线：
- 运行：`scripts\run_mineru_auto.bat`

完成后查看：
- `outputs/worksheet.md`
- `outputs/worksheet.tex` 与 `outputs/worksheet_pandoc.tex`
- `qs_DB/*.md` 和对应的 `qs_DB/*.latex`

## 关键设计与约定

- 统一 MinerU 到 venv
  - 我们在激活的 venv 中安装 MinerU，并优先用当前解释器调用：`python -m mineru ...`，避免系统 PATH 上的其他 MinerU 干扰。
  - 相关逻辑：`src/mineru_helper.py` 使用 `sys.executable -m mineru`，失败时才回退到 PATH 中的 `mineru`。

- 输出与中间文件策略
  - `qs_DB/<文档名>/` 仅保留源 `md_part_<文档名>_<标签>.md` 与最终 `<n>_<文档名>_<标签>.latex`。
  - v1 的中间结果通过临时目录承载，不会在仓库中留下 `*.v1.md`。历史遗留的 `*.v1.md` 会被清理。

- 图片链接修复与兼容
  - 将 MinerU 产生的图片复制/汇聚到 `qs_image_DB/<文档名>/`。
  - 在 `outputs/worksheet.md` 内重写所有图片链接为 DB 相对路径；若 URL 含空格/非 ASCII，会自动使用尖括号 `![](<...>)` 包裹以适配严格渲染器。
  - 在切分到 `qs_DB/<文档名>/` 时会根据目录深度自动调整相对路径（例如 `../qs_image_DB/...` 变为 `../../qs_image_DB/...`）。

## 自动流水线步骤（scripts\run_mineru_auto.bat）

1) 环境检查与 venv 激活
2) 安装/校验 MinerU（安装到当前 venv）
3) 运行主管线：`python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru`
4) 题号与题干合并到一行：`scripts/normalize_md_question_titles.py`
5) 在“解析：”“解法<n>：”前插入换行：`scripts/insert_linebreaks_before_solutions.py`
6) 同步图片库并修复 `worksheet.md` 链接：`scripts/sync_qs_image_db_and_fix_links.py`
7) 将 `worksheet.md` 按规则切分为逐题 MD：`scripts/split_md_to_parts.py`（输出到 `qs_DB/`）
8) 串联 v1/v2 生成逐题 LaTeX 片段：`scripts/batch_v1_v2_to_latex.py`
   - v1：`scripts/v1_fix_math_dollor.py` 将 Unicode 数学符号包裹进 `$...$`
   - v2：`scripts/v2_fix_uni_to_latex.py` 将数学中的 Unicode 映射为 LaTeX 命令，并把 `![]()` 转为 `\includegraphics{}`
   - 输出：`qs_DB/<文档名>/<n>_<文档名>_<标签>.latex`
9) 基于 `worksheet.md` 再次 Pandoc 导出：`scripts/pandoc_export.bat`

说明：若 MinerU CLI 在你的机器上不可用，`src/pipeline.py` 会优雅降级并继续产出 Markdown/LaTeX，后续步骤仍可执行。

稳健执行策略（Step 6）
- Step 6 是核心步骤，但采用“稳健失败”策略：
  - 若 `python -m src.pipeline` 返回非 0，且 `outputs/worksheet.md` 仍然存在，则打印警告并继续后续步骤；
  - 若返回非 0 且 `outputs/worksheet.md` 不存在，则终止并报错。
- 原因：MinerU 依赖网络/模型加载，偶发不可用时尽量不阻断后续的本地处理链（规范化、修复链接、切分、v1→v2 输出 .latex 等）。

## 排版建议（LaTeX）

- 全局放大行内公式（避免压缩变扁）：
  - 在导言区添加：`\usepackage{amsmath}` 与 `\everymath{\displaystyle}`。
  - 作用：将所有行内数学以显示样式排版；可读性更好，但也会增大行高。

- 局部增大行距以获得更优雅的版面：
  - 需导言区：`\usepackage{setspace}`。
  - 在需要的段落外包裹：
    - `\begingroup\setstretch{2.4}`
    - 内容...
    - `\endgroup`
  - 说明：仅对包裹区域生效；全局行距可用 `\setstretch{<倍数>}` 或 `\linespread{<系数>}`。

- 与 Pandoc 配合：
  - 建议把上述导言内容写到一个头文件（例如 `pandoc-header.tex`），通过 Pandoc 增加 `-H pandoc-header.tex` 载入。
  - 若使用 `scripts/pandoc_export.bat`，可在脚本里为 Pandoc 命令追加 `-H` 参数，或直接在生成的 `outputs/worksheet_pandoc.tex` 手工加入上述宏包与命令。

## 常见问题（FAQ）

- Markdown 预览不显示图片？
  - 我们已将含空格/中文的 URL 用 `![](<...>)` 形式包裹，适配大多数预览器。
  - 仍不显示时，请从仓库根目录打开 `outputs/worksheet.md` 预览（部分预览器禁止 `..` 上级访问），或在设置中开启“信任工作区/允许本地文件访问”。

- 行内公式显得偏小？
  - 行内是 `\textstyle`，复杂分式/求和会显得“扁”。可在公式内显式加 `\displaystyle` 或使用 `\dfrac`；或将复杂公式改为独立一行 `$$...$$`。

- 仅需逐题 LaTeX 片段？
  - 直接使用 `qs_DB/*.latex`。这些是可嵌入的 LaTeX 片段（未包含导言）。

## 主要脚本概览

- `src/pipeline.py`：主流程（MinerU→切图→OCR→结构化→导出 md/tex + Pandoc）
- `scripts/run_mineru_auto.bat`：一键自动化批处理
- `scripts/normalize_md_question_titles.py`：将题号与题干并为一行
- `scripts/insert_linebreaks_before_solutions.py`：在“解析：”“解法<n>：”前插入换行
- `scripts/sync_qs_image_db_and_fix_links.py`：同步图片库并重写 `worksheet.md` 的图片链接（支持空格/中文）
- `scripts/split_md_to_parts.py`：按标签规则切分 `worksheet.md` 为 `qs_DB/md_part_*.md`
- `scripts/batch_v1_v2_to_latex.py`：对 `qs_DB/*.md` 批量运行 v1→v2，产出 `*.latex`（无中间落地）
- `scripts/pandoc_export.bat`：调用 Pandoc 生成 `outputs/worksheet_pandoc.tex`/PDF，并做若干 TeX 清理

历史/备用脚本已移至 `scripts/legacy/`，保持主目录清爽。

## 依赖管理

- 主要依赖列于 `requirements.txt`（包含 `mineru==2.5.4`、PyTorch、PaddleOCR 等）。
- `scripts/setup_env.bat` 会创建并激活 `venv310`，安装依赖，并按需补装常见包。

## 手动命令速查

- 手动运行主流程（使用 venv）：
  - `venv310\Scripts\python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru`

- 仅修复/切分/转换：
  - `venv310\Scripts\python -m scripts.normalize_md_question_titles`
  - `venv310\Scripts\python -m scripts.insert_linebreaks_before_solutions`
  - `venv310\Scripts\python -m scripts.sync_qs_image_db_and_fix_links`
  - `venv310\Scripts\python -m scripts.split_md_to_parts`
  - `venv310\Scripts\python -m scripts.batch_v1_v2_to_latex`

欢迎根据你的教材/习题风格调整切分正则与清理规则。




## 预处理与命名规范

- 建议先运行：env310\\Scripts\\python -m scripts.rename_images_whitespace
  - 将 images/ 下文件与目录名中的空格统一替换为 _
  - 可避免路径转义、Markdown 链接与 Pandoc 渲染异常
  - 自动批处理脚本已在 Step 5.5 执行相同步骤

