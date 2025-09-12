#!/bin/bash

# 观星地点查找器 - 快速启动脚本
# Stargazing Place Finder - Quick Start Script

echo "🌟 启动观星地点查找器..."
echo "🌟 Starting Stargazing Place Finder..."

# 检查是否安装了uv
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: 未找到 uv 包管理器"
    echo "❌ Error: uv package manager not found"
    echo "请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 检查项目依赖
echo "📦 检查项目依赖..."
echo "📦 Checking project dependencies..."
uv sync

# 生成地图文件
echo "🗺️  生成地图文件..."
echo "🗺️  Generating map files..."
uv run python src/utils/styled_map_generator.py

# 复制资源文件
echo "📁 复制资源文件..."
echo "📁 Copying resource files..."
cp -r src/source/assets/* styled_map_output/assets/

# 启动光污染API服务（后台运行）
echo "🚀 启动光污染API服务..."
echo "🚀 Starting Light Pollution API service..."
uv run python src/light_pollution/light_pollution_api.py &
API_PID=$!

# 等待API服务启动
sleep 2

# 启动HTTP服务器
echo "🌐 启动HTTP服务器..."
echo "🌐 Starting HTTP server..."
echo "📍 地图访问地址: http://localhost:8000/styled_map_output/index.html"
echo "📍 Map URL: http://localhost:8000/styled_map_output/index.html"
echo ""
echo "💡 使用 Ctrl+C 停止所有服务"
echo "💡 Press Ctrl+C to stop all services"
echo ""

# 启动HTTP服务器（前台运行）
uv run python -m http.server 8000 &
HTTP_PID=$!

# 等待用户中断
trap 'echo "\n🛑 正在停止服务..."; kill $API_PID $HTTP_PID 2>/dev/null; echo "✅ 所有服务已停止"; exit 0' INT

# 保持脚本运行
wait