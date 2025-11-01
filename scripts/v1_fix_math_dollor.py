import re
import sys

def wrap_unicode_math(content):
    """
    Splits the text by '$', '\(', and '\)' delimiters and processes the parts.
    Text outside of all math blocks will be scanned for unicode math symbols,
    which are then wrapped in '$'.
    """
    
    # 目标 Unicode 符号列表
    TARGET_SYMBOLS = r'∠°△∥⊥Ωαβγδ√θπ≌ΣΩΔ±×÷⋅≠≤≥≈≡√∞→←↔⇒⇐'
    
    # 合法的数学表达式字符
    VALID_MATH_CHARS = r'a-zA-Z0-9\s=+\-.,()\[\]{}' + TARGET_SYMBOLS

    # 查找由合法字符组成，且至少包含一个目标符号的字符串
    wrapper_regex = re.compile(
        f'([{VALID_MATH_CHARS}]*[{TARGET_SYMBOLS}][{VALID_MATH_CHARS}]*)'
    )
    
    # 关键改动：现在按三种分隔符进行分割
    # 我们需要转义 \ (\\) 和 ( \( )
    parts = re.split(r'(\$|\\\s*\(|\\\s*\))', content)
    
    new_content_parts = []
    in_math_dollar = False  # 是否在 $...$ 内部
    in_math_paren = False   # 是否在 \(...\) 内部
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        # 状态机逻辑
        if part == '$':
            in_math_dollar = not in_math_dollar
            new_content_parts.append(part)
        elif re.match(r'\\\s*\(', part): # 匹配 \(
            in_math_paren = True
            new_content_parts.append(part)
        elif re.match(r'\\\s*\)', part): # 匹配 \)
            in_math_paren = False
            new_content_parts.append(part)
        else:
            # 仅在所有数学模式之外才处理
            if not in_math_dollar and not in_math_paren:
                # 在数学模式之外：应用正则表达式进行替换
                processed_part = re.sub(wrapper_regex, r'$\1$', part)
                new_content_parts.append(processed_part)
            else:
                # 在数学模式之内：不做任何改动
                new_content_parts.append(part)
        i += 1
            
    return "".join(new_content_parts)

def main():
    """
    Main function to run the script from the command line.
    """
    if len(sys.argv) != 3:
        print("Usage: python fix_math_v3.py <input_file.md> <output_file.md>")
        sys.exit(1)
        
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"--- Reading file: {input_filename}")
        
        fixed_content = wrap_unicode_math(content)
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
            
        print(f"--- Successfully processed and saved to: {output_filename}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()