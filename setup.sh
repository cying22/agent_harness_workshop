#!/usr/bin/env bash
# Agent Harness Workshop 环境配置脚本
# 使用 uv 创建虚拟环境并安装依赖

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=========================================="
echo "  Agent Harness Workshop 环境配置"
echo "=========================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 未找到 uv，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "✓ uv $(uv --version)"

# 创建虚拟环境
echo ""
echo "→ 创建虚拟环境: $VENV_DIR"
uv venv "$VENV_DIR" --python 3.12

# 安装依赖
echo ""
echo "→ 安装依赖包..."
uv pip install --python "$VENV_DIR/bin/python" \
    openai \
    jupyter \
    ipykernel

# 注册 Jupyter kernel
echo ""
echo "→ 注册 Jupyter kernel..."
"$VENV_DIR/bin/python" -m ipykernel install --user --name agent-harness --display-name "Agent Harness Workshop"

# 验证安装
echo ""
echo "→ 验证安装..."
"$VENV_DIR/bin/python" -c "import openai; print(f'  ✓ openai {openai.__version__}')"
"$VENV_DIR/bin/python" -c "import jupyter; print(f'  ✓ jupyter 已安装')"

# 检查 DeepSeek API key
echo ""
echo "→ 检查 DEEPSEEK_API_KEY / DEEPSEEK_APIKEY..."
if [ -n "${DEEPSEEK_API_KEY:-${DEEPSEEK_APIKEY:-}}" ]; then
    echo "  ✓ 已检测到 DeepSeek API key"
    echo "  ✓ 当前模型: ${DEEPSEEK_MODEL:-deepseek-reasoner}"
else
    echo "  ⚠️  未检测到 DEEPSEEK_API_KEY / DEEPSEEK_APIKEY"
    echo "  请设置环境变量: DEEPSEEK_API_KEY（兼容 DEEPSEEK_APIKEY）"
    echo "  可选: DEEPSEEK_MODEL（默认 deepseek-reasoner）"
fi

echo ""
echo "=========================================="
echo "  ✅ 环境配置完成！"
echo "=========================================="
echo ""
echo "启动 Jupyter:"
echo "  cd $SCRIPT_DIR"
echo "  source .venv/bin/activate"
echo "  jupyter notebook"
echo ""
echo "或直接运行:"
echo "  $VENV_DIR/bin/jupyter notebook --notebook-dir=$SCRIPT_DIR"
echo ""
echo "打开后选择 kernel: Agent Harness Workshop"
