import re
import sys

def wrap_unicode_math(content):
    """
    Splits the text by '$' delimiters and processes the parts.
    Text outside of '$...$' blocks will be scanned for unicode math symbols,
    which are then wrapped in '$'.
    """
    
    # This regex is designed to find a contiguous block of text that
    # "looks like" a math expression and contains at least one of
    # the target unicode symbols.
    #
    # It finds:
    # (
    #   [a-zA-Z0-9\s=+\-.]* # Optional valid math chars (letters, nums, space, =, +, -, .) BEFORE...
    #   [∠°△]                 # ...at least one of our target symbols...
    #   [a-zA-Z0-9\s=+\-.°∠△]* # ...followed by any number of valid math/target chars.
    # )
    # This ensures it wraps "∠FGC+∠FBG=90°" as one block, not as "$∠$FGC+$∠$FBG=90$°$".
    
    # 请注意：我特意没有包含中文标点符号（如 ，。？！）
    wrapper_regex = re.compile(
        r'([a-zA-Z0-9\s=+\-.]*[∠°△]+[a-zA-Z0-9\s=+\-.°∠△]*)'
    )
    
    # We split the text by the '$' delimiter.
    # The ( ) around the '$' keep it in the list, which is crucial.
    parts = re.split(r'(\$)', content)
    
    new_content_parts = []
    in_math_mode = False
    
    for part in parts:
        if part == '$':
            # Flip the state
            in_math_mode = not in_math_mode
            new_content_parts.append(part)
        elif not in_math_mode:
            # We are OUTSIDE math mode, so we apply the wrapper
            # We use re.sub() to replace all occurrences found
            processed_part = re.sub(wrapper_regex, r'$\1$', part)
            new_content_parts.append(processed_part)
        else:
            # We are INSIDE math mode, so we leave this part alone
            new_content_parts.append(part)
            
    return "".join(new_content_parts)

def main():
    """
    Main function to run the script from the command line.
    """
    if len(sys.argv) != 3:
        print("Usage: python fix_math.py <input_file.md> <output_file.md>")
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