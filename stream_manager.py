import cv2
import time
import json
import os
import re
from datetime import datetime
from threading import Thread, Event
from typing import Optional, Dict, List, Callable

class StreamManager:
    def __init__(self, logger):
        self.save_dir = os.path.join('static', 'captures')
        self.current_stream = None
        self.stop_event = Event()
        self.logger = logger
        self.history_file = 'stream_history.json'
        
        # 确保保存目录存在
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 加载历史记录
        self._load_history()

    def _load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            else:
                self.history = []
        except Exception as e:
            self.logger.error(f'加载历史记录失败: {str(e)}')
            self.history = []

    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f'保存历史记录失败: {str(e)}')

    def add_to_history(self, url):
        """添加URL到历史记录"""
        try:
            # 检查URL是否已存在
            for item in self.history:
                if item['url'] == url:
                    # 更新最后使用时间
                    item['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self._save_history()
                    return

            # 添加新记录
            self.history.append({
                'url': url,
                'name': url,  # 可以根据需要修改显示名称
                'last_used': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            self._save_history()
        except Exception as e:
            self.logger.error(f'添加历史记录失败: {str(e)}')

    def remove_from_history(self, url):
        """从历史记录中删除URL"""
        try:
            self.history = [item for item in self.history if item['url'] != url]
            self._save_history()
        except Exception as e:
            self.logger.error(f'删除历史记录失败: {str(e)}')

    def get_history(self):
        """获取历史记录列表"""
        return sorted(self.history, key=lambda x: x['last_used'], reverse=True)

    def create_folder(self):
        """创建新的保存文件夹"""
        try:
            folder_name = datetime.now().strftime('%Y%m%d_%H%M')
            folder_path = os.path.join(self.save_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            self.logger.info(f'创建新文件夹: {folder_path}')
            return folder_name
        except Exception as e:
            self.logger.error(f'创建文件夹失败: {str(e)}')
            raise

    def start_capture(self, stream_url, on_frame_captured=None, on_error=None, on_new_folder=None):
        """开始捕获视频流"""
        if self.current_stream is not None:
            self.logger.warning('已有视频流正在捕获，请先停止')
            raise Exception('已有视频流正在捕获，请先停止')

        try:
            # 验证RTMP URL
            if not self._is_valid_rtmp_url(stream_url):
                raise ValueError('无效的RTMP地址格式')

            # 创建新的保存文件夹
            current_folder = self.create_folder()
            if on_new_folder:
                on_new_folder(current_folder)

            # 添加到历史记录
            self.add_to_history(stream_url)

            # 设置OpenCV的RTMP流参数
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
            
            # 打开视频流
            self.logger.info(f'开始捕获视频流: {stream_url}')
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
            
            # 设置缓冲区大小
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            
            # 设置超时参数
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            
            if not cap.isOpened():
                raise Exception('无法打开视频流')

            self.current_stream = cap
            self.stop_event.clear()
            
            # 启动捕获线程
            thread = Thread(target=self._capture_thread, 
                          args=(stream_url, current_folder, on_frame_captured, on_error, on_new_folder))
            thread.daemon = True
            thread.start()
            
            return current_folder

        except Exception as e:
            self.logger.error(f'启动捕获失败: {str(e)}')
            if self.current_stream is not None:
                self.current_stream.release()
                self.current_stream = None
            raise

    def _capture_thread(self, stream_url, current_folder, on_frame_captured, on_error, on_new_folder):
        """捕获线程"""
        consecutive_errors = 0
        last_folder_time = time.time()
        folder_interval = 60  # 每60秒创建新文件夹
        
        try:
            while not self.stop_event.is_set():
                try:
                    # 检查是否需要创建新文件夹
                    current_time = time.time()
                    if current_time - last_folder_time >= folder_interval:
                        current_folder = self.create_folder()
                        if on_new_folder:
                            on_new_folder(current_folder)
                        last_folder_time = current_time
                        consecutive_errors = 0  # 重置错误计数

                    # 读取帧
                    ret, frame = self.current_stream.read()
                    
                    if not ret:
                        consecutive_errors += 1
                        self.logger.warning(f'读取帧失败，连续错误次数: {consecutive_errors}')
                        
                        if consecutive_errors >= 5:  # 连续5次失败后尝试重新连接
                            self.logger.warning('尝试重新连接视频流')
                            self.current_stream.release()
                            self.current_stream = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                            if not self.current_stream.isOpened():
                                raise Exception('重新连接视频流失败')
                            consecutive_errors = 0
                        continue

                    # 重置错误计数
                    consecutive_errors = 0

                    # 检查帧是否有效
                    if frame is None or frame.size == 0:
                        self.logger.warning('收到无效帧')
                        continue

                    # 保存图片
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'frame_{timestamp}.jpg'
                    filepath = os.path.join(self.save_dir, current_folder, filename)
                    
                    # 保存图片
                    if cv2.imwrite(filepath, frame):
                        self.logger.info(f'成功保存图片: {filepath}')
                        if on_frame_captured:
                            on_frame_captured(current_folder, filename)
                    else:
                        self.logger.error(f'保存图片失败: {filepath}')

                    # 等待一秒
                    time.sleep(1)

                except Exception as e:
                    self.logger.error(f'捕获过程出错: {str(e)}')
                    if on_error:
                        on_error(str(e))
                    time.sleep(1)  # 出错后等待一秒再继续

        except Exception as e:
            self.logger.error(f'捕获线程异常: {str(e)}')
            if on_error:
                on_error(str(e))
        finally:
            if self.current_stream is not None:
                self.current_stream.release()
                self.current_stream = None
            self.logger.info('捕获线程结束')

    def stop_capture_stream(self):
        """停止捕获视频流"""
        try:
            self.stop_event.set()
            if self.current_stream is not None:
                self.current_stream.release()
                self.current_stream = None
            self.logger.info('停止捕获视频流')
        except Exception as e:
            self.logger.error(f'停止捕获失败: {str(e)}')
            raise

    def get_folders(self):
        """获取所有捕获文件夹"""
        try:
            if not os.path.exists(self.save_dir):
                return []
            folders = [d for d in os.listdir(self.save_dir) 
                      if os.path.isdir(os.path.join(self.save_dir, d))]
            return sorted(folders, reverse=True)
        except Exception as e:
            self.logger.error(f'获取文件夹列表失败: {str(e)}')
            return []

    def get_images(self, folder):
        """获取指定文件夹中的所有图片"""
        try:
            folder_path = os.path.join(self.save_dir, folder)
            if not os.path.exists(folder_path):
                self.logger.error(f'文件夹不存在: {folder_path}')
                return []
            
            images = [f for f in os.listdir(folder_path) 
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            return sorted(images)
        except Exception as e:
            self.logger.error(f'获取图片列表失败: {str(e)}')
            return []

    def _is_valid_rtmp_url(self, url):
        """验证RTMP URL格式"""
        pattern = r'^rtmp://[a-zA-Z0-9\-\.]+(:[0-9]+)?(/[a-zA-Z0-9\-\._~:/?#[\]@!$&\'()*+,;=]*)?$'
        return bool(re.match(pattern, url)) 