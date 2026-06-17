#!/bin/bash

# 观星地点查找器 - 快速启动脚本
# Stargazing Place Finder - Quick Start Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
WEB_PORT="${WEB_PORT:-8000}"
API_PORT="${API_PORT:-5001}"
WEB_ENTRY_PATH="src/source/template.html"
WEB_URL="http://localhost:${WEB_PORT}/${WEB_ENTRY_PATH}"
API_URL="http://localhost:${API_PORT}"
API_PID=""
HTTP_PID=""

# 关闭指定端口上的遗留进程，避免重复启动失败。
cleanup_port() {
    local port="$1"
    local pids

    pids="$(lsof -t -i :"${port}" 2>/dev/null || true)"
    if [[ -n "${pids}" ]]; then
        echo "🧹 清理端口 ${port} 上的旧进程..."
        echo "🧹 Cleaning processes on port ${port}..."
        kill ${pids} 2>/dev/null || true
    fi
}

# 统一停止后台服务，确保 Ctrl+C 或异常退出时不会留下孤儿进程。
stop_services() {
    echo ""
    echo "🛑 正在停止服务..."
    echo "🛑 Stopping services..."

    if [[ -n "${API_PID}" ]]; then
        kill "${API_PID}" 2>/dev/null || true
    fi
    if [[ -n "${HTTP_PID}" ]]; then
        kill "${HTTP_PID}" 2>/dev/null || true
    fi

    wait 2>/dev/null || true
    echo "✅ 所有服务已停止"
    echo "✅ All services stopped"
}

trap stop_services INT TERM EXIT

cd "${PROJECT_ROOT}"

echo "🌟 启动观星地点查找器..."
echo "🌟 Starting Stargazing Place Finder..."

cleanup_port "${API_PORT}"
cleanup_port "${WEB_PORT}"
sleep 1

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ 错误: 未找到 uv 包管理器"
    echo "❌ Error: uv package manager not found"
    echo "请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if [[ ! -f "${WEB_ENTRY_PATH}" ]]; then
    echo "❌ 错误: 未找到前端入口 ${WEB_ENTRY_PATH}"
    echo "❌ Error: Web entry ${WEB_ENTRY_PATH} not found"
    exit 1
fi

echo "📦 检查项目依赖..."
echo "📦 Checking project dependencies..."
uv sync

echo "🚀 启动光污染 API 服务..."
echo "🚀 Starting Light Pollution API service..."
uv run python -m light_pollution.light_pollution_api &
API_PID=$!

sleep 2

echo "🌐 启动静态文件服务器..."
echo "🌐 Starting static file server..."
uv run python -m http.server "${WEB_PORT}" --directory "${PROJECT_ROOT}" &
HTTP_PID=$!

echo ""
echo "📍 Web URL: ${WEB_URL}"
echo "📍 API URL: ${API_URL}"
echo "💡 可通过 ?apiBaseUrl=http://<host>:<port> 覆盖前端 API 地址"
echo "💡 Override frontend API URL with ?apiBaseUrl=http://<host>:<port>"
echo "💡 使用 Ctrl+C 停止所有服务"
echo "💡 Press Ctrl+C to stop all services"
echo ""

wait
