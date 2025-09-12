# AI Assistant - 智能对话与可视化平台

一个现代化的AI助手平台，支持实时对话、流式响应、3D可视化等功能。

## ✨ 功能特性

- 🤖 **智能对话**: 基于Qwen模型的AI助手
- 🌊 **流式响应**: 实时流式文本生成
- ⏹️ **停止控制**: 随时停止AI生成
- 🎨 **现代UI**: 类似ChatGPT的美观界面
- 🌓 **主题切换**: 支持深色/浅色主题
- 🎮 **3D可视化**: 交互式3D画布
- 📱 **响应式设计**: 完美适配各种设备

## 🚀 快速开始

### 前提条件

- Python 3.8+
- Node.js 16+
- 运行中的Qwen模型服务 (http://localhost:8000/v1)

### 安装依赖

#### 后端
```bash
cd backend
pip install -r requirements.txt
```

#### 前端
```bash
cd frontend
npm install
```

### 启动服务

#### 方法1: 使用启动脚本（推荐）
```bash
# 启动后端
python start_backend.py

# 新终端启动前端
cd frontend
npm run dev
```

#### 方法2: 分别启动
```bash
# 后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 前端
cd frontend
npm run dev
```

### 访问应用

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8080
- **API文档**: http://localhost:8080/docs
- **健康检查**: http://localhost:8080/health

## 🏗️ 项目结构

```
Hackathon/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   │   └── chat.py     # Socket.IO聊天接口
│   │   ├── services/       # 业务服务
│   │   │   └── llm_service.py  # LLM服务
│   │   └── main.py         # FastAPI应用
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   │   ├── Chat.tsx    # 聊天组件
│   │   │   ├── Canvas.tsx  # 3D画布组件
│   │   │   ├── Header.tsx  # 头部组件
│   │   │   └── ThemeProvider.tsx  # 主题提供者
│   │   ├── App.tsx         # 主应用组件
│   │   └── index.css       # 全局样式
│   └── package.json        # 前端依赖
├── start_backend.py        # 后端启动脚本
└── README.md              # 项目文档
```

## 🎯 使用说明

### 聊天功能
1. 在聊天框中输入消息
2. 点击发送按钮或按Enter发送
3. AI开始回复时，发送按钮变为停止按钮
4. 点击停止按钮可随时中断生成
5. 使用垃圾桶按钮清除对话历史

### 3D可视化
- 鼠标拖拽旋转视角
- 滚轮缩放场景
- 点击立方体交互
- 点击全屏按钮进入全屏模式

### 主题切换
- 点击右上角月亮/太阳图标切换主题
- 支持跟随系统主题设置

## 🔧 配置说明

### 后端配置
在 `backend/app/services/llm_service.py` 中配置LLM参数：

```python
self.llm_cfg = {
    'model': 'Qwen/Qwen3-4B-Instruct-2507-FP8',
    'model_server': 'http://localhost:8000/v1',  # 修改为你的模型服务地址
    'generate_cfg': {
        'top_p': 0.8
    }
}
```

### 前端配置
在 `frontend/.env` 中设置后端地址：

```env
VITE_BACKEND_URL=ws://localhost:8080
```

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 确保后端服务正在运行
   - 检查端口是否被占用
   - 确认防火墙设置

2. **LLM响应错误**
   - 确保Qwen模型服务正在运行
   - 检查模型服务地址配置
   - 查看后端日志获取详细错误信息

3. **前端无法加载**
   - 确保Node.js版本兼容
   - 重新安装依赖: `rm -rf node_modules && npm install`
   - 检查浏览器控制台错误

## 📝 开发说明

### 后端开发
- 使用FastAPI框架
- Socket.IO实现实时通信
- 异步处理提高性能
- 支持多会话管理

### 前端开发
- React + TypeScript
- 现代化CSS变量系统
- 响应式设计
- Three.js 3D渲染

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证。