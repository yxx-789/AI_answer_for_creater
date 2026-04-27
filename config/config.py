"""
AI客服运营平台 - 配置文件
"""
import os
from pathlib import Path

# 动态获取项目根目录（重点修改了这一行！兼容本地和云端）
# __file__ 指向当前 config.py 文件，向上退两级（.parent.parent）刚好是项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent

# 平台配置
PLATFORM_NAME = "AI客服运营平台"
VERSION = "2.0.0"

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR}/data/platform.db")

# 数据目录（基于动态根目录）
SCENARIOS_DIR = ROOT_DIR / "data" / "scenarios"
KNOWLEDGE_DIR = ROOT_DIR / "data" / "knowledge"
TRACES_DIR = ROOT_DIR / "data" / "traces"
BAD_CASES_DIR = ROOT_DIR / "data" / "bad_cases"

# 核心引擎目录
CORE_DIR = ROOT_DIR / "core"
CODE_FUNCTIONS_DIR = ROOT_DIR / "code_functions"

# Harness 目录
HARNESS_DIR = ROOT_DIR / "harness"

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 默认场景
DEFAULT_SCENARIO = "bailing/main_flow.yml"

# 分页配置
PAGE_SIZE = 20

# 会话状态键
class SessionKeys:
    CURRENT_SCENARIO = "current_scenario"
    CHAT_HISTORY = "chat_history"
    TRACE_DATA = "trace_data"
    USER = "user"

# 初始化数据目录
def init_directories():
    """初始化所有数据目录"""
    for dir_path in [SCENARIOS_DIR, KNOWLEDGE_DIR, TRACES_DIR, BAD_CASES_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

# 自动初始化
init_directories()