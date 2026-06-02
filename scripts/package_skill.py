#!/usr/bin/env python3
import os
import zipfile
import datetime
import shutil
import re
import sys

SENSITIVE_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}', 'API Key'),
    (r'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}', 'Secret Key'),
    (r'(?i)(access[_-]?token|accesstoken)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}', 'Access Token'),
    (r'(?i)(auth[_-]?token|authtoken)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}', 'Auth Token'),
    (r'(?i)(bearer)\s+[a-zA-Z0-9_\-\.]{20,}', 'Bearer Token'),
    (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API Key'),
    (r'sk-ant-[a-zA-Z0-9\-]{20,}', 'Anthropic API Key'),
    (r'(?i)(password|passwd)\s*[:=]\s*["\']?[^\s"\']{8,}', 'Password'),
    (r'[a-f0-9]{32,}', 'Possible Hash/Secret'),
]

SENSITIVE_FILES = [
    '.env', '.env.local', '.env.production', '.env.development',
    'secrets.json', 'credentials.json', 'config.secrets.json',
    'config.txt',  # Exclude actual config (may contain API keys)
    'private.key', 'id_rsa', 'id_ed25519',
]

def check_file_for_secrets(file_path):
    """Check a file for potential secret leaks."""
    warnings = []
    
    filename = os.path.basename(file_path)
    if filename in SENSITIVE_FILES:
        warnings.append(f"  ⚠️  Sensitive file detected: {filename}")
        return warnings
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern, secret_type in SENSITIVE_PATTERNS:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    warnings.append(f"  ⚠️  {secret_type} detected at line {line_num}")
    except Exception as e:
        pass
    
    return warnings

def package_skill():
    """
    Packages the 'skills/asr' directory into a zip file with date-based versioning.
    The output zip is saved to the 'dist' directory.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(project_root, "skills", "asr")
    dist_dir = os.path.join(project_root, "dist")
    
    today = datetime.datetime.now().strftime("%Y%m%d")
    zip_filename = f"asr-skill-{today}.zip"
    zip_filepath = os.path.join(dist_dir, zip_filename)

    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
        print(f"Created directory: {dist_dir}")

    ignore_patterns = {
        "__pycache__", "*.pyc", ".DS_Store", ".git", ".gitignore",
        ".idea", ".vscode", ".env", ".env.local", ".env.production",
        ".env.development", "secrets.json", "credentials.json",
        "config.secrets.json", "config.txt", "private.key", "*.pem"
    }

    print(f"🔍 Checking for potential secret leaks...")
    all_warnings = []
    files_to_package = []
    
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in ignore_patterns and not d.startswith('.')]
        
        for file in files:
            if file in ignore_patterns or file.endswith('.pyc') or file == ".DS_Store":
                continue
            
            file_path = os.path.join(root, file)
            warnings = check_file_for_secrets(file_path)
            if warnings:
                rel_path = os.path.relpath(file_path, source_dir)
                all_warnings.append(f"\n📄 {rel_path}:")
                all_warnings.extend(warnings)
            
            # ZIP format requires forward slashes; os.path.relpath returns
            # backslashes on Windows, so normalize with os.sep replacement
            zip_arcname = os.path.relpath(file_path, os.path.dirname(source_dir)).replace(os.sep, "/")
            files_to_package.append((file_path, zip_arcname))
    
    if all_warnings:
        print("\n" + "="*60)
        print("⚠️  SECURITY WARNING: Potential secrets detected!")
        print("="*60)
        for warning in all_warnings:
            print(warning)
        print("="*60)
        
        response = input("\n⚠️  Continue packaging? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Packaging cancelled.")
            sys.exit(1)
        print()
    
    print(f"\n📦 Packaging {source_dir} into {zip_filepath}...")

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, rel_path in files_to_package:
                print(f"  ✓ Adding: {rel_path}")
                zipf.write(file_path, rel_path)
        
        file_size = os.path.getsize(zip_filepath)
        size_kb = file_size / 1024
        print(f"\n✅ Success! Package created at:")
        print(f"   {zip_filepath}")
        print(f"   Size: {size_kb:.2f} KB")
        
    except Exception as e:
        print(f"\n❌ Error: Failed to create package. {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    package_skill()
