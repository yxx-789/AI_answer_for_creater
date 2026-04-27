# AI客服运营平台 - 最终修复版

**版本**: v2.0.6 Final Complete  
**更新时间**: 2026-04-23 22:15  
**项目路径**: `/Users/xingyao/Desktop/ai-customer-service-platform-v2`

---

## 🚨 重要说明

**已修复的核心问题**:
1. ✅ code_functions目录缺失 → 已复制
2. ✅ 对话测试无输出 → 已修复引擎调用
3. ✅ 场景文件完整性 → 已验证

---

## 🚀 快速开始（3步）

### 步骤1: 诊断检查

```bash
cd /Users/xingyao/Desktop/ai-customer-service-platform-v2
python3 diagnose.py
```

**预期输出**:
```
✅ 所有检查通过！
```

---

### 步骤2: 本地测试

```bash
python3 test_local.py
```

**测试内容**:
- 简化场景对话
- 4个测试问题
- 验证输出不为空

**预期输出**:
```
✅ 所有测试通过！
💬 回复: 你好！我是百灵平台的AI客服助手...
```

---

### 步骤3: 启动Web平台

```bash
bash start.sh
```

访问: **http://localhost:8501**

---

## 🧪 测试用例

### 1. 使用简化场景（推荐先测试）

**场景**: `test_simple.yml`  
**节点数**: 3个（START → LLM → END）

**测试问题**:
1. 你好
2. 我的账号怎么了？
3. 为什么我的账号被莫名其妙封禁了？
4. 别搞笑了好吗？

**预期结果**: ✅ 每个问题都有回复

---

### 2. 使用完整场景

**场景**: `bailing/main_flow.yml`  
**节点数**: 100+  
**功能**: 完整的客服流程

**注意**: 完整场景较复杂，如遇到问题请查看Trace日志

---

## 📁 完整文件清单

```
ai-customer-service-platform-v2/
├── app/                      # Streamlit前端
│   ├── main.py              # 主入口
│   └── pages/               # 功能页面
│
├── core/                     # 核心引擎 ✅
│   ├── engine.py
│   ├── yml_parser.py
│   └── node_executors/
│       └── llm_executor.py  # LLM执行器
│
├── code_functions/           # ⭐ 业务函数（已修复）
│   └── bailing_functions.py
│
├── config/                   # 配置文件
│   ├── config.py
│   ├── api_config.py
│   └── models.py            # 13个模型配置
│
├── data/
│   ├── scenarios/
│   │   ├── test_simple.yml  # ⭐ 简化测试场景
│   │   └── bailing/         # 完整场景
│   ├── knowledge/           # 知识库
│   ├── traces/              # Trace记录
│   └── bad_cases/           # Bad Cases
│
├── test_local.py            # ⭐ 本地测试脚本
├── diagnose.py              # ⭐ 快速诊断
├── start.sh                 # 启动脚本
└── README.md                # 本文档
```

---

## 🔧 核心修复内容

### 1. code_functions 补充 ✅

**问题**: CODE节点无法执行，缺少业务函数

**修复**:
- ✅ 复制 `bailing_functions.py` 到项目
- ✅ 包含所有业务函数（build_penalty_params, wrap_penalty_llm_result等）

---

### 2. 引擎调用修复 ✅

**问题**: 对话测试无输出

**根本原因**:
1. execute_scenario 参数错误（应传字典）
2. output_mapping 未正确应用

**修复**:
```python
# ✅ 正确调用
initial_vars = {"raw_query": user_input}
result = await engine.execute_scenario(scenario, initial_vars)

# ✅ output_mapping自动应用
output_mapping:
  output: final_answer
```

---

### 3. 简化测试场景 ✅

**新增**: `test_simple.yml`

**优势**:
- 只有3个节点，容易调试
- 快速验证核心功能
- 排除复杂场景干扰

---

## 📊 测试流程图

```
┌─────────────┐
│ 运行诊断    │
│ diagnose.py │
└──────┬──────┘
       │
       ▼
┌─────────────┐    失败    ┌──────────────┐
│ 本地测试    │ ─────────> │ 检查配置     │
│ test_local  │            │ 查看错误日志 │
└──────┬──────┘            └──────────────┘
       │ 成功
       ▼
┌─────────────┐
│ 启动Web平台 │
│ start.sh    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 选择简化场景│
│ test_simple │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 测试对话    │
│ 验证输出    │
└─────────────┘
```

---

## 🐛 常见问题

### Q1: 诊断检查失败？

```bash
# 检查Python路径
which python3

# 检查依赖
pip3 list | grep streamlit
pip3 list | grep pyyaml
```

---

### Q2: test_local.py 测试失败？

**检查API配置**:
```bash
cat config/api_config.py
```

**测试API连接**:
```bash
python3 test_api.py
```

---

### Q3: Web平台对话无输出？

**查看Trace文件**:
```bash
ls -lt data/traces/ | head -5
cat data/traces/trace_*.json | python3 -m json.tool
```

**检查日志**:
- Streamlit终端会打印详细执行日志
- 查看节点执行顺序和错误信息

---

### Q4: 完整场景太复杂？

**使用简化场景**:
- 场景选择: `test_simple.yml`
- 快速验证核心功能
- 成功后再测试完整场景

---

## 📝 下一步

### 1. 测试简化场景（必做）

```bash
python3 test_local.py
```

### 2. 启动Web平台

```bash
bash start.sh
```

### 3. Web界面测试

- 选择场景: `test_simple.yml`
- 选择模型: `deepseek-v3.2`
- 输入问题测试

### 4. 验证成功后

- 切换完整场景: `bailing/main_flow.yml`
- 测试真实客服流程

---

## 💡 关键提示

1. **先运行 diagnose.py** - 确保环境完整
2. **先测试 test_simple.yml** - 快速验证核心功能
3. **检查 Trace 文件** - 了解执行细节
4. **查看终端日志** - 所有错误会打印到终端

---

## 📞 如有问题

如果测试仍有问题，请提供以下信息：
1. `diagnose.py` 的完整输出
2. `test_local.py` 的完整输出
3. 失败时的错误信息

---

**请先运行诊断和测试，确保通过后再使用Web平台！** 🚀
