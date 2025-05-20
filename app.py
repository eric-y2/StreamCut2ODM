import os
import re
import threading
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from stream_manager import StreamManager
import eventlet
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

# 配置日志
def setup_logger():
    """配置日志记录器"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logger = logging.getLogger('stream_capture')
    logger.setLevel(logging.INFO)
    
    file_handler = RotatingFileHandler(
        'logs/stream_capture.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    
    console_handler = logging.StreamHandler()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 创建日志记录器
logger = setup_logger()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, async_mode='eventlet')

# 创建流管理器实例
stream_manager = StreamManager(logger)

# 全局变量
capture_thread = None

# 创建自定义日志处理器，用于发送日志到前端
class WebSocketLogHandler(logging.Handler):
    def __init__(self, socketio):
        super().__init__()
        self.socketio = socketio
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.socketio.emit('log', {
                'level': record.levelname.lower(),
                'message': msg
            })
        except Exception:
            self.handleError(record)

# 添加WebSocket日志处理器
ws_handler = WebSocketLogHandler(socketio)
logger.addHandler(ws_handler)

def is_valid_rtmp_url(url):
    """验证RTMP URL格式是否正确"""
    rtmp_pattern = r'^rtmp://[a-zA-Z0-9\-\.]+(:[0-9]+)?/[a-zA-Z0-9\-\._~:/?#\[\]@!$&\'()*+,;=]+$'
    return bool(re.match(rtmp_pattern, url))

@app.route('/')
def index():
    """渲染主页"""
    # 获取所有捕获文件夹
    captures_dir = os.path.join('static', 'captures')
    if not os.path.exists(captures_dir):
        os.makedirs(captures_dir)
    
    folders = sorted([d for d in os.listdir(captures_dir) 
                     if os.path.isdir(os.path.join(captures_dir, d))], 
                    reverse=True)
    
    # 获取历史记录
    history = stream_manager.get_history()
    
    return render_template('index.html', folders=folders, history=history)

@app.route('/start_capture', methods=['POST'])
def start_capture():
    """开始捕获视频流"""
    global capture_thread
    
    stream_url = request.json.get('stream_url')
    if not stream_url:
        return jsonify({'error': '请提供RTMP视频流URL'}), 400

    if not is_valid_rtmp_url(stream_url):
        return jsonify({'error': '无效的RTMP URL格式'}), 400

    if capture_thread and capture_thread.is_alive():
        return jsonify({'error': '已经在捕获中'}), 400

    # 添加到历史记录
    stream_manager.add_to_history(stream_url)

    def on_frame_captured(folder, filename):
        socketio.emit('new_image', {'folder': folder, 'filename': filename})

    def on_error(message):
        socketio.emit('error', {'message': message})

    def on_new_folder(folder):
        socketio.emit('new_folder', {'folder': folder})

    def capture_thread_func():
        stream_manager.start_capture(
            stream_url,
            on_frame_captured=on_frame_captured,
            on_error=on_error,
            on_new_folder=on_new_folder
        )

    capture_thread = threading.Thread(target=capture_thread_func)
    capture_thread.daemon = True
    capture_thread.start()
    
    return jsonify({
        'message': '开始捕获',
        'folder': os.path.basename(stream_manager.current_folder) if stream_manager.current_folder else None
    })

@app.route('/stop_capture', methods=['POST'])
def stop_capture_stream():
    """停止捕获视频流"""
    stream_manager.stop_capture_stream()
    return jsonify({'message': '停止捕获'})

@app.route('/get_images/<folder>')
def get_images(folder):
    """获取指定文件夹中的所有图片"""
    folder_path = os.path.join('static', 'captures', folder)
    if not os.path.exists(folder_path):
        return jsonify({'error': '文件夹不存在'}), 404
    
    images = sorted([f for f in os.listdir(folder_path) 
                    if f.endswith(('.jpg', '.jpeg', '.png'))])
    return jsonify({'images': images})

@app.route('/stream_history', methods=['GET'])
def get_stream_history():
    """获取流历史记录"""
    return jsonify(stream_manager.get_history())

@app.route('/stream_history/<path:stream_url>', methods=['DELETE'])
def delete_stream_history(stream_url):
    """删除流历史记录"""
    stream_manager.remove_from_history(stream_url)
    return jsonify({'message': '删除成功'})

@app.route('/captures/<folder>/<filename>')
def get_image(folder, filename):
    return send_from_directory(os.path.join('static', 'captures', folder), filename)

@app.route('/get_image_info/<folder>/<filename>')
def get_image_info(folder, filename):
    """获取图片的详细信息，包括EXIF数据"""
    try:
        filepath = os.path.join('static', 'captures', folder, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '图片不存在'}), 404

        # 获取文件信息
        file_stat = os.stat(filepath)
        file_info = {
            'filename': filename,
            'size': file_stat.st_size,
            'created_time': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified_time': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'dimensions': None,
            'exif': {}
        }

        # 使用PIL获取图片信息
        with Image.open(filepath) as img:
            # 获取图片尺寸
            file_info['dimensions'] = {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode
            }

            # 获取EXIF信息
            try:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        # 处理一些特殊的值
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8')
                            except:
                                value = str(value)
                        file_info['exif'][tag] = value
            except Exception as e:
                logger.warning(f'获取EXIF信息失败: {str(e)}')

        return jsonify(file_info)
    except Exception as e:
        logger.error(f'获取图片信息失败: {str(e)}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs(os.path.join('static', 'captures'), exist_ok=True)
    logger.info('应用启动')
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f'应用运行错误: {str(e)}')
    finally:
        logger.info('应用关闭') 