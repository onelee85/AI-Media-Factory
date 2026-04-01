# AI Media Factory

一个基于 AI 的自动化媒体内容制作平台，集成 LLM 脚本生成、TTS 语音合成、字幕制作和视频渲染功能。

## ✨ 功能特性

- **📝 脚本生成** - 使用 LLM 自动生成视频脚本
- **🎙️ TTS 语音合成** - 支持 Edge-TTS 和多语音选择
- **📄 字幕制作** - 自动生成 SRT 字幕文件
- **🖼️ 素材搜索** - 集成 Pexels 图片素材库
- **🎬 视频合成** - 使用 Remotion + FFmpeg 渲染视频
- **🖥️ Web UI** - 可视化操作界面

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                      Web UI (FastAPI)                   │
├─────────────────────────────────────────────────────────┤
│  API Layer (scripts / preview / videos / health)        │
├─────────────────────────────────────────────────────────┤
│  Services Layer                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │  Script    │ │   TTS      │ │   Media    │          │
│  │ Generator  │ │  Service   │ │  Service   │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │  Subtitle  │ │  Compose   │ │   Model    │          │
│  │  Service   │ │  Service   │ │  Provider  │          │
│  └────────────┘ └────────────┘ └────────────┘          │
├─────────────────────────────────────────────────────────┤
│  Task Queue (Celery + Redis)                            │
│  tts / media / render / compose / scripts               │
├─────────────────────────────────────────────────────────┤
│  Storage Layer                                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │ PostgreSQL │ │   Redis    │ │  File Sys  │          │
│  └────────────┘ └────────────┘ └────────────┘          │
└─────────────────────────────────────────────────────────┘
```

## 📋 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 任务队列 | Celery + Redis |
| 数据库 | PostgreSQL (asyncpg) |
| 视频渲染 | Remotion (React) + FFmpeg |
| TTS | Edge-TTS |
| LLM 集成 | LiteLLM (OpenAI / Anthropic / LM Studio) |
| 素材搜索 | Pexels API |

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+ (Remotion)
- Docker & Docker Compose
- FFmpeg

### 1. 克隆项目

```bash
git clone <repository-url>
cd AI-Media-Factory
```

### 2. 启动依赖服务

```bash
# 启动 Redis 和 PostgreSQL
make up
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

### 4. 安装依赖

```bash
# Python 依赖
make install

# Remotion 依赖
cd remotion && npm install
```

### 5. 启动服务

```bash
# 开发模式
make dev

# 或手动启动
uvicorn app.main:app --reload
celery -A app.celery_app worker --loglevel=info
```

### 6. 访问应用

- Web UI: http://localhost:8000
- API 文档: http://localhost:8000/docs

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# 应用配置
APP_NAME=AI-Media-Factory
DEBUG=false

# 数据库
DB_PASSWORD=your-db-password

# Redis
REDIS_PASSWORD=your-redis-password

# 存储路径
STORAGE_ROOT=./storage

# FFmpeg
FFMPEG_BINARY=ffmpeg
FFPROBE_BINARY=ffprobe

# API Keys
PEXELS_API_KEY=your-pexels-api-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### LLM 配置 (config/models.yaml)

支持多种 LLM 提供商配置，包括：
- OpenAI
- Anthropic
- Azure OpenAI
- LM Studio (本地推理)

### 数据库配置 (config/database.yaml)

PostgreSQL 连接配置，支持环境变量替换。

### Redis 配置 (config/redis.yaml)

Redis 连接配置，支持密码认证。

## 📁 项目结构

```
AI-Media-Factory/
├── app/
│   ├── api/              # API 路由
│   │   ├── health.py     # 健康检查
│   │   ├── scripts.py    # 脚本接口
│   │   ├── preview.py    # 预览接口
│   │   └── videos.py     # 视频接口
│   ├── services/         # 业务服务
│   │   ├── script_generator.py   # 脚本生成
│   │   ├── tts_service.py        # TTS 服务
│   │   ├── media_service.py      # 媒体服务
│   │   ├── subtitle_service.py   # 字幕服务
│   │   ├── compose_service.py    # 合成服务
│   │   ├── model_provider.py     # LLM 提供商
│   │   ├── orchestrator.py       # 流程编排
│   │   └── voice_manager.py      # 语音管理
│   ├── tasks/            # Celery 任务
│   ├── models/           # 数据模型
│   ├── web/              # Web UI 静态文件
│   ├── config.py         # 配置管理
│   ├── db.py             # 数据库连接
│   ├── celery_app.py     # Celery 应用
│   └── main.py           # FastAPI 入口
├── config/               # 配置文件
│   ├── database.yaml
│   ├── redis.yaml
│   └── models.yaml
├── remotion/             # Remotion 视频渲染
├── scripts/              # 辅助脚本
├── storage/              # 文件存储
├── tests/                # 测试文件
├── docker-compose.yml    # Docker 编排
├── pyproject.toml        # Python 项目配置
└── Makefile              # 常用命令
```

## 🛠️ 开发命令

```bash
make up       # 启动 Docker 服务 (Redis, PostgreSQL)
make down     # 停止 Docker 服务
make install  # 安装 Python 依赖
make dev      # 启动开发环境
make logs     # 查看 Docker 日志
make test     # 运行测试
make check    # 代码检查 (Ruff)
```

## 🔄 工作流程

1. **创建脚本** - 通过 API 或 Web UI 提交主题
2. **生成内容** - LLM 自动生成视频脚本
3. **语音合成** - Edge-TTS 将文本转为语音
4. **素材搜索** - 从 Pexels 获取匹配图片
5. **字幕生成** - 基于 TTS 时间轴生成字幕
6. **视频渲染** - Remotion 合成最终视频

## 📊 Celery 队列

| 队列名称 | 用途 |
|----------|------|
| tts | 语音合成任务 |
| media | 媒体处理任务 |
| render | 视频渲染任务 |
| compose | 合成任务 |
| scripts | 脚本生成任务 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。

## 📄 许可证

[待定]
