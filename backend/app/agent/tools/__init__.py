# 导入并注册所有工具
from .pic_simulation import PICSimulation
from .kcat_predict import KcatPredict

# 工具会通过 @register_tool 装饰器自动注册到 qwen-agent 系统中
__all__ = ['PICSimulation', 'KcatPredict']
