# 🚀 发布到PyPI指南

## 📋 发布前准备

### 1. 构建项目包
```bash
# 确保在dev分支（功能更完整）
git checkout dev

# 构建包
uv run python -m build

# 检查构建结果
ls -lh dist/
```

### 2. 验证包质量
```bash
# 检查包是否符合PyPI要求
uv run twine check dist/*
```

### 3. 配置PyPI认证

#### 方法1：使用API Token（推荐）
1. 登录 [PyPI](https://pypi.org/manage/account/token/)
2. 创建API Token（作用域选择"Entire account"）
3. 在终端输入：
```bash
uv run twine upload dist/*
# 输入用户名: __token__
# 输入密码: 你的API Token
```

#### 方法2：配置.pypirc文件
创建 `~/.pypirc` 文件：
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = 你的API_TOKEN

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = 你的测试API_TOKEN
```

## 🧪 测试发布（可选）

### 上传到测试PyPI
```bash
uv run twine upload --repository testpypi dist/*
```

测试包地址：https://test.pypi.org/project/stargazing-place-finder/

### 测试安装
```bash
# 从测试PyPI安装
pip install -i https://test.pypi.org/simple/ stargazing-place-finder

# 测试导入
python -c "from light_pollution.public_api import init_light_pollution_analyzer; print('✅ 安装成功')"
```

## 🌟 正式发布

### 上传到正式PyPI
```bash
uv run twine upload dist/*
```

正式包地址：https://pypi.org/project/stargazing-place-finder/

### 验证发布
```bash
# 等待几分钟后测试安装
pip install stargazing-place-finder

# 测试基本功能
python -c "
from light_pollution.public_api import init_light_pollution_analyzer
from stargazing_analyzer.public_api import init_stargazing_analyzer
print('✅ 包安装和功能正常')
"
```

## 📦 包内容说明

### 核心模块
- `light_pollution` - 光污染分析模块
- `stargazing_analyzer` - 观星地点分析模块  
- `location_finder` - 位置查找模块
- `mountain_peak` - 山峰查找模块
- `road_connectivity` - 道路连通性检测模块
- `utils` - 工具模块

### 示例文件
- `examples/python_public_api_demo.py` - API使用演示
- `examples/batch_elevation_query_demo.py` - 批量高程查询
- 其他多个示例文件...

### 数据文件
- `light_pollution/resources/world_atlas/` - 光污染世界地图数据
- 包含564个JPG文件的光污染亮度图

## ⚠️ 注意事项

1. **版本号管理**：每次发布前更新 `pyproject.toml` 中的版本号
2. **文件大小**：包大小约25MB，主要因为包含光污染地图数据
3. **依赖兼容性**：支持Python 3.9+，依赖包版本已优化
4. **网络问题**：如果遇到上传问题，可以重试或使用VPN

## 🔧 问题排查

### 上传失败
- 检查网络连接
- 验证API Token有效性
- 确认包文件未损坏

### 安装失败  
- 检查Python版本是否符合要求
- 确认pip版本是否最新
- 查看依赖包是否安装成功

### 导入失败
- 检查模块路径是否正确
- 确认数据文件是否存在
- 查看错误信息定位问题

## 📞 获取帮助

如有问题，可以：
1. 检查PyPI项目页面
2. 查看GitHub Issues
3. 重新构建和上传包

---

**祝发布顺利！🎉**