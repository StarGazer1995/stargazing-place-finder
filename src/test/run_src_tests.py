#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行src目录下的所有测试脚本

这个脚本会自动发现并运行src目录中的所有测试文件。
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def find_src_test_files():
    """
    查找src目录中的所有测试文件
    
    Returns:
        list: 测试文件路径列表
    """
    test_files = []
    # 修正路径：从当前文件位置向上两级到达项目根目录，然后进入src目录
    src_dir = Path(__file__).parent.parent.parent / "src"
    
    # 递归查找所有测试文件
    for test_file in src_dir.rglob("test_*.py"):
        if test_file.is_file():
            test_files.append(test_file)
    
    # 排序
    test_files = sorted(test_files)
    return test_files

def run_test_file(test_file):
    """
    运行单个测试文件
    
    Args:
        test_file (Path): 测试文件路径
        
    Returns:
        tuple: (是否成功, 输出信息)
    """
    print(f"\n{'='*60}")
    print(f"Running test: {test_file.relative_to(Path.cwd())}")
    print(f"{'='*60}")
    
    try:
        # 设置环境变量，将src目录添加到PYTHONPATH
        env = os.environ.copy()
        src_path = str(Path.cwd() / "src")
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = src_path
        env['FAST_TESTS'] = '1'
            
        # 使用python -u来确保输出不被缓冲，-v开启详细模式
        result = subprocess.run(
            [sys.executable, "-u", str(test_file)],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            env=env
        )
        
        # 打印输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        success = result.returncode == 0
        if success:
            print(f"✅ Test {test_file.name} PASSED")
        else:
            print(f"❌ Test {test_file.name} FAILED (return code: {result.returncode})")
            
        return success, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Test {test_file.name} TIMEOUT (exceeded 5 minutes)")
        return False, "Test timeout"
    except Exception as e:
        print(f"💥 Test {test_file.name} ERROR: {e}")
        return False, str(e)

def main():
    """
    主函数 - 运行src目录下的所有测试
    """
    print("🚀 Starting src directory test suite")
    print(f"Working directory: {Path.cwd()}")
    print(f"Python version: {sys.version}")
    
    # 查找所有测试文件
    test_files = find_src_test_files()
    
    if not test_files:
        print("❌ No test files found in src directory!")
        return False
        
    print(f"\n📋 Found {len(test_files)} test files in src directory:")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i}. {test_file.relative_to(Path.cwd())}")
    
    # 运行所有测试
    passed = 0
    failed = 0
    failed_tests = []
    
    start_time = time.time()
    
    for test_file in test_files:
        success, output = run_test_file(test_file)
        
        if success:
            passed += 1
        else:
            failed += 1
            failed_tests.append((test_file, output))
            
        # 在测试之间添加短暂延迟，避免资源冲突
        time.sleep(1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 输出总结
    print(f"\n{'='*80}")
    print(f"📊 SRC DIRECTORY TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {len(test_files)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success rate: {passed/len(test_files)*100:.1f}%")
    print(f"Total duration: {duration:.2f} seconds")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test_file, output in failed_tests:
            print(f"  - {test_file.relative_to(Path.cwd())}")
    
    if failed == 0:
        print(f"\n🎉 All src tests passed! The project modules are working correctly.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)