#!/usr/bin/env python3
"""
测试PIC模拟GIF生成功能
"""
import socketio
import time
import json

# 创建Socket.IO客户端
sio = socketio.Client()

@sio.event
def connect():
    print("✅ 连接成功!")

@sio.event
def connected(data):
    print(f"🔗 服务器确认连接: {data}")

@sio.event
def generation_started(data):
    print(f"🤖 AI开始生成: {data}")

@sio.event
def response_chunk(data):
    chunk = data.get('chunk', '')
    print(f"📝 收到回复: {chunk}")
    
    # 检查是否包含GIF链接
    if 'gif' in chunk.lower() and 'http' in chunk:
        print("🎬 检测到GIF链接!")

@sio.event
def generation_completed(data):
    print(f"✅ 生成完成!")
    print("完整响应:")
    print(data.get('final_response', ''))

@sio.event
def error(data):
    print(f"❌ 错误: {data}")

def main():
    try:
        print("🚀 连接到后端服务...")
        sio.connect('http://localhost:8080')
        
        print("📤 发送PIC模拟请求...")
        sio.emit('message', {
            'message': '请运行一个双流不稳定性模拟，我想看到动画效果'
        })
        
        # 等待响应
        print("⏳ 等待AI响应和GIF生成...")
        time.sleep(60)  # 等待60秒看结果
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    finally:
        sio.disconnect()
        print("🔌 连接已断开")

if __name__ == "__main__":
    main()
