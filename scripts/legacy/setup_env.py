import os, sys, subprocess, importlib

REQUIRED = [
    "torch", "torchvision", "torchaudio",
    "paddleocr", "paddlenlp", "paddlepaddle",
    "mineru", "doclayout-yolo", "ultralytics",
    "pix2tex[gui]", "onnx", "omegaconf",
    "ftfy", "sentencepiece", "shapely", "pyclipper",
    "pypdfium2", "transformers", "jinja2", "packaging"
]

print("======================================================")
print("[ worksheet2mdlatex ] MinerU + pix2tex 环境自动安装器")
print("======================================================")

def pip_install(pkg):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装 {pkg} 失败: {e}")

for pkg in REQUIRED:
    module_name = pkg.split("[")[0].split("==")[0]
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} 已安装")
    except ImportError:
        print(f"⚙️ 正在安装 {pkg} ...")
        pip_install(pkg)

print("------------------------------------------------------")
print("✅ 所有依赖已安装完成。")
print("你现在可以运行：")
print("    scripts/run_mineru_auto.bat  (Windows)")
print("或  python scripts/run_mineru_auto.py  (跨平台)")
print("------------------------------------------------------")
