#!/usr/bin/env python3
"""
发布脚本：用于将stargazing-place-finder包发布到PyPI

使用方法:
    python publish_to_pypi.py [test|prod]

参数:
    test - 发布到测试PyPI (test.pypi.org)
    prod - 发布到正式PyPI (pypi.org)
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """运行shell命令并检查返回码"""
    print(f"\n🔄 {description}")
    print(f"命令: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 失败: {result.stderr}")
        return False
    
    print(f"✅ 成功")
    if result.stdout:
        print(result.stdout)
    return True

def main():
    # 检查参数
    if len(sys.argv) != 2 or sys.argv[1] not in ['test', 'prod']:
        print("用法: python publish_to_pypi.py [test|prod]")
        print("  test - 发布到测试PyPI")
        print("  prod - 发布到正式PyPI")
        sys.exit(1)
    
    target = sys.argv[1]
    
    print("🚀 开始发布流程...")
    
    # 1. 检查包是否存在
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist目录不存在，请先运行构建命令")
        sys.exit(1)
    
    wheel_files = list(dist_dir.glob("*.whl"))
    tar_files = list(dist_dir.glob("*.tar.gz"))
    
    if not wheel_files or not tar_files:
        print("❌ 未找到构建的包文件，请先运行: uv run python -m build")
        sys.exit(1)
    
    print(f"📦 找到包文件:")
    for f in wheel_files + tar_files:
        print(f"  - {f.name}")
    
    # 2. 检查包质量
    if not run_command("uv run twine check dist/*", "检查包质量"):
        sys.exit(1)
    
    # 3. 上传到PyPI
    if target == 'test':
        print("\n🧪 发布到测试PyPI (test.pypi.org)")
        print("⚠️  需要PyPI测试服务器API Token")
        cmd = "uv run twine upload --repository testpypi dist/*"
    else:
        print("\n🌟 发布到正式PyPI (pypi.org)")
        print("⚠️  需要PyPI正式服务器API Token")
        cmd = "uv run twine upload dist/*"
    
    print("\n📋 发布前检查清单:")
    print("✅ 包文件已构建")
    print("✅ 包质量检查通过")
    print("⚠️  确保你已配置PyPI API Token")
    print("⚠️  确保版本号正确 (当前: 0.1.0)")
    
    # 4. 执行上传
    print(f"\n执行命令: {cmd}")
    response = input(f"确定要发布到{'测试' if target == 'test' else '正式'}PyPI吗? [y/N]: ")
    
    if response.lower() == 'y':
        if run_command(cmd, f"上传到{'测试' if target == 'test' else '正式'}PyPI"):
            print(f"\n🎉 成功发布到{'测试' if target == 'test' else '正式'}PyPI!")
            if target == 'test':
                print("📍 测试包地址: https://test.pypi.org/project/stargazing-place-finder/")
            else:
                print("📍 正式包地址: https://pypi.org/project/stargazing-place-finder/")
        else:
            print("\n❌ 发布失败，请检查错误信息")
            sys.exit(1)
    else:
        print("\n❌ 发布已取消")

if __name__ == "__main__":
    main()