#!/bin/bash

# YXT Manual T0 Collaboration - Claude Code 启动脚本
# 使用阿里云百炼 API

# 设置环境变量
export ANTHROPIC_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
export ANTHROPIC_API_KEY="sk-sp-7cd7757da4eb479db08897359fb43463"
export ANTHROPIC_MODEL="qwen3.5-plus"

# 切换到项目目录
cd "$(dirname "$0")"

# 启动 Claude Code
echo "🦞 YXT Code Agent 启动中..."
echo "📁 项目目录：$(pwd)"
echo "🤖 模型：qwen3.5-plus (阿里云百炼)"
echo "📝 查看 PROJECT_STATUS.md 了解当前进度"
echo ""

node /home/admin/.openclaw/workspace/node_modules/@anthropic-ai/claude-code/cli.js "$@"
