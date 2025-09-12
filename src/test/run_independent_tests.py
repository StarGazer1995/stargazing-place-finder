#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行src目录下可独立执行的测试文件

这个脚本专门运行那些包含main函数或run_tests函数的测试文件，
这些文件通常可以独立运行而不依赖复杂的模块导入。
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 可独立运行的测试文件列表
INDEPENDENT_TEST_FILES = [
    "src/cache/test/test_cache_functionality.py",
    "src/cache/test/test_cache_integration.py", 
    "src/mountain_peak/test/test_mountain_peak_finder.py",
    "src/road_connectivity/test/test_road_connectivity.py",
    "src/stargazing_analyzer/test/test_stargazing_analyzer.py",
    "src/stargazing_analyzer/test/test_updated_analyze_area.py",
    "src/light_pollution/test/test_light_pollution_sorting.py",
    "src/location_finder/test/test_viewpoint_finder.py",
    "src/utils/test/test_unified_dataclasses.py"
]

def run_independent_test(test_file_path):
    """
    运行单个独立测试文件
    
    Args:
        test_file_path (str): 测试文件相对路径
        
    Returns:
        tuple: (是否成功, 输出信息)
    """
    test_file = Path(test_file_path)
    
    if not test_file.exists():
        print(f"⚠️ Test file not found: {test_file}")
        return False, f"File not found: {test_file}"
    
    print(f"\n{'='*60}")
    print(f"Running independent test: {test_file}")
    print(f"{'='*60}")
    
    try:
        # 从项目根目录运行测试，设置PYTHONPATH
        env = os.environ.copy()
        src_path = str(Path.cwd() / "src")
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = src_path
            
        # 运行测试文件
        result = subprocess.run(
            [sys.executable, "-u", str(test_file)],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            env=env
        )
        
        # 打印输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        success = result.returncode == 0
        if success:
            print(f"✅ Independent test {test_file.name} PASSED")
        else:
            print(f"❌ Independent test {test_file.name} FAILED (return code: {result.returncode})")
            
        return success, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Independent test {test_file.name} TIMEOUT (exceeded 10 minutes)")
        return False, "Test timeout"
    except Exception as e:
        print(f"💥 Independent test {test_file.name} ERROR: {e}")
        return False, str(e)

def main():
    """
    主函数 - 运行所有可独立执行的测试
    """
    print("🚀 Starting independent test suite")
    print(f"Working directory: {Path.cwd()}")
    print(f"Python version: {sys.version}")
    
    # 检查哪些测试文件存在
    existing_tests = []
    missing_tests = []
    
    for test_file in INDEPENDENT_TEST_FILES:
        if Path(test_file).exists():
            existing_tests.append(test_file)
        else:
            missing_tests.append(test_file)
    
    if missing_tests:
        print(f"\n⚠️ Missing test files:")
        for test in missing_tests:
            print(f"  - {test}")
    
    if not existing_tests:
        print("❌ No independent test files found!")
        return False
        
    print(f"\n📋 Found {len(existing_tests)} independent test files:")
    for i, test_file in enumerate(existing_tests, 1):
        print(f"  {i}. {test_file}")
    
    # 运行所有独立测试
    passed = 0
    failed = 0
    failed_tests = []
    
    start_time = time.time()
    
    for test_file in existing_tests:
        success, output = run_independent_test(test_file)
        
        if success:
            passed += 1
        else:
            failed += 1
            failed_tests.append((test_file, output))
            
        # 在测试之间添加短暂延迟
        time.sleep(2)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 输出总结
    print(f"\n{'='*80}")
    print(f"📊 INDEPENDENT TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {len(existing_tests)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success rate: {passed/len(existing_tests)*100:.1f}%")
    print(f"Total duration: {duration:.2f} seconds")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test_file, output in failed_tests:
            print(f"  - {test_file}")
    
    if failed == 0:
        print(f"\n🎉 All independent tests passed! The core modules are working correctly.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)