"""
Windows 7 Compatibility Test
Tests if all required packages and Python features work with Python 3.7.9
"""
import sys

def test_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor == 7:
        print("✅ Python 3.7.x - Compatible with Windows 7")
        return True
    elif version.major == 3 and version.minor < 7:
        print("⚠️  Python 3.6 or earlier - May have compatibility issues")
        return True
    elif version.major == 3 and version.minor >= 8:
        print("⚠️  Python 3.8+ - May not work on Windows 7")
        print("   Windows 7 officially supports up to Python 3.7.9")
        return False
    else:
        print("❌ Unsupported Python version")
        return False

def test_imports():
    """Test if all required packages can be imported"""
    packages = {
        'undetected_chromedriver': 'undetected-chromedriver',
        'selenium': 'selenium',
        'requests': 'requests',
        'json': 'json (built-in)',
        'os': 'os (built-in)',
        'sys': 'sys (built-in)',
        'subprocess': 'subprocess (built-in)',
        'threading': 'threading (built-in)',
        'datetime': 'datetime (built-in)',
        'io': 'io (built-in)',
        'time': 'time (built-in)',
        're': 're (built-in)',
        'shutil': 'shutil (built-in)',
    }
    
    print("\nTesting package imports...")
    failed = []
    
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError as e:
            print(f"❌ {name} - {str(e)}")
            failed.append(name)
    
    return len(failed) == 0

def test_encoding():
    """Test Windows encoding fix"""
    print("\nTesting Windows encoding...")
    try:
        import io
        if sys.platform == 'win32':
            # Test the encoding fix
            test_output = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            print("✅ Windows encoding fix works")
            return True
        else:
            print("ℹ️  Not Windows - encoding fix not needed")
            return True
    except Exception as e:
        print(f"❌ Encoding test failed: {e}")
        return False

def test_script_files():
    """Check if all required script files exist"""
    import os
    print("\nChecking script files...")
    files = [
        'auto_scraper.py',
        'scraper_viagogo.py',
        'scraper_ftn.py',
    ]
    
    missing = []
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - NOT FOUND")
            missing.append(file)
    
    return len(missing) == 0

def main():
    print("=" * 60)
    print("Windows 7 Compatibility Test")
    print("=" * 60)
    
    results = []
    
    # Test Python version
    results.append(("Python Version", test_python_version()))
    
    # Test imports
    results.append(("Package Imports", test_imports()))
    
    # Test encoding
    results.append(("Windows Encoding", test_encoding()))
    
    # Test script files
    results.append(("Script Files", test_script_files()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ All tests passed! Ready to run on Windows 7.")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

