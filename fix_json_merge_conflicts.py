"""
Fix merge conflict markers in JSON files
Removes Git merge conflict markers and keeps the newer version
"""
import json
import re
import os
import sys
import glob

def fix_merge_conflicts(file_path):
    """Remove merge conflict markers from a JSON file"""
    print(f'Fixing: {file_path}...', flush=True)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove all merge conflict markers
        # Pattern: <<<<<<< ... ======= ... >>>>>>>
        # We'll keep the first version (before =======) which has newer timestamps
        # Handle multi-line conflicts
        while '<<<<<<<' in content:
            # Find the conflict block
            start = content.find('<<<<<<<')
            middle = content.find('=======', start)
            end = content.find('>>>>>>>', middle)
            
            if start != -1 and middle != -1 and end != -1:
                # Find the end of the >>>>>>> line (including newline)
                end_line = end + len('>>>>>>>')
                if end_line < len(content) and content[end_line] == '\n':
                    end_line += 1
                elif end_line < len(content) and content[end_line] == '\r':
                    end_line += 1
                    if end_line < len(content) and content[end_line] == '\n':
                        end_line += 1
                
                # Extract the part before ======= (newer version)
                before_marker = content[start:middle]
                # Remove the marker line itself (<<<<<<< ...)
                before_marker = re.sub(r'^<<<<<<<[^\n\r]*[\r\n]+', '', before_marker)
                
                # Replace the entire conflict block with just the first part
                content = content[:start] + before_marker + content[end_line:]
            else:
                break
        
        # Try to parse the cleaned JSON
        try:
            data = json.loads(content)
            
            # Save the cleaned version
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f'  ✅ Fixed: {file_path}', flush=True)
            return True
        except json.JSONDecodeError as e:
            print(f'  ⚠️ Still has JSON errors after cleanup: {e}', flush=True)
            print(f'  Trying to extract just team_name and team_url...', flush=True)
            
            # If still broken, try to extract just the essential fields
            name_match = re.search(r'"team_name"\s*:\s*"([^"]+)"', content)
            url_match = re.search(r'"team_url"\s*:\s*"([^"]+)"', content)
            
            if name_match and url_match:
                # Create a minimal valid JSON
                minimal_data = {
                    "team_name": name_match.group(1),
                    "team_url": url_match.group(1),
                    "games": []
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(minimal_data, f, indent=2, ensure_ascii=False)
                print(f'  ✅ Created minimal valid JSON (games will be re-scraped)', flush=True)
                return True
            else:
                print(f'  ❌ Could not extract team info', flush=True)
                return False
                
    except Exception as e:
        print(f'  ❌ Error: {e}', flush=True)
        return False

if __name__ == '__main__':
    print('='*60)
    print('FIX JSON MERGE CONFLICTS')
    print('='*60)
    print()
    
    # Fix all *_prices.json files
    pattern = '*_prices.json'
    files = glob.glob(pattern)
    
    if not files:
        print('No *_prices.json files found.')
        sys.exit(0)
    
    print(f'Found {len(files)} file(s) to check...')
    print()
    
    fixed = 0
    for file_path in files:
        if fix_merge_conflicts(file_path):
            fixed += 1
        print()
    
    print('='*60)
    print(f'Fixed {fixed} out of {len(files)} file(s)')
    print('='*60)

