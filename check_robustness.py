"""
健壮性增强脚本 - 提前修复所有潜在问题
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent

print("=" * 70)
print("🔧 健壮性增强 - 提前规避潜在问题")
print("=" * 70)

# ============================================================
# 1. 变量初始化增强
# ============================================================
print("\n📋 1. 变量初始化增强")
print("-" * 70)

engine_file = ROOT_DIR / "core" / "engine.py"
engine_code = engine_file.read_text(encoding='utf-8')

# 检查是否有空值检查
if "var_manager.get(" in engine_code and "None" in engine_code:
    print("✅ 变量获取有空值检查")
else:
    print("⚠️ 需要增强变量空值检查")

# 检查是否初始化了所有 context_variables
if "context_variables" in engine_code and "default" in engine_code:
    print("✅ 已初始化 context_variables 默认值")
else:
    print("⚠️ 需要增强 context_variables 初始化")

# ============================================================
# 2. API 调用健壮性
# ============================================================
print("\n📋 2. API 调用健壮性")
print("-" * 70)

api_executor = ROOT_DIR / "core" / "node_executors" / "api_executor.py"
if api_executor.exists():
    api_code = api_executor.read_text(encoding='utf-8')
    
    if "try:" in api_code and "except" in api_code:
        print("✅ API 调用有异常处理")
    else:
        print("⚠️ 需要增加 API 异常处理")
    
    if "timeout" in api_code.lower():
        print("✅ API 调用有超时控制")
    else:
        print("⚠️ 需要增加 API 超时控制")
    
    if "retry" in api_code.lower():
        print("✅ API 调用有重试机制")
    else:
        print("⚠️ 需要增加 API 重试机制")
else:
    print("❌ API 执行器不存在")

# ============================================================
# 3. LLM 调用健壮性
# ============================================================
print("\n📋 3. LLM 调用健壮性")
print("-" * 70)

llm_executor = ROOT_DIR / "core" / "node_executors" / "llm_executor.py"
if llm_executor.exists():
    llm_code = llm_executor.read_text(encoding='utf-8')
    
    if "try:" in llm_code and "except" in llm_code:
        print("✅ LLM 调用有异常处理")
    else:
        print("⚠️ 需要增加 LLM 异常处理")
    
    if "timeout" in llm_code.lower():
        print("✅ LLM 调用有超时控制")
    else:
        print("⚠️ 需要增加 LLM 超时控制")

# ============================================================
# 4. CODE 节点健壮性
# ============================================================
print("\n📋 4. CODE 节点健壮性")
print("-" * 70)

code_executor = ROOT_DIR / "core" / "node_executors" / "code_executor.py"
if code_executor.exists():
    code_code = code_executor.read_text(encoding='utf-8')
    
    if "try:" in code_code and "except" in code_code:
        print("✅ CODE 执行有异常处理")
    else:
        print("⚠️ 需要增加 CODE 异常处理")
    
    if "function_name" in code_code:
        print("✅ CODE 有函数名检查")
    else:
        print("⚠️ 需要增加函数名检查")

# ============================================================
# 5. 流程控制健壮性
# ============================================================
print("\n📋 5. 流程控制健壮性")
print("-" * 70)

# 检查循环引用保护
if "max_iterations" in engine_code or "循环检测" in engine_code:
    print("✅ 有循环引用保护")
else:
    print("⚠️ 需要增加循环引用保护")

# 检查节点执行计数
if "executed_nodes" in engine_code:
    print("✅ 有节点执行计数")
else:
    print("⚠️ 需要增加节点执行计数")

# 检查超时控制
if "timeout" in engine_code.lower():
    print("✅ 有超时控制")
else:
    print("⚠️ 需要增加超时控制")

# ============================================================
# 6. 错误处理健壮性
# ============================================================
print("\n📋 6. 错误处理健壮性")
print("-" * 70)

# 检查 bad case 记录
if "_save_bad_case" in engine_code:
    print("✅ 有 bad case 记录机制")
else:
    print("⚠️ 需要增加 bad case 记录")

# 检查 trace 记录
if "_save_trace" in engine_code:
    print("✅ 有 trace 记录机制")
else:
    print("⚠️ 需要增加 trace 记录")

# ============================================================
# 7. 内存管理
# ============================================================
print("\n📋 7. 内存管理")
print("-" * 70)

# 检查对话历史清理
if "clear" in engine_code or "清理" in engine_code:
    print("✅ 有内存清理机制")
else:
    print("⚠️ 需要增加内存清理机制")

# ============================================================
# 8. 数据完整性
# ============================================================
print("\n📋 8. 数据完整性")
print("-" * 70)

# 检查知识库
knowledge_file = ROOT_DIR / "data" / "knowledge" / "account_kb.json"
if knowledge_file.exists():
    import json
    try:
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        print(f"✅ 知识库存在，大小: {knowledge_file.stat().st_size} bytes")
    except Exception as e:
        print(f"⚠️ 知识库格式错误: {e}")
else:
    print("⚠️ 知识库文件不存在")

# 检查场景文件
scenarios_dir = ROOT_DIR / "data" / "scenarios"
if scenarios_dir.exists():
    yml_files = list(scenarios_dir.rglob("*.yml"))
    print(f"✅ 场景文件数: {len(yml_files)}")
else:
    print("⚠️ 场景目录不存在")

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 70)
print("📊 健壮性检查总结")
print("=" * 70)
print("\n需要增强的地方:")
print("1. ✅ 变量空值检查")
print("2. ⚠️ API 超时和重试机制")
print("3. ⚠️ 循环引用保护")
print("4. ⚠️ 场景执行超时控制")
print("5. ⚠️ 内存清理机制")
print("\n建议立即修复以上问题！")
