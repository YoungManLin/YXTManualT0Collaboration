# Claude Code 配置说明

## 环境变量配置

使用阿里云百炼 API 代替 Anthropic API：

```bash
export ANTHROPIC_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
export ANTHROPIC_API_KEY="sk-sp-7cd7757da4eb479db08897359fb43463"
export ANTHROPIC_MODEL="qwen3.5-plus"
```

## 使用方式

### 启动交互式会话
```bash
cd /home/admin/.openclaw/workspace/YXTManualT0Collaboration
export ANTHROPIC_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
export ANTHROPIC_API_KEY="sk-sp-7cd7757da4eb479db08897359fb43463"
export ANTHROPIC_MODEL="qwen3.5-plus"
./node_modules/.bin/claude
```

### 执行单个任务
```bash
export ANTHROPIC_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
export ANTHROPIC_API_KEY="sk-sp-7cd7757da4eb479db08897359fb43463"
export ANTHROPIC_MODEL="qwen3.5-plus"
./node_modules/.bin/claude "帮我实现 CCTJ 仓位文件解析功能"
```

## 项目信息

- **仓库**: https://github.com/YoungManLin/YXTManualT0Collaboration
- **项目状态**: 查看 PROJECT_STATUS.md
- **核心概念**: 
  - CCTJ 仓位文件（GT 系统）
  - 虚拟持仓 vs 真实持仓
  - T0 交易逻辑
  - DBF 预埋单

## 开发原则

1. 一次只做一个功能模块
2. 完成后立即提交 Git
3. 等待确认后再继续下一步
4. 有疑问先问，不要假设需求

## 当前任务

等待用户提供 CCTJ 仓位文件格式文档，然后开始实现。
