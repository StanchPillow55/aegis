import os
import ast
import glob
import sys

def check_file_sanity():
    patterns = ["backend/**/*.py", "importer/**/*.py", "tests/**/*.py", "scripts/**/*.py", "*.txt", "Makefile", "*.yaml", "*.md", "docs/**/*.md"]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))

    hidden_chars = ["\u202A", "\u202B", "\u202C", "\u202D", "\u202E", "\uFEFF"]
    
    has_error = False

    for file_path in files:
        if not os.path.isfile(file_path):
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Check for hidden characters
        for char in hidden_chars:
            if char in content:
                print(f"ERROR: Hidden character {repr(char)} found in {file_path}")
                has_error = True

        # Check for suspiciously long single lines
        lines = content.splitlines()
        if len(lines) == 1 and len(content) > 500:
            print(f"ERROR: File suspiciously one-line long (>500 chars) in {file_path}")
            has_error = True

        # Check for python AST parsing
        if file_path.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as e:
                print(f"ERROR: SyntaxError parsing {file_path}: {e}")
                has_error = True

    if has_error:
        sys.exit(1)
    else:
        print("File sanity check passed.")

if __name__ == "__main__":
    check_file_sanity()
