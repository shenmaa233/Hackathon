import socketio
import asyncio
import logging
from app.services.llm_service import llm_service
from typing import Dict

# 配置日志记录器
logger = logging.getLogger(__name__)

# 创建一个 ASGI 兼容的 Socket.IO 服务器实例
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# 存储每个 socket 连接（sid）对应的自定义会话ID
# 这层映射将 socketio 的临时 sid 与我们持久化的会话逻辑解耦
connection_sessions: Dict[str, str] = {}


@sio.event
async def connect(sid, environ):
    """
    处理新的客户端连接。
    为每个连接创建一个唯一的会话，并通知客户端连接成功。
    """
    logger.info(f"Client connected: sid={sid}")
    
    # 使用 sid 生成一个唯一的会话 ID
    session_id = f"session_{sid}"
    connection_sessions[sid] = session_id
    llm_service.create_session(session_id)
    
    await sio.emit("connected", {"message": "已连接到AI助手服务"}, room=sid)

@sio.event
async def disconnect(sid):
    """
    处理客户端断开连接。
    清理与该连接相关的会话数据，释放资源。
    """
    logger.info(f"Client disconnected: sid={sid}")
    
    if sid in connection_sessions:
        session_id = connection_sessions.pop(sid)
        llm_service.clear_session(session_id)
        logger.info(f"Cleaned up session {session_id} for disconnected client {sid}")

@sio.event
async def message(sid, data):
    """
    接收并处理来自客户端的用户消息，以流式方式返回AI响应。
    
    接收事件: 'message'
    接收数据: {'message': str}
    发送事件: 
      - 'generation_started': 通知客户端开始处理。
      - 'response_chunk': 流式发送AI响应的片段。
      - 'generation_completed': 通知客户端响应已全部发送完毕。
      - 'error': 发生错误时发送。
    """
    session_id = connection_sessions.get(sid)
    if not session_id:
        logger.warning(f"Message from unknown sid: {sid}")
        return await sio.emit("error", {"message": "会话未找到，请重新连接"}, room=sid)

    user_message = data.get('message', '').strip()
    if not user_message:
        return await sio.emit("error", {"message": "消息不能为空"}, room=sid)
        
    logger.info(f"Received message from session {session_id}: '{user_message[:100]}...'")
    
    try:
        await sio.emit("generation_started", {"message": "AI正在思考中..."}, room=sid)
        
        full_response = ""
        async for chunk in llm_service.generate_response_stream(session_id, user_message):
            if chunk:
                full_response += chunk
                
                # 检查是否包含PIC模拟数据
                pic_data = None
                if '"visualization_type": "pic_simulation"' in chunk:
                    try:
                        # 提取PIC模拟数据
                        import json
                        import re
                        json_match = re.search(r'\{.*"visualization_type":\s*"pic_simulation".*\}', chunk, re.DOTALL)
                        if json_match:
                            pic_data = json.loads(json_match.group())
                            logger.info(f"Extracted PIC data with {len(pic_data.get('data', {}).get('frames', []))} frames")
                    except Exception as e:
                        logger.error(f"Failed to parse PIC data: {e}")
                
                await sio.emit("response_chunk", {
                    "chunk": chunk,
                    "full_response": full_response,
                    "pic_data": pic_data
                }, room=sid)
                
                # 如果有PIC数据，发送canvas展开信号
                if pic_data:
                    # 获取完整的模拟数据
                    full_simulation_data = pic_data
                    if pic_data.get('full_data_available'):
                        # 尝试从工具实例获取完整数据
                        from app.agent.tools.pic_simulation import PICSimulation
                        try:
                            # 这里需要找到正确的工具实例
                            # 暂时使用概览数据，后续可以优化
                            pass
                        except:
                            pass
                    
                    await sio.emit("canvas_expand", {
                        "simulation_data": full_simulation_data
                    }, room=sid)
                    logger.info(f"Sent canvas_expand event with PIC data")

        await sio.emit("generation_completed", {"final_response": full_response}, room=sid)
        
    except Exception as e:
        logger.error(f"Error processing message for session {session_id}: {e}", exc_info=True)
        await sio.emit("error", {"message": f"处理消息时发生错误: {str(e)}"}, room=sid)


@sio.event
async def stop_generation(sid, _):
    """
    处理客户端的停止生成请求。
    
    接收事件: 'stop_generation'
    发送事件:
      - 'generation_stopped': 成功停止后发送。
      - 'error': 无法停止时发送。
    """
    session_id = connection_sessions.get(sid)
    if not session_id:
        return await sio.emit("error", {"message": "会话未找到"}, room=sid)

    if llm_service.stop_generation(session_id):
        logger.info(f"Generation stop requested and processed for session: {session_id}")
        await sio.emit("generation_stopped", {"message": "生成已停止"}, room=sid)
    else:
        logger.warning(f"Failed to stop generation for session: {session_id}, it might not be running.")
        await sio.emit("error", {"message": "无法停止，可能当前没有正在生成的内容"}, room=sid)

@sio.event
async def get_history(sid, _):
    """
    处理客户端获取历史消息的请求。
    
    接收事件: 'get_history'
    发送事件:
      - 'history': 携带历史消息列表。
    """
    session_id = connection_sessions.get(sid)
    if not session_id:
        return await sio.emit("error", {"message": "会话未找到"}, room=sid)
    
    history = llm_service.get_session_history(session_id)
    await sio.emit("history", {"messages": history}, room=sid)

@sio.event
async def clear_history(sid, _):
    """
    处理客户端清除当前会话历史的请求。
    
    接收事件: 'clear_history'
    发送事件:
      - 'history_cleared': 成功清除后发送。
    """
    session_id = connection_sessions.get(sid)
    if not session_id:
        return await sio.emit("error", {"message": "会话未找到"}, room=sid)
    
    # 重新创建一个空的会话状态，覆盖旧的
    llm_service.create_session(session_id) 
    
    logger.info(f"History cleared for session: {session_id}")
    await sio.emit("history_cleared", {"message": "历史记录已清除"}, room=sid)


@sio.event
async def ping(sid, data):
    """
    处理客户端的心跳检测，用于保持连接活跃。
    
    接收事件: 'ping'
    接收数据: {'timestamp': any}
    发送事件: 'pong'
    """
    await sio.emit("pong", {"timestamp": data.get("timestamp")}, room=sid)