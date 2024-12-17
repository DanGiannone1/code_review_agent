import os
import glob
from fnmatch import fnmatch

# Base directory
base_dir = 'D:/projects/code_review_agent/'

# Patterns to match
patterns = [
    '**/*.md',
    '**/*.py',
    '**/*.tsx',
    '**/*.ts',
    '**/*.json',
    '**/*.js',
    '**/*.html',
    '**/*.css',
    '*.gitignore',
    'example.env',  # Include example environment files
]

# Files or directories to exclude
exclude_patterns = [
    '**/package-lock.json',  # Exclude package-lock.json
    '**/__pycache__/**',
    '**/node_modules/**',
    '**/.git/**',
    '**/.vscode/**',
    '**/dist/**',
    '**/*.log',
    '**/*.pyc',
    'LICENSE',
    'scripts/getcodebase.py',
    '**/*.pyo',
    '**/.env',          # Exclude actual .env files
    '**/*.env',         # Exclude any other env files with sensitive data
    '**/env/**',
    '**/venv/**',
    '**/venv*',         # Exclude virtual environments
    '**/*.egg-info/**',
    '**/build/**',
]

# Collect files matching patterns
files = []
for pattern in patterns:
    files.extend(glob.glob(os.path.join(base_dir, pattern), recursive=True))

# Remove duplicates
files = list(set(files))

# Filter out excluded files
def is_excluded(file_path):
    for pattern in exclude_patterns:
        if fnmatch(file_path, pattern):
            return True
    return False

files = [f for f in files if not is_excluded(f)]

# Generate output file name based on the last part of base_dir
output_filename = f"{os.path.basename(base_dir.rstrip('/\\'))}.txt"
output_file = os.path.join('D:/temp/tmp_codebase/', output_filename)

# Open the output file in write mode
with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
    # Iterate over all collected files
    for filepath in files:
        relative_path = os.path.relpath(filepath, base_dir)
        # Open the file in read mode
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as code_file:
            # Write the filename to the output file
            f.write(f"<File: {relative_path}>\n")
            # Write the code from the file to the output file
            f.write(code_file.read())
            # Add a separator between files
            f.write('\n' + '-'*80 + '\n')