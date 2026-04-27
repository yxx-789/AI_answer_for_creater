# 模型配置文件

# 可用模型列表
MODELS = [
    # ── 阿里 Qwen3.5 系列（2个）──
    "qwen3.5-35b-a3b",
    "qwen3.5-27b",

    # ── 阿里 Qwen3-VL 视觉系列（2个）──
    "qwen3-vl-30b-a3b-thinking",
    "qwen3-vl-32b-thinking",

    # ── 阿里 Qwen3 系列（2个）──
    "qwen3-30b-a3b-thinking-2507",
    "qwen3-32b",

    # ── 百度 ERNIE 系列（2个）──
    "ernie-4.5-vl-28b-a3b",
    "ernie-5.0",

    # ── 其他模型 ──
    "glm-5.1",  # 智谱 GLM-5.1
    "qwen3.5-397b-a17b",  # 阿里 Qwen3.5-397B 旗舰
    "deepseek-v3.2",  # DeepSeek-V3.2
]

# 默认模型
DEFAULT_MODEL = "deepseek-v3.2"

# 模型分组（用于UI展示）
MODEL_GROUPS = {
    "Qwen3.5 系列": [
        "qwen3.5-35b-a3b",
        "qwen3.5-27b",
        "qwen3.5-397b-a17b",
    ],
    "Qwen3-VL 视觉": [
        "qwen3-vl-30b-a3b-thinking",
        "qwen3-vl-32b-thinking",
    ],
    "Qwen3 系列": [
        "qwen3-30b-a3b-thinking-2507",
        "qwen3-32b",
    ],
    "ERNIE 系列": [
        "ernie-4.5-vl-28b-a3b",
        "ernie-5.0",
    ],
    "其他": [
        "glm-5.1",
        "deepseek-v3.2",
    ],
}

# 模型推荐场景
MODEL_RECOMMENDATIONS = {
    "qwen3.5-35b-a3b": "均衡性能，适合一般对话",
    "qwen3.5-27b": "快速响应，适合高频对话",
    "qwen3.5-397b-a17b": "旗舰模型，最强性能",
    "deepseek-v3.2": "推荐模型，综合能力强",
    "ernie-5.0": "百度旗舰，中文理解优秀",
    "glm-5.1": "智谱旗舰，适合知识问答",
}
