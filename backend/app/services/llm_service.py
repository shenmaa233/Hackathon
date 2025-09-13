import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional

from qwen_agent.agents import Assistant
import logging

# 导入工具以确保它们被注册
from app.agent.tools import PICSimulation, KcatPredict

# 配置日志记录器
logger = logging.getLogger(__name__)

# 定义消息和会话状态的类型别名，增强可读性
Message = Dict[str, Any]
SessionState = Dict[str, Any]

class LLMService:
    """
    封装了与Qwen LLM的交互，并管理多用户会话的核心服务。
    """

    def __init__(self):
        """
        初始化LLM服务，配置模型、工具和系统提示。
        """
        self.llm_cfg = {
            'model': 'Qwen/Qwen3-4B-Instruct-2507-FP8',
            'model_server': 'http://localhost:8000/v1',
            'generate_cfg': {
                'top_p': 0.8
            }
        }
        
        self.tools = ['image_gen', 'pic_simulation', 'kcat_predict']
        self.system = '''你是一个智能助手，可以回答用户的问题、生成图片、进行等离子体物理模拟和预测酶催化常数。

你有以下工具可以使用：
1. image_gen - 生成图片
2. pic_simulation - 进行Particle-in-Cell等离子体物理模拟
3. kcat_predict - 预测酶催化常数(kcat)

当用户询问关于等离子体、电子束、相空间、电场模拟等物理现象时，你可以使用pic_simulation工具进行模拟演示。

支持的模拟类型：
- two_stream: 双电子束不稳定性模拟
- single_beam: 单电子束模拟  
- landau_damping: 朗道阻尼模拟

当用户询问关于酶催化效率、kcat值预测、酶动力学等生物化学问题时，你可以使用kcat_predict工具进行预测。该工具需要：
- smiles: 底物分子的SMILES字符串
- protein_sequence: 酶的氨基酸序列
- log_transform: 是否进行对数变换(默认true)

请用中文回复用户。'''
        
        # 初始化 qwen-agent 助手
        self.bot = Assistant(
            llm=self.llm_cfg,
            system_message=self.system,
            function_list=self.tools
        )
        
        # 存储活跃的会话，以 session_id 为键
        self.active_sessions: Dict[str, SessionState] = {}

    def create_session(self, session_id: str) -> None:
        """
        为指定 session_id 创建一个新的、干净的会话状态。

        Args:
            session_id (str): 唯一的会话标识符。
        """
        if session_id in self.active_sessions:
            logger.warning(f"Session {session_id} already exists. It will be re-initialized.")
        
        self.active_sessions[session_id] = {
            'messages': [],
            'stop_flag': False,
            'is_generating': False
        }
        logger.info(f"Created session: {session_id}")

    def stop_generation(self, session_id: str) -> bool:
        """
        设置停止标志，以中断指定会话的流式生成。

        Args:
            session_id (str): 目标会话的标识符。

        Returns:
            bool: 如果会话存在且成功设置标志，则返回 True，否则返回 False。
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['stop_flag'] = True
            logger.info(f"Stop flag set for session: {session_id}")
            return True
        logger.warning(f"Attempted to stop generation for non-existent session: {session_id}")
        return False

    def is_generating(self, session_id: str) -> bool:
        """
        检查指定会话当前是否正在生成响应。

        Args:
            session_id (str): 目标会话的标识符。

        Returns:
            bool: 如果正在生成，则返回 True，否则返回 False。
        """
        return self.active_sessions.get(session_id, {}).get('is_generating', False)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        向指定会话的历史记录中添加一条消息。

        如果会话不存在，会自动创建。

        Args:
            session_id (str): 目标会话的标识符。
            role (str): 消息发送者的角色（如 'user', 'assistant'）。
            content (str): 消息内容。
        """
        if session_id not in self.active_sessions:
            self.create_session(session_id)
        
        self.active_sessions[session_id]['messages'].append({
            'role': role,
            'content': content
        })

    async def generate_response_stream(self, session_id: str, user_message: str) -> AsyncGenerator[str, None]:
        """
        为用户消息异步生成流式响应。

        Args:
            session_id (str): 当前会话的标识符。
            user_message (str): 用户输入的消息。

        Yields:
            str: LLM生成的响应内容块。
        """
        if session_id not in self.active_sessions:
            self.create_session(session_id)
        
        session = self.active_sessions[session_id]
        
        # 重置状态
        session['stop_flag'] = False
        session['is_generating'] = True
        
        self.add_message(session_id, 'user', user_message)
        
        try:
            messages_history = session['messages'].copy()
            
            # bot.run 是一个同步的生成器函数，不能直接在异步代码中 await。
            # 我们使用 loop.run_in_executor 将其放在一个独立的线程中运行，
            # 以避免阻塞 FastAPI 的事件循环。
            def _run_sync_bot() -> List[Message]:
                try:
                    # list() 会消耗掉整个生成器，获取所有结果
                    return list(self.bot.run(messages=messages_history))
                except Exception as e:
                    logger.error(f"Error during bot.run in thread: {e}", exc_info=True)
                    return []

            loop = asyncio.get_running_loop()
            response_chunks_list = await loop.run_in_executor(None, _run_sync_bot)
            
            final_content = ""
            for chunk in response_chunks_list:
                # 检查是否需要中途停止
                if session['stop_flag']:
                    logger.info(f"Generation stopped for session: {session_id}")
                    yield "[生成已停止]"
                    break

                # qwen-agent 的 run 方法返回的是一个包含历史消息的列表
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    
                    # 我们只关心助手最后一条不含函数调用的回复内容
                    if (last_message.get('role') == 'assistant' 
                        and last_message.get('content') 
                        and not last_message.get('function_call')):
                        
                        current_content = last_message['content']
                        
                        # 模型返回的是累计内容，我们只 yield 新增的部分
                        if len(current_content) > len(final_content):
                            new_content = current_content[len(final_content):]
                            final_content = current_content
                            yield new_content
                            await asyncio.sleep(0.01) # 短暂延迟，让事件循环处理其他任务

            # 如果生成未被停止，将最终的完整回复存入历史记录
            if final_content and not session['stop_flag']:
                self.add_message(session_id, 'assistant', final_content)
                
        except Exception as e:
            logger.error(f"Error in generate_response_stream for session {session_id}: {e}", exc_info=True)
            yield f"错误: {str(e)}"
        
        finally:
            # 确保在生成结束后，总是将状态标记为 False
            session['is_generating'] = False
            logger.info(f"Generation finished for session: {session_id}")

    def get_session_history(self, session_id: str) -> List[Message]:
        """
        获取指定会话的完整消息历史。

        Args:
            session_id (str): 目标会话的标识符。

        Returns:
            List[Message]: 包含消息历史的列表，如果会话不存在则返回空列表。
        """
        return self.active_sessions.get(session_id, {}).get('messages', [])

    def clear_session(self, session_id: str) -> bool:
        """
        从内存中删除指定的会话。

        Args:
            session_id (str): 要清除的会话的标识符。

        Returns:
            bool: 如果成功删除，返回 True，如果会话不存在，返回 False。
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Cleared session: {session_id}")
            return True
        return False

# 创建一个全局单例
llm_service = LLMService()