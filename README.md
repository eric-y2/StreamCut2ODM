# 视频流截图工具

这是一个基于 Flask 和 OpenCV 的视频流截图工具，可以从 RTMP 视频流中捕获图片并保存。

## 功能特点

- 支持 RTMP 视频流输入
- 自动按时间创建文件夹存储图片
- 实时预览捕获的图片
- 支持历史记录管理
- 完整的错误处理和日志记录
- 模块化设计，易于扩展

## 目录结构

```
.
├── app.py                 # 主应用文件，处理Web请求和路由
├── stream_manager.py      # 视频流管理模块，处理视频流捕获核心功能
├── requirements.txt       # Python依赖包列表
├── README.md             # 项目说明文档
├── logs/                 # 日志目录
│   └── stream_capture.log # 应用运行日志
├── static/               # 静态文件目录
│   └── captures/         # 图片保存目录
│       └── YYYYMMDD_HHMM/ # 按时间戳命名的图片文件夹
│           └── frame_*.jpg # 捕获的图片文件
├── templates/            # 模板目录
│   └── index.html        # 主页面模板
└── stream_history.json   # 视频流历史记录文件
```

### 文件说明

- `app.py`: 
  - Flask 应用主文件
  - 处理所有 Web 请求和路由
  - 管理 WebSocket 连接
  - 提供 RESTful API 接口

- `stream_manager.py`:
  - 视频流管理核心模块
  - 处理视频流连接和帧捕获
  - 管理历史记录
  - 处理图片保存
  - 错误处理和日志记录

- `requirements.txt`:
  - 列出所有必需的 Python 包
  - 包含版本信息

- `logs/stream_capture.log`:
  - 应用运行日志
  - 记录所有操作和错误信息
  - 自动轮转，限制大小

- `static/captures/`:
  - 存储捕获的图片
  - 按时间戳自动创建子文件夹
  - 每个文件夹包含一分钟内的图片

- `templates/index.html`:
  - 主页面模板
  - 包含用户界面
  - 处理前端交互
  - 管理历史记录显示

- `stream_history.json`:
  - 存储视频流历史记录
  - JSON 格式
  - 包含 URL 和使用时间

## 安装说明

1. 创建虚拟环境：
```bash
python -m venv venv
```

2. 激活虚拟环境：
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 运行应用

1. 确保虚拟环境已激活
2. 运行应用：
```bash
python app.py
```
3. 在浏览器中访问：`http://localhost:5000`

## 使用说明

1. 在输入框中输入 RTMP 视频流地址
2. 点击历史记录图标（时钟图标）可以查看之前使用过的地址
3. 点击历史记录中的地址可以快速填充到输入框
4. 点击历史记录中的垃圾桶图标可以删除该记录
5. 点击"开始捕获"按钮开始捕获图片
6. 捕获的图片会自动保存在按时间创建的文件夹中
7. 可以点击左侧文件夹列表查看不同时间段的图片
8. 点击"停止捕获"按钮停止捕获

## 注意事项

- 确保输入的 RTMP 地址格式正确
- 需要稳定的网络连接
- 建议定期清理捕获的图片文件
- 日志文件会自动轮转，但建议定期检查日志目录大小

## 依赖包

- Flask
- Flask-SocketIO
- opencv-python
- python-dotenv
- eventlet

## 开发说明

- 使用模块化设计，便于扩展
- 完整的错误处理机制
- 详细的日志记录
- 支持历史记录管理
- 响应式用户界面

## 系统要求

- Python 3.7+
- OpenCV
- Flask
- Flask-SocketIO
- 其他依赖项（见requirements.txt）

## 安装步骤

1. 克隆或下载本项目到本地

2. 创建并激活虚拟环境（可选但推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖项：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动应用：
```bash
python app.py
```

2. 在浏览器中访问：
```
http://localhost:5000
```

3. 在输入框中输入WebRTC视频流地址

4. 点击"开始捕获"按钮开始截取图片

5. 点击"停止捕获"按钮停止截取

6. 在左侧文件夹列表中查看和选择不同的捕获文件夹

7. 在右侧图片预览区域查看捕获的图片

## 注意事项

- 确保视频流地址格式正确且可访问
- 图片将保存在 `static/captures` 目录下
- 每个文件夹以时间戳命名，格式为：YYYYMMDD_HHMM
- 图片文件以时间戳命名，格式为：frame_YYYYMMDD_HHMMSS.jpg

## 许可证

MIT License 