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
    "anthropic[bedrock]" \
    jupyter \
    ipykernel

# 注册 Jupyter kernel
echo ""
echo "→ 注册 Jupyter kernel..."
"$VENV_DIR/bin/python" -m ipykernel install --user --name agent-harness --display-name "Agent Harness Workshop"

# 验证安装
echo ""
echo "→ 验证安装..."
"$VENV_DIR/bin/python" -c "import anthropic; print(f'  ✓ anthropic {anthropic.__version__}')"
"$VENV_DIR/bin/python" -c "import jupyter; print(f'  ✓ jupyter 已安装')"

# 检查 AWS credentials
echo ""
echo "→ 检查 AWS credentials..."
if "$VENV_DIR/bin/python" -c "
import boto3
sts = boto3.client('sts')
identity = sts.get_caller_identity()
print(f'  ✓ AWS Account: {identity[\"Account\"]}')
" 2>/dev/null; then
    :
else
    echo "  ⚠️  未检测到 AWS credentials"
    echo "  请运行: aws configure"
    echo "  或设置环境变量: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY"
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
