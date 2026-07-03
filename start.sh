#!/bin/bash

# 观星地点查找器 - 快速启动脚本
# Stargazing Place Finder - Quick Start Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
API_PORT="${API_PORT:-5001}"
API_URL="http://localhost:${API_PORT}"
API_PID=""

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

    wait 2>/dev/null || true
    echo "✅ 所有服务已停止"
    echo "✅ All services stopped"
}

trap stop_services INT TERM EXIT

cd "${PROJECT_ROOT}"

echo "🌟 启动观星地点查找器..."
echo "🌟 Starting Stargazing Place Finder..."

cleanup_port "${API_PORT}"
sleep 1

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ 错误: 未找到 uv 包管理器"
    echo "❌ Error: uv package manager not found"
    echo "请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "📦 检查项目依赖..."
echo "📦 Checking project dependencies..."
uv sync

echo "🚀 启动 FastAPI 服务 (API + 前端)..."
echo "🚀 Starting FastAPI server (API + frontend)..."
uv run uvicorn server.main:app --host 0.0.0.0 --port "${API_PORT}" --reload &
API_PID=$!

sleep 2

echo ""
echo "📍 Web URL:  ${API_URL}"
echo "📍 API Docs: ${API_URL}/docs"
echo "📍 API 和前端已合并在同一端口，无需 CORS"
echo "📍 API and frontend served from a single port — no CORS needed"
echo "💡 可通过 ?apiBaseUrl=http://<host>:<port> 覆盖前端 API 地址"
echo "💡 Override frontend API URL with ?apiBaseUrl=http://<host>:<port>"
echo "💡 使用 Ctrl+C 停止所有服务"
echo "💡 Press Ctrl+C to stop all services"
echo ""

wait
