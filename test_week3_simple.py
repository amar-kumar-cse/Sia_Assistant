#!/usr/bin/env python3
"""Week 3 Validation Tests - Simple version without emoji"""

import sys
import pathlib
import inspect

sys.path.insert(0, str(pathlib.Path(__file__).parent))

def test_requirements_pinned():
    print("\nTEST #1: REQUIREMENTS VERSIONS PINNED")
    req_file = pathlib.Path(__file__).parent / "requirements.txt"
    content = req_file.read_text(encoding="utf-8", errors="ignore")
    unpinned = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            if "==" not in line and not any(c in line for c in [">=", "<=", ">", "<", "~="]):
                unpinned.append(line)
    if unpinned:
        print(f"FAILED: Unpinned packages: {unpinned}")
        return False
    print("PASS: All requirements pinned")
    return True

def test_hardcoded_paths():
    print("\nTEST #2: HARDCODED PATHS REMOVED")
    from engine import memory
    source = inspect.getsource(memory)
    if "C:\\Users\\yadav" in source or "/Users/yadav" in source:
        print("FAILED: Found hardcoded paths")
        return False
    if "_get_default_resume_path" not in source:
        print("FAILED: No dynamic path function")
        return False
    print("PASS: Paths are dynamic")
    return True

def test_logger_cleanup():
    print("\nTEST #3: LOGGER CLEANUP FUNCTION")
    from engine import logger
    if not hasattr(logger, 'cleanup_logger'):
        print("FAILED: cleanup_logger not found")
        return False
    source = inspect.getsource(logger.cleanup_logger)
    if "handler.close()" not in source:
        print("FAILED: No handler.close() in cleanup")
        return False
    print("PASS: Logger cleanup exists")
    return True

def test_docstrings():
    print("\nTEST #4: DOCSTRINGS ADDED")
    from engine import brain
    doc = inspect.getdoc(brain.think)
    if not doc or len(doc) < 50:
        print("FAILED: brain.think missing comprehensive docstring")
        return False
    doc = inspect.getdoc(brain.think_streaming)
    if not doc or len(doc) < 50:
        print("FAILED: brain.think_streaming missing docstring")
        return False
    print("PASS: Comprehensive docstrings present")
    return True

def test_type_hints():
    print("\nTEST #5: TYPE HINTS ADDED")
    from engine import brain
    sig = inspect.signature(brain.think)
    if sig.return_annotation == inspect.Signature.empty:
        print("FAILED: brain.think missing return type")
        return False
    sig = inspect.signature(brain.think_streaming)
    if sig.return_annotation == inspect.Signature.empty:
        print("FAILED: brain.think_streaming missing return type")
        return False
    print("PASS: Type hints present")
    return True

def main():
    tests = [
        test_requirements_pinned,
        test_hardcoded_paths,
        test_logger_cleanup,
        test_docstrings,
        test_type_hints,
    ]
    
    print("="*60)
    print("WEEK 3 VALIDATION TEST SUITE")
    print("="*60)
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nALL WEEK 3 IMPROVEMENTS VALIDATED!")
        print("- Requirements pinned")
        print("- Hardcoded paths removed")
        print("- Logger cleanup added")
        print("- Docstrings added")
        print("- Type hints added")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
