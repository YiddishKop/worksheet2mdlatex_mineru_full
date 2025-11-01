import sys
import re

# 1. Unicode 到 LaTeX 的替换字典
REPLACEMENT_DICT = {
    # 几何与角度
    '∠': r'\angle',
    '°': r'^{\circ}',
    '△': r'\triangle',
    '△': r'\triangle',
    '≌': r'\cong',
    '∥': r'\parallel',
    '⊥': r'\perp',
    '≌': r'\cong', # 增加“全等于”
    # 希腊字母
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta', 'θ': r'\theta',
    'π': r'\pi', 'Σ': r'\Sigma', 'Ω': r'\Omega',
    # 运算符
    '±': r'\pm', '×': r'\times', '÷': r'\div', '⋅': r'\cdot',
    '≠': r'\neq', '≤': r'\leq', '≥': r'\geq', '≈': r'\approx', '≡': r'\equiv',
    # 箭头
    '→': r'\rightarrow', '←': r'\leftarrow', '↔': r'\leftrightarrow',
    '⇒': r'\Rightarrow', '⇐': r'\Leftarrow',
    # 其他
    '√': r'\sqrt', '∞': r'\infty',
}

def clean_math_content(content):
    """
    对提取出的数学内容字符串执行所有清理操作
    """
    
    # 1. 执行 Unicode 替换
    for unicode_char, latex_command in REPLACEMENT_DICT.items():
        content = content.replace(unicode_char, latex_command)
    
    # 2. 修复常见的 OCR/转换错误，例如 "9 0" -> "90"
    # 匹配一个数字，后面跟着一个或多个空格，再跟着一个数字
    content = re.sub(r'(\d)\s+(\d)', r'\1\2', content)
    
    # 3. (可选) 移除 \boldsymbol 之类的 Pandoc 特有命令
    content = content.replace(r'\boldsymbol { E }', 'E') # 简化

    # --- 这是您要求的修改 ---
    # 4. 为特定命令后的多个连续字母添加大括号
    #    例如： \triangleABC -> \triangle{ABC}
    #    但 \angleA 不会变成 \angle{A} (因为它只匹配2个或更多字母)
    
    # 匹配 (\triangle, \angle, \parallel, \perp) 
    # 后面必须跟着 ([a-zA-Z]{2,}) 两个或更多连续的字母
    brace_regex = re.compile(r'(\\triangle|\\angle|\\parallel|\\perp)([a-zA-Z]{1,})')
    content = brace_regex.sub(r'\1{\2}', content)
    
    return content


def convert_images_to_latex(content):
    """
    使用正则表达式查找 Markdown 图像语法 ![](path)
    并将其替换为 \includegraphics{path}
    """
    
    # 正则表达式：
    # \!\[        # 匹配 `![`
    # [^\]]* # 匹配方括号内的任何 alt-text (我们不关心它)
    # \]          # 匹配 `]`
    # \(          # 匹配 `(`
    # (.*?)       # 捕获组 1: 路径 (非贪婪)
    # \)          # 匹配 `)`
    
    # 我们将保留图像的原始宽高比
    image_regex = re.compile(r'!\[[^\]]*\]\((.*?)\)')
    
    # 替换：使用 \includegraphics[keepaspectratio]{...}
    # \1 代表捕获到的路径
    # 我们需要用 \\ 来转义 Python 字符串中的 \
    replacement = r'\\includegraphics[keepaspectratio]{\1}'
    
    return image_regex.sub(replacement, content)


def replacer_callback(match):
    """
    这个回调函数会被 re.sub() 调用
    它检查是哪种定界符匹配了，提取内容，清理它，
    然后统一用 $...$ 格式返回
    """
    
    # 检查是 $...$ 匹配 (group 2) 还是 \(...\) 匹配 (group 4)
    content = None
    if match.group(2) is not None:
        content = match.group(2)
    elif match.group(4) is not None:
        content = match.group(4)
    
    if content is not None:
        cleaned_content = clean_math_content(content)
        # 统一返回 $...$ 格式
        return f'${cleaned_content}$'
    
    # 如果匹配到但没有捕获到内容（理论上不应该发生），返回原文
    return match.group(0)

def main():
    if len(sys.argv) != 3:
        print("Usage: python process_markdown.py <input.md> <output.md>")
        sys.exit(1)
        
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"--- Reading file: {input_filename}")
        
        # 这个正则表达式同时查找 $...$ 和 \(...\)
        # 捕获组 2: $...$ 的内容
        # 捕获组 4: \(...\) 的内容
        math_regex = re.compile(
            r'(\$(.*?)\$)|' +  # 匹配 $...$
            r'(\\\(\s*(.*?)\s*\\\))' # 匹配 \(...\)
        )
        
        # 使用 re.sub 和回调函数一次性替换所有
        final_content = math_regex.sub(replacer_callback, content)
        final_content = convert_images_to_latex(final_content)
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print(f"--- Successfully cleaned and saved to: {output_filename}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()