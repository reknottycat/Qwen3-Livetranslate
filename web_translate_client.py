import os
import json
import time
import base64
import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, Callable, List
import websockets
from websockets.exceptions import ConnectionClosed

# 创建日志目录
os.makedirs("logs", exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/web_translate_client.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class WebTranslateClient:
    """阿里云DashScope WebSocket客户端，用于实时语音翻译"""
    
    def __init__(
        self,
        api_key: str,
        target_language: str = "zh-Hans",
        voice: str = "zh-CN-YunxiNeural",
        audio_enabled: bool = True,
        model_id: str = "qwen-audio-turbo"
    ):
        """
        初始化WebTranslateClient
        
        参数:
            api_key: 阿里云DashScope API密钥
            target_language: 目标翻译语言
            voice: 语音合成音色
            audio_enabled: 是否启用音频输出
            model_id: 使用的模型ID
        """
        self.api_key = api_key
        self.target_language = target_language
        self.voice = voice
        self.audio_enabled = audio_enabled
        self.model_id = model_id
        self.websocket = None
        self.is_connected = False
        self.on_text_callback = None
        self.on_audio_callback = None
        self.on_error_callback = None
        self.on_close_callback = None
        self.on_open_callback = None
        self.last_activity_time = time.time()
        self.heartbeat_task = None
        self.receive_task = None
        
        logger.info(f"WebTranslateClient初始化 - 目标语言: {target_language}, 音色: {voice}, 音频启用: {audio_enabled}")
    
    async def connect(self):
        """连接到阿里云DashScope WebSocket服务"""
        try:
            if self.is_connected:
                logger.warning("已经连接到WebSocket服务，忽略重复连接请求")
                return
            
            # WebSocket连接URL
            url = "wss://dashscope.aliyuncs.com/api/v1/models/qwen-audio-turbo/streaming-translate"
            
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"正在连接到DashScope WebSocket服务: {url}")
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            self.last_activity_time = time.time()
            logger.info("成功连接到DashScope WebSocket服务")
            
            # 发送初始化消息
            await self._send_init_message()
            
            # 启动心跳任务
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # 启动接收任务
            self.receive_task = asyncio.create_task(self._receive_loop())
            
            # 调用打开回调
            if self.on_open_callback:
                await self.on_open_callback()
                
        except Exception as e:
            self.is_connected = False
            logger.error(f"连接到DashScope WebSocket服务失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 调用错误回调
            if self.on_error_callback:
                await self.on_error_callback(str(e))
            raise
    
    async def _send_init_message(self):
        """发送初始化消息"""
        try:
            init_message = {
                "task_id": f"task_{int(time.time())}",
                "input": {
                    "audio": {
                        "sample_rate": 16000,
                        "format": "pcm",
                        "channel": 1
                    }
                },
                "parameters": {
                    "target_language": self.target_language,
                    "text_to_speech": {
                        "enabled": self.audio_enabled,
                        "voice": self.voice
                    }
                }
            }
            
            logger.info(f"发送初始化消息: {json.dumps(init_message, ensure_ascii=False)}")
            await self.websocket.send(json.dumps(init_message))
            logger.info("初始化消息发送成功")
            
        except Exception as e:
            logger.error(f"发送初始化消息失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise
    
    async def _heartbeat_loop(self):
        """心跳循环，定期发送心跳消息"""
        try:
            while self.is_connected:
                await asyncio.sleep(25)  # 每25秒发送一次心跳
                
                if not self.is_connected:
                    logger.info("连接已关闭，停止心跳")
                    break
                
                # 检查最后活动时间，如果超过30秒没有活动，发送心跳
                if time.time() - self.last_activity_time > 30:
                    try:
                        heartbeat_message = {"type": "heartbeat"}
                        logger.debug("发送心跳消息")
                        await self.websocket.send(json.dumps(heartbeat_message))
                        self.last_activity_time = time.time()
                    except Exception as e:
                        logger.error(f"发送心跳消息失败: {e}")
                        if not self.is_connected:
                            break
        except asyncio.CancelledError:
            logger.info("心跳任务被取消")
        except Exception as e:
            logger.error(f"心跳循环中发生错误: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    async def _receive_loop(self):
        """接收循环，处理服务器消息"""
        try:
            while self.is_connected:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                    self.last_activity_time = time.time()
                    
                    # 解析消息
                    data = json.loads(message)
                    await self._process_message(data)
                    
                except asyncio.TimeoutError:
                    logger.warning("WebSocket接收超时，检查连接状态")
                    # 发送心跳检查连接
                    try:
                        heartbeat_message = {"type": "heartbeat"}
                        await self.websocket.send(json.dumps(heartbeat_message))
                        logger.info("心跳消息发送成功，连接正常")
                    except Exception as e:
                        logger.error(f"发送心跳消息失败，连接可能已断开: {e}")
                        self.is_connected = False
                        break
                        
                except ConnectionClosed as e:
                    logger.warning(f"WebSocket连接已关闭: {e}")
                    self.is_connected = False
                    
                    # 调用关闭回调
                    if self.on_close_callback:
                        code = e.code if hasattr(e, 'code') else None
                        await self.on_close_callback(code)
                    break
                    
                except Exception as e:
                    logger.error(f"接收或处理消息时发生错误: {e}")
                    logger.error(f"错误详情: {traceback.format_exc()}")
                    
                    # 调用错误回调
                    if self.on_error_callback:
                        await self.on_error_callback(str(e))
        
        except asyncio.CancelledError:
            logger.info("接收任务被取消")
        except Exception as e:
            logger.error(f"接收循环中发生错误: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    async def _process_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            # 检查消息类型
            if "output" in data:
                output = data["output"]
                
                # 处理文本输出
                if "text" in output:
                    text = output["text"]
                    logger.debug(f"收到文本: {text}")
                    
                    # 调用文本回调
                    if self.on_text_callback:
                        await self.on_text_callback(text)
                
                # 处理音频输出
                if "audio" in output and output["audio"]:
                    audio_data = output["audio"]
                    logger.debug(f"收到音频数据: {len(audio_data)} 字符")
                    
                    # 解码Base64音频数据
                    try:
                        audio_bytes = base64.b64decode(audio_data)
                        
                        # 调用音频回调
                        if self.on_audio_callback:
                            await self.on_audio_callback(audio_bytes)
                    except Exception as e:
                        logger.error(f"解码音频数据失败: {e}")
            
            # 处理错误消息
            elif "error" in data:
                error = data["error"]
                error_code = error.get("code", "unknown")
                error_message = error.get("message", "Unknown error")
                logger.error(f"收到错误消息: {error_code} - {error_message}")
                
                # 调用错误回调
                if self.on_error_callback:
                    await self.on_error_callback(f"{error_code}: {error_message}")
            
            # 处理心跳响应
            elif data.get("type") == "heartbeat_response":
                logger.debug("收到心跳响应")
                
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    async def send_audio_data(self, audio_data: bytes):
        """发送音频数据"""
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("WebSocket未连接，无法发送音频数据")
                return
            
            # 编码为Base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 构建消息
            message = {
                "input": {
                    "audio": {
                        "data": audio_base64
                    }
                }
            }
            
            # 发送消息
            logger.debug(f"发送音频数据: {len(audio_data)} bytes")
            await self.websocket.send(json.dumps(message))
            self.last_activity_time = time.time()
            
        except Exception as e:
            logger.error(f"发送音频数据失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 调用错误回调
            if self.on_error_callback:
                await self.on_error_callback(str(e))
    
    async def send_image_frame(self, image_data: bytes):
        """发送图像帧数据（用于视频翻译）"""
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("WebSocket未连接，无法发送图像数据")
                return
            
            # 编码为Base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 构建消息
            message = {
                "input": {
                    "image": {
                        "data": image_base64
                    }
                }
            }
            
            # 发送消息
            logger.debug(f"发送图像数据: {len(image_data)} bytes")
            await self.websocket.send(json.dumps(message))
            self.last_activity_time = time.time()
            
        except Exception as e:
            logger.error(f"发送图像数据失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 调用错误回调
            if self.on_error_callback:
                await self.on_error_callback(str(e))
    
    async def send_end_signal(self):
        """发送结束信号"""
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("WebSocket未连接，无法发送结束信号")
                return
            
            # 构建结束消息
            end_message = {"input": {"end": True}}
            
            # 发送消息
            logger.info("发送结束信号")
            await self.websocket.send(json.dumps(end_message))
            self.last_activity_time = time.time()
            
        except Exception as e:
            logger.error(f"发送结束信号失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    async def close(self):
        """关闭WebSocket连接"""
        try:
            logger.info("正在关闭WebSocket连接")
            
            # 取消任务
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                
            if self.receive_task:
                self.receive_task.cancel()
            
            # 关闭WebSocket连接
            if self.websocket:
                await self.websocket.close()
                
            self.is_connected = False
            logger.info("WebSocket连接已关闭")
            
        except Exception as e:
            logger.error(f"关闭WebSocket连接时发生错误: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    def set_callbacks(
        self,
        on_text: Optional[Callable[[str], Any]] = None,
        on_audio: Optional[Callable[[bytes], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
        on_close: Optional[Callable[[Optional[int]], Any]] = None,
        on_open: Optional[Callable[[], Any]] = None
    ):
        """设置回调函数"""
        self.on_text_callback = on_text
        self.on_audio_callback = on_audio
        self.on_error_callback = on_error
        self.on_close_callback = on_close
        self.on_open_callback = on_open
        logger.info("回调函数已设置")