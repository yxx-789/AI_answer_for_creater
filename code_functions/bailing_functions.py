# -*- coding: utf-8 -*-
"""
百灵AI客服系统 - CODE节点函数库（增强版）

说明：
1. 保留原有函数能力，不阉割。
2. 修复 talk_context / penalty_context 解析兼容性问题。
3. 新增“实体抽取 + 实体融合 + 槽位完整性判断”能力。
4. 适配当前百灵主流程的 CODE 节点调用方式。
"""

from typing import Dict, Any, List
import json
import re
from collections import Counter
from datetime import datetime


# ============================================================
# 内部工具函数（新增，供本文件内部复用）
# ============================================================

def _safe_int(value: Any, default: int = 0) -> int:
    """
    安全转 int。
    例如：
    - "1" -> 1
    - None -> default
    - 非法值 -> default
    """
    try:
        return int(value)
    except Exception:
        return default


def _safe_json_loads(text: Any, default: Any):
    """
    安全解析 JSON。
    - text 为空时返回 default
    - 解析失败时返回 default
    """
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _normalize_text(text: Any) -> str:
    """
    对输入文本做轻量归一化：
    - 转字符串
    - strip
    - 去除多余空白
    """
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", "", text)
    return text


def _extract_intention_id(item: Any) -> str:
    """
    从 talk_context 的单个元素中抽取意图 ID。
    兼容两种格式：
    1. 老格式：["1", "2", "-1"]
    2. 新格式：[{"intentionId":"1", ...}, {"intentionId":"2", ...}]
    """
    if isinstance(item, dict):
        return str(item.get("intentionId", ""))
    return str(item)


# ============================================================
# 基础工具（4个）
# ============================================================

def passthrough(value: Any = None) -> Dict[str, Any]:
    """
    透传函数。
    常用于简单把输入值透传给后续变量。
    """
    return {"value": value}


def barrier_noop() -> Dict[str, Any]:
    """
    BARRIER 节点空操作。
    """
    return {}


def noop() -> Dict[str, Any]:
    """
    通用空操作函数。
    """
    return {}


def passthrough_to_emotion() -> Dict[str, Any]:
    """
    高危分类为 -1 时回退到情绪判断。
    当前仅作为占位空函数。
    """
    return {}


# ============================================================
# 预处理（原有8个 + 新增3个）
# ============================================================

def merge_query(img_query: str = "", no_img_query: str = "") -> Dict[str, Any]:
    """
    合并图片 query 和文字 query。
    优先使用图片识别后的 query，否则使用纯文本 query。
    """
    img_query = img_query or ""
    no_img_query = no_img_query or ""
    merged = img_query or no_img_query or ""
    return {"merged": merged}


def merge_user_info(
    condition_desc_list: List[str] = None,
    variable_data: Dict = None
) -> Dict[str, Any]:
    """
    合并 API 返回的条件描述和变量信息。

    Args:
        condition_desc_list: 条件描述列表
        variable_data: 变量数据字典

    Returns:
        {
            "user_list": [
                "非鼓励层",
                "工时内",
                "用户账号状态:暂未发现异常",
                "未审核数:0"
            ]
        }
    """
    user_list = []

    if condition_desc_list:
        user_list.extend([str(x) for x in condition_desc_list if x is not None])

    variable_data = variable_data or {}

    # 用户账号状态
    if variable_data.get("userAccountStatusDesc") is not None and variable_data.get("userAccountStatusDesc") != "":
        user_list.append(f"用户账号状态:{variable_data['userAccountStatusDesc']}")

    # 未审核数：即使是 0，也建议保留，方便上下文使用
    if "unapprovedCount" in variable_data:
        user_list.append(f"未审核数:{variable_data.get('unapprovedCount', 0)}")

    return {"user_list": user_list}


def parse_talk_context(talk_context_str: str = "[]") -> Dict[str, Any]:
    """
    解析 talk_context JSON 字符串。

    兼容两种格式：
    1. 老格式：["1", "1", "2"]
    2. 新格式：
       [
         {"intentionId":"1","secondaryIntentionId":"8","classificationId":"-1","timestamp":"..."},
         {"intentionId":"2","secondaryIntentionId":null,"classificationId":"","timestamp":"..."}
       ]

    Returns:
        {
            "count_map": {"1": 4, "2": 1},
            "last_id": "1",
            "continuity_count": 2,
            "parsed_array": [...]
        }
    """
    talk_context = _safe_json_loads(talk_context_str, [])

    # 兜底：如果不是 list，则强制置空
    if not isinstance(talk_context, list):
        talk_context = []

    if not talk_context:
        return {
            "count_map": {},
            "last_id": "",
            "continuity_count": 0,
            "parsed_array": []
        }

    # 统一抽取 intentionId 序列
    intention_ids = []
    for item in talk_context:
        intention_id = _extract_intention_id(item)
        if intention_id != "":
            intention_ids.append(intention_id)

    if not intention_ids:
        return {
            "count_map": {},
            "last_id": "",
            "continuity_count": 0,
            "parsed_array": talk_context
        }

    count_map = dict(Counter(intention_ids))
    last_id = intention_ids[-1] if intention_ids else ""

    continuity_count = 0
    for i in range(len(intention_ids) - 1, -1, -1):
        if intention_ids[i] == last_id:
            continuity_count += 1
        else:
            break

    return {
        "count_map": {str(k): v for k, v in count_map.items()},
        "last_id": str(last_id),
        "continuity_count": continuity_count,
        "parsed_array": talk_context
    }


def parse_transfer_stats(
    count_map: Dict[str, int] = None,
    talk_context_parsed: List = None
) -> Dict[str, Any]:
    """
    统计意图 ID = 2（转人工）的累计和最近连续次数。

    兼容 talk_context_parsed 为字符串数组 / 对象数组 两种格式。

    Returns:
        {"total_count": 1, "recent_count": 0}
    """
    count_map = count_map or {}
    talk_context_parsed = talk_context_parsed or []

    total_count = count_map.get("2", 0)

    recent_count = 0
    for i in range(len(talk_context_parsed) - 1, -1, -1):
        intention_id = _extract_intention_id(talk_context_parsed[i])
        if intention_id == "2":
            recent_count += 1
        else:
            break

    return {"total_count": total_count, "recent_count": recent_count}


def parse_unparsed_stats(
    count_map: Dict[str, int] = None,
    talk_context_parsed: List = None
) -> Dict[str, Any]:
    """
    统计意图 ID = -1（未识别）的累计和最近连续次数。

    注意：
    这里仍按主意图 intentionId == -1 统计。
    如果你未来想统计 classificationId == -1 的“未命中知识”，
    建议单独再加一个解析函数，不要混在这里。

    Returns:
        {"total_count": 2, "recent_count": 1}
    """
    count_map = count_map or {}
    talk_context_parsed = talk_context_parsed or []

    total_count = count_map.get("-1", 0)

    recent_count = 0
    for i in range(len(talk_context_parsed) - 1, -1, -1):
        intention_id = _extract_intention_id(talk_context_parsed[i])
        if intention_id == "-1":
            recent_count += 1
        else:
            break

    return {"total_count": total_count, "recent_count": recent_count}


def parse_penalty_context(
    penalty_context_str: str = "{}",
    raw_query: str = ""
) -> Dict[str, Any]:
    """
    解析账号处罚上下文。

    Returns:
        {
            "confirm_liveness_detection": 0,
            "has_ban": 0,
            "reject_data": ""
        }
    """
    penalty_context = _safe_json_loads(penalty_context_str, {})
    if not isinstance(penalty_context, dict):
        penalty_context = {}

    return {
        "confirm_liveness_detection": _safe_int(penalty_context.get("confirm_liveness_detection", 0), 0),
        "has_ban": _safe_int(penalty_context.get("has_ban", 0), 0),
        "reject_data": penalty_context.get("reject_data", "") or ""
    }


def generate_extra_prompt(user_list: List[str] = None) -> Dict[str, Any]:
    """
    生成额外 prompt。
    当前逻辑：
    - 命中“非工时”时，给后续模型一个轻量补充提示
    """
    if not user_list:
        return {"extra_prompt": ""}

    if any("非工时" in str(item) for item in user_list):
        return {"extra_prompt": "现在处于非工作时间。"}

    return {"extra_prompt": ""}


def fill_query_with_info(
    rewrite_query: str = "",
    user_list: List[str] = None,
    semantic_complete: str = "1",
    extra_prompt: str = ""
) -> Dict[str, Any]:
    """
    生成两个版本的 query：
    1. query_with_info：拼接用户上下文信息
    2. query_without_info：仅保留纯用户问题

    Returns:
        {
            "query_with_info": "非鼓励层 工时内 我的号被封了",
            "query_without_info": "我的号被封了"
        }
    """
    if semantic_complete == "0":
        return {
            "query_with_info": rewrite_query,
            "query_without_info": rewrite_query
        }

    user_info = " ".join([str(item) for item in (user_list or []) if item])
    query_with_info = f"{user_info} {rewrite_query} {extra_prompt}".strip()

    return {
        "query_with_info": query_with_info,
        "query_without_info": rewrite_query
    }


# ============================================================
# 新增：实体抽取 / 实体融合 / 槽位判断（3个）
# ============================================================

def extract_query_entities(
    raw_query: str = "",
    final_query: str = ""
) -> Dict[str, Any]:
    """
    从用户 query 中抽取轻量业务实体。

    设计目标：
    1. 不依赖 LLM，优先用规则和关键词做首层判断
    2. 先把“辱骂 / 闲聊 / 业务”分开
    3. 识别业务域 domain、问题类型 issue_type、场景 scene 等
    4. 为后续“槽位完整性判断”提供结构化输入

    Args:
        raw_query: 原始 query
        final_query: 若流程中已合并/改写，可优先传 final_query

    Returns:
        {
            "query_entities": "<json string>",
            "chat_type": "business/smalltalk/insult/unknown",
            "domain": "account/revenue/content_review/publish/...",
            "issue_type": "...",
            "intent_action": "...",
            "is_vague_business": 0/1
        }
    """
    source_query = final_query or raw_query or ""
    q = _normalize_text(source_query)

    insult_words = [
        "傻瓜", "笨蛋", "白痴", "蠢", "废物", "垃圾", "傻逼", "脑残", "智障"
    ]

    smalltalk_words = [
        "在吗", "你好", "您好", "哈喽", "hi", "hello",
        "在干嘛", "你是谁", "有人吗", "忙吗", "干嘛呢", "睡了吗"
    ]

    question_words = ["怎么", "怎么办", "如何", "为什么", "咋办", "是否", "能不能", "可以吗"]
    time_words = ["今天", "刚刚", "刚才", "昨天", "一直", "最近", "这几天"]

    matched_keywords = []

    def hit_any(words: List[str]) -> bool:
        for w in words:
            if w in q:
                matched_keywords.append(w)
                return True
        return False

    is_insult = 1 if hit_any(insult_words) else 0
    is_smalltalk = 1 if hit_any(smalltalk_words) else 0
    has_question_word = 1 if any(w in q for w in question_words) else 0

    time_expr = ""
    for w in time_words:
        if w in q:
            time_expr = w
            matched_keywords.append(w)
            break

    # 默认值
    chat_type = "unknown"
    domain = ""
    intent_action = ""
    issue_type = ""
    scene = ""
    error_message = ""
    content_type = ""
    is_vague_business = 0
    confidence = 0.3

    # 1) 先判辱骂 / 闲聊
    if is_insult:
        chat_type = "insult"
        confidence = 0.98

    elif is_smalltalk:
        chat_type = "smalltalk"
        confidence = 0.95

    else:
        # 2) 业务域和问题类型抽取

        # ------------------------
        # account 账号类
        # ------------------------
        if any(k in q for k in ["账号", "帐号", "登录", "登陆", "实名", "认证", "封禁", "封号", "申诉"]):
            domain = "account"
            chat_type = "business"
            confidence = max(confidence, 0.75)

        if "登录" in q or "登陆" in q:
            intent_action = "login"
            scene = "login"
            matched_keywords.append("登录")
            if any(k in q for k in ["异常", "失败", "不了", "不上", "无法", "登不上", "登不了"]):
                issue_type = "login_exception"
                confidence = max(confidence, 0.88)

        if any(k in q for k in ["封禁", "封号", "封了", "被封", "禁言", "限制发文", "限制使用", "账号受限"]):
            domain = "account"
            intent_action = "query"
            issue_type = "account_ban"
            confidence = max(confidence, 0.9)
            matched_keywords.extend([k for k in ["封禁", "封号", "被封", "限制使用", "账号受限"] if k in q])

        if any(k in q for k in ["实名", "实名认证", "认证失败", "身份校验", "人脸", "活体"]):
            domain = "account"
            intent_action = "verify"
            issue_type = "realname_verify"
            confidence = max(confidence, 0.88)
            matched_keywords.extend([k for k in ["实名", "实名认证", "认证失败", "人脸", "活体"] if k in q])

        if any(k in q for k in ["找回账号", "账号找回", "找回", "忘记账号"]):
            domain = "account"
            intent_action = "query"
            issue_type = "account_recovery"
            confidence = max(confidence, 0.85)
            matched_keywords.extend([k for k in ["找回账号", "账号找回", "找回", "忘记账号"] if k in q])

        # ------------------------
        # revenue 收益 / 提现类
        # ------------------------
        if any(k in q for k in ["收益", "提现", "打款", "结算", "收入"]):
            domain = "revenue"
            chat_type = "business"
            confidence = max(confidence, 0.75)

        if "提现" in q:
            intent_action = "withdraw"
            scene = "withdraw"
            matched_keywords.append("提现")
            if any(k in q for k in ["失败", "不到账", "未到账", "打款失败", "提现不了", "提不了"]):
                issue_type = "withdraw_fail"
                confidence = max(confidence, 0.9)

        if "收益" in q:
            matched_keywords.append("收益")
            if any(k in q for k in ["下降", "变少", "很低", "为0", "没有"]):
                issue_type = "revenue_drop"
                confidence = max(confidence, 0.82)

        # ------------------------
        # content_review 内容审核类
        # ------------------------
        if any(k in q for k in ["审核", "未通过", "驳回", "下线", "限流", "推荐少", "推荐低"]):
            domain = "content_review"
            chat_type = "business"
            confidence = max(confidence, 0.78)

        if any(k in q for k in ["审核不通过", "未通过", "驳回"]):
            issue_type = "review_reject"
            intent_action = "review"
            scene = "review"
            confidence = max(confidence, 0.9)
            matched_keywords.extend([k for k in ["审核不通过", "未通过", "驳回"] if k in q])

        if any(k in q for k in ["下线", "删除", "限流", "推荐少", "没推荐"]):
            intent_action = "review"
            scene = "review"
            matched_keywords.extend([k for k in ["下线", "删除", "限流", "推荐少", "没推荐"] if k in q])

        # ------------------------
        # publish 发布类
        # ------------------------
        if any(k in q for k in ["发文", "发布", "上传", "发视频", "发文章"]):
            domain = "publish"
            chat_type = "business"
            confidence = max(confidence, 0.76)

        if any(k in q for k in ["发布失败", "发文失败", "上传失败", "不能发布", "发不了"]):
            issue_type = "publish_fail"
            intent_action = "publish"
            scene = "publish"
            confidence = max(confidence, 0.9)
            matched_keywords.extend([k for k in ["发布失败", "发文失败", "上传失败", "不能发布", "发不了"] if k in q])

        # 内容类型
        if any(k in q for k in ["文章", "图文"]):
            content_type = "article"
            matched_keywords.extend([k for k in ["文章", "图文"] if k in q])
        elif "视频" in q:
            content_type = "video"
            matched_keywords.append("视频")
        elif any(k in q for k in ["动态", "帖子"]):
            content_type = "dynamic"
            matched_keywords.extend([k for k in ["动态", "帖子"] if k in q])

        # 错误提示抽取：如“提示账号异常”“报错xxx”
        m = re.search(r"(提示|报错|显示)([^，。！？\n]{1,30})", q)
        if m:
            error_message = m.group(2)
            confidence = max(confidence, 0.88)

        # 3) 业务兜底：如果没有准确抽到具体 domain，但含明显业务词，也先归业务
        if chat_type == "unknown":
            if any(k in q for k in ["账号", "收益", "提现", "审核", "发文", "发布", "视频", "文章"]):
                chat_type = "business"
                confidence = max(confidence, 0.65)

        # 4) 判断是否为“业务方向有了，但信息不足”
        vague_patterns = [
            "出问题了", "有问题", "不对", "异常", "不行", "失败了", "有点问题"
        ]

        if chat_type == "business":
            # domain 已知，但没有 issue_type / error_message
            if domain and not issue_type and not error_message:
                if any(v in q for v in vague_patterns):
                    is_vague_business = 1

                # “账号”“收益”“审核”这种超短词也视为模糊业务
                if len(q) <= 6:
                    is_vague_business = 1

            # 没有 domain 且又非常短，也视为模糊业务
            if not domain and len(q) <= 6:
                is_vague_business = 1

    entity = {
        "raw_query": source_query,
        "normalized_query": q,
        "chat_type": chat_type,
        "domain": domain,
        "intent_action": intent_action,
        "issue_type": issue_type,
        "scene": scene,
        "error_message": error_message,
        "content_type": content_type,
        "time_expr": time_expr,
        "has_question_word": has_question_word,
        "is_insult": is_insult,
        "is_smalltalk": is_smalltalk,
        "is_vague_business": is_vague_business,
        "confidence": confidence,
        "matched_keywords": list(dict.fromkeys(matched_keywords))
    }

    return {
        "query_entities": json.dumps(entity, ensure_ascii=False),
        "chat_type": chat_type,
        "domain": domain,
        "issue_type": issue_type,
        "intent_action": intent_action,
        "is_vague_business": is_vague_business
    }


def merge_entity_context(
    query_entities: str = "{}",
    user_list: List[str] = None,
    has_ban: int = 0,
    confirm_liveness_detection: int = 0,
    reject_data: str = "",
    variable_data: Dict = None
) -> Dict[str, Any]:
    """
    融合 query 实体与用户已有系统侧信息。

    作用：
    1. 把用户说的话里抽到的实体，和系统已知账号状态做统一上下文
    2. 为后续槽位判断提供更丰富的实体背景

    Args:
        query_entities: extract_query_entities 输出的 JSON 字符串
        user_list: 用户信息列表，如 ["非鼓励层","工时内","用户账号状态:暂未发现异常","未审核数:0"]
        has_ban: 是否有封禁
        confirm_liveness_detection: 活体校验状态
        reject_data: 处罚驳回数据
        variable_data: 变量数据字典（如果流程里有）

    Returns:
        {
            "entity_context": "<json string>",
            "resolved_domain": "account"
        }
    """
    query_entities_obj = _safe_json_loads(query_entities, {})
    user_list = user_list or []
    variable_data = variable_data or {}

    if not isinstance(user_list, list):
        user_list = [str(user_list)]

    account_status_desc = ""
    black_reason = ""
    unapproved_count = 0
    is_blacklist = 0

    # 从 user_list 里做粗解析
    for item in user_list:
        s = str(item)
        if s.startswith("用户账号状态:"):
            account_status_desc = s.replace("用户账号状态:", "", 1)
        elif s.startswith("未审核数:"):
            try:
                unapproved_count = int(s.replace("未审核数:", "", 1))
            except Exception:
                unapproved_count = 0
        elif "黑名单" in s and "非黑名单" not in s:
            is_blacklist = 1

    # 从 variable_data 兜底补充
    if isinstance(variable_data, dict):
        account_status_desc = variable_data.get("userAccountStatusDesc", account_status_desc) or account_status_desc
        black_reason = variable_data.get("blackReason", black_reason) or black_reason
        try:
            unapproved_count = int(variable_data.get("unapprovedCount", unapproved_count))
        except Exception:
            pass

    if black_reason:
        is_blacklist = 1

    resolved_domain = query_entities_obj.get("domain", "") or ""

    # 如果 query 没识别出 domain，但系统侧处罚特征明显，可保守推断为 account
    if not resolved_domain:
        if _safe_int(has_ban, 0) == 1 or _safe_int(confirm_liveness_detection, 0) == 1 or black_reason:
            resolved_domain = "account"

    entity_context = {
        "query_entities": query_entities_obj,
        "user_entities": {
            "user_tags": user_list,
            "account_status_desc": account_status_desc,
            "black_reason": black_reason,
            "has_ban": _safe_int(has_ban, 0),
            "confirm_liveness_detection": _safe_int(confirm_liveness_detection, 0),
            "unapproved_count": unapproved_count,
            "is_blacklist": is_blacklist,
            "reject_data": reject_data or ""
        },
        "resolved_domain": resolved_domain
    }

    return {
        "entity_context": json.dumps(entity_context, ensure_ascii=False),
        "resolved_domain": resolved_domain
    }


def check_slot_completeness(entity_context: str = "{}") -> Dict[str, Any]:
    """
    检查槽位是否完整，并决定下一步路由策略。

    核心思想：
    - 辱骂 / 闲聊：直接短路回复，不进业务主链
    - 业务问题但信息不足：先定向澄清
    - 业务问题且槽位足够：继续原主流程

    Returns:
        {
            "slot_complete": 0/1,
            "resolved_domain": "account",
            "clarify_type": "account_issue_type",
            "missing_slots": '["issue_type"]',
            "reason": "...",
            "suggested_reply": "...",
            "route_type": "direct_reply / clarify / continue",
            "slot_check_result": "{...}"
        }
    """
    entity_context_obj = _safe_json_loads(entity_context, {})
    query_entities = entity_context_obj.get("query_entities", {}) or {}
    user_entities = entity_context_obj.get("user_entities", {}) or {}

    chat_type = query_entities.get("chat_type", "unknown")
    domain = entity_context_obj.get("resolved_domain", "") or query_entities.get("domain", "") or ""
    issue_type = query_entities.get("issue_type", "") or ""
    error_message = query_entities.get("error_message", "") or ""
    scene = query_entities.get("scene", "") or ""
    is_vague_business = _safe_int(query_entities.get("is_vague_business", 0), 0)

    missing_slots = []
    clarify_type = ""
    slot_complete = 1
    route_type = "continue"
    reason = ""
    suggested_reply = ""

    # 1) 非业务：直接回复
    if chat_type == "insult":
        slot_complete = 0
        route_type = "direct_reply"
        clarify_type = "insult_reply"
        reason = "辱骂/挑衅输入"
        suggested_reply = (
            "创作者大人，小百是来帮您解决问题的～"
            "如果您有账号、发文、审核、收益等问题，可以直接告诉我具体情况。"
        )

    elif chat_type == "smalltalk":
        slot_complete = 0
        route_type = "direct_reply"
        clarify_type = "smalltalk_reply"
        reason = "闲聊输入"
        suggested_reply = (
            "创作者大人，小百主要帮助处理百家号相关问题哦，"
            "比如发文、审核、收益、账号异常等。您可以直接告诉我具体问题～"
        )

    # 2) 业务但 domain 不清晰：先做通用澄清
    elif chat_type == "business" and not domain:
        slot_complete = 0
        route_type = "clarify"
        clarify_type = "general_business"
        missing_slots = ["domain"]
        reason = "业务问题但未识别出明确业务域"
        suggested_reply = (
            "创作者大人，请问您遇到的是哪类问题呢？\n"
            "1. 账号登录/认证\n"
            "2. 发文/发布失败\n"
            "3. 审核不通过/内容下线\n"
            "4. 收益/提现异常\n"
            "您也可以直接补充页面提示或报错信息。"
        )

    # 3) 按不同 domain 判断槽位够不够
    elif chat_type == "business":
        if domain == "account":
            # 账号类问题：至少要有 issue_type / error_message / login scene 之一
            if not issue_type and not error_message and scene not in ["login"]:
                slot_complete = 0
                route_type = "clarify"
                clarify_type = "account_issue_type"
                missing_slots = ["issue_type"]
                reason = "账号类问题缺少具体问题类型"
                suggested_reply = (
                    "创作者大人，请问您的账号具体遇到哪类问题呢？\n"
                    "1. 登录异常\n"
                    "2. 账号被限制/封禁\n"
                    "3. 实名认证问题\n"
                    "4. 账号信息或找回问题\n"
                    "也可以把页面提示发给小百，我来帮您判断。"
                )

        elif domain == "revenue":
            # 收益类问题：至少要有具体类型，如提现失败 / 收益下降 / 错误提示
            if not issue_type and not error_message and scene not in ["withdraw"]:
                slot_complete = 0
                route_type = "clarify"
                clarify_type = "revenue_issue_type"
                missing_slots = ["issue_type"]
                reason = "收益类问题缺少具体问题类型"
                suggested_reply = (
                    "创作者大人，请问您遇到的是哪类收益问题呢？\n"
                    "1. 提现失败/未到账\n"
                    "2. 收益下降\n"
                    "3. 收益为0\n"
                    "4. 结算或打款异常\n"
                    "也可以把页面提示发给小百。"
                )

        elif domain == "content_review":
            # 审核类问题：至少知道“审核不通过 / 下线 / 限流 / 违规提示”等之一
            if not issue_type and not error_message:
                slot_complete = 0
                route_type = "clarify"
                clarify_type = "content_review_issue_type"
                missing_slots = ["issue_type"]
                reason = "内容审核类问题缺少具体结果描述"
                suggested_reply = (
                    "创作者大人，请问内容具体遇到什么情况呢？\n"
                    "1. 审核不通过\n"
                    "2. 内容被下线\n"
                    "3. 推荐/流量异常\n"
                    "4. 提示违规\n"
                    "您也可以直接发失败提示或违规原因给小百。"
                )

        elif domain == "publish":
            # 发布类问题：至少知道“发布失败 / 上传失败 / 页面报错”等之一
            if not issue_type and not error_message:
                slot_complete = 0
                route_type = "clarify"
                clarify_type = "publish_issue_type"
                missing_slots = ["issue_type"]
                reason = "发布类问题缺少具体失败类型"
                suggested_reply = (
                    "创作者大人，请问您发文时具体遇到什么情况呢？\n"
                    "1. 发布失败\n"
                    "2. 上传失败\n"
                    "3. 无法提交\n"
                    "4. 页面提示异常\n"
                    "也可以把报错提示发给小百，我来帮您判断。"
                )

        # 通用模糊业务兜底
        if slot_complete == 1 and is_vague_business == 1 and not issue_type and not error_message:
            slot_complete = 0
            route_type = "clarify"
            clarify_type = f"{domain or 'general'}_vague_business"
            missing_slots = ["issue_type"]
            reason = "业务方向已知但信息不足"
            suggested_reply = (
                "创作者大人，小百还需要更具体一点的信息才能帮您判断哦～"
                "您可以补充一下具体场景、页面提示，或者说明是登录、审核、发文、收益中的哪一类问题。"
            )

    # 4) unknown 兜底
    else:
        slot_complete = 0
        route_type = "clarify"
        clarify_type = "unknown"
        missing_slots = ["domain"]
        reason = "无法判断输入类型"
        suggested_reply = (
            "创作者大人，小百暂时还没理解您的问题。"
            "您可以直接描述具体场景，例如“文章审核不通过”“账号登录异常”“收益提现失败”。"
        )

    result = {
        "slot_complete": slot_complete,
        "resolved_domain": domain,
        "clarify_type": clarify_type,
        "missing_slots": missing_slots,
        "reason": reason,
        "suggested_reply": suggested_reply,
        "route_type": route_type,
        "query_entities": query_entities,
        "user_entities": user_entities
    }

    return {
        "slot_complete": slot_complete,
        "resolved_domain": domain,
        "clarify_type": clarify_type,
        "missing_slots": json.dumps(missing_slots, ensure_ascii=False),
        "reason": reason,
        "suggested_reply": suggested_reply,
        "route_type": route_type,
        "slot_check_result": json.dumps(result, ensure_ascii=False)
    }


# ============================================================
# 知识库处理（4个）
# ============================================================

def merge_topic_query(rewrite_query: str = "", classification_id: str = "") -> Dict[str, Any]:
    """
    新话题 query 合并。
    当前版本直接返回 rewrite_query。
    """
    return {"merged_query": rewrite_query}


def merge_followup_query(rewrite_query: str = "", classification_id: str = "") -> Dict[str, Any]:
    """
    追问 query 合并。
    当前版本直接返回 rewrite_query。
    """
    return {"merged_query": rewrite_query}


def postprocess_knowledge(
    raw_results: List[Dict] = None,
    rewrite_query: str = "",
    user_list: List[str] = None,
    has_ban: int = 0,
    confirm_liveness_detection: int = 0
) -> Dict[str, Any]:
    """
    知识库后处理（核心 CODE 节点）。

    主要职责：
    1. 规范化知识库结果
    2. 提取链接并做占位替换
    3. 生成供 LLM 使用的知识摘要串
    4. 统计是否前置命中、是否建议快转人工

    Returns:
        {
            "knowledge_list_for_llm": "...",
            "knowledge_raw": "...",
            "link_map": {},
            "question_category_ids": "",
            "fast_transfer": 0,
            "match_success": 0,
            "user_info_list": []
        }
    """
    if raw_results is None:
        raw_results = []

    if user_list is None:
        user_list = []

    knowledge_list = []
    knowledge_raw = []
    link_map = {}
    question_category_ids = []
    fast_transfer = 0
    match_success = 0

    for idx, result in enumerate(raw_results[:5]):  # 最多 5 条
        question = result.get("question", "")
        answer = result.get("answer", "")
        category_id = result.get("category_id", "")
        is_fast_transfer = result.get("fast_transfer", 0)

        # 提取 URL 并替换为占位符，避免 LLM 生成时误处理长链接
        urls = re.findall(r'https?://[^\s]+', answer)
        for url_idx, url in enumerate(urls):
            placeholder = f"[链接{idx}_{url_idx}]"
            answer = answer.replace(url, placeholder)
            link_map[placeholder] = url

        knowledge_item = f"[知识库索引:{idx}]\n问题：{question}\n答案：{answer}"
        knowledge_list.append(knowledge_item)

        knowledge_raw.append({
            "index": idx,
            "question": question,
            "answer": answer,
            "category_id": category_id,
            "fast_transfer": is_fast_transfer
        })

        question_category_ids.append(category_id)

        # 一个非常轻量的前置命中判断
        if question and question.lower() in (rewrite_query or "").lower():
            match_success = 1

        if is_fast_transfer:
            fast_transfer = 1

    return {
        "knowledge_list_for_llm": "\n\n".join(knowledge_list),
        "knowledge_raw": json.dumps(knowledge_raw, ensure_ascii=False),
        "link_map": link_map,
        "question_category_ids": ",".join([str(x) for x in question_category_ids if x != ""]),
        "fast_transfer": fast_transfer,
        "match_success": match_success,
        "user_info_list": user_list
    }


def merge_knowledge_context(
    knowledge_list: str = "",
    user_info_list: List[str] = None,
    rewrite_query: str = "",
    classification_id: str = ""
) -> Dict[str, Any]:
    """
    合并知识库上下文，提供给后续 LLM 生成答案。

    Returns:
        {"context": "..."}
    """
    if user_info_list is None:
        user_info_list = []

    user_info = " ".join([str(item) for item in user_info_list if item])
    context = f"用户信息：{user_info}\n\n知识库内容：\n{knowledge_list}"

    return {"context": context}


# ============================================================
# 后处理（3个）
# ============================================================

def extract_json_and_replace_links(
    gen_result_json: str = "",
    knowledge_raw: str = "[]",
    link_map: Dict = None
) -> Dict[str, Any]:
    """
    从生成结果中提取 JSON，并将链接占位符替换回真实链接。

    Returns:
        {
            "answer": "...",
            "knowledge_indexes": "0,2",
            "question_category_ids": "...",
            "fast_transfer": 0
        }
    """
    if link_map is None:
        link_map = {}

    try:
        result = json.loads(gen_result_json) if gen_result_json else {}
        answer = result.get("answer", "")
        knowledge_indexes = result.get("knowledge_indexes", "")

        # 替换短链接占位符
        for placeholder, url in link_map.items():
            answer = answer.replace(placeholder, url)

        knowledge_raw_list = json.loads(knowledge_raw) if knowledge_raw else []
        question_category_ids = []
        fast_transfer = 0

        if knowledge_indexes:
            indexes = [int(idx.strip()) for idx in knowledge_indexes.split(",") if idx.strip().isdigit()]
            for idx in indexes:
                if idx < len(knowledge_raw_list):
                    item = knowledge_raw_list[idx]
                    question_category_ids.append(item.get("category_id", ""))
                    if item.get("fast_transfer"):
                        fast_transfer = 1

        return {
            "answer": answer,
            "knowledge_indexes": knowledge_indexes,
            "question_category_ids": ",".join([str(x) for x in question_category_ids if x != ""]),
            "fast_transfer": fast_transfer
        }
    except Exception as e:
        print(f"提取JSON失败: {e}")
        return {
            "answer": gen_result_json,
            "knowledge_indexes": "",
            "question_category_ids": "",
            "fast_transfer": 0
        }


def attach_material_card(final_answer: str = "") -> Dict[str, Any]:
    """
    附加物料卡片。
    当前为固定卡片返回。
    """
    return {"card": True, "material_id": "34"}


def build_transfer_params(
    question_category_ids: str = "",
    rewrite_query: str = "",
    user_list: List[str] = None
) -> Dict[str, Any]:
    """
    构建转人工参数。

    Returns:
        {"transfer_flag": True, "params": {...}}
    """
    if user_list is None:
        user_list = []

    params = {
        "question_category_ids": question_category_ids,
        "query": rewrite_query,
        "user_info": user_list,
        "timestamp": datetime.now().isoformat()
    }

    return {"transfer_flag": True, "params": params}


# ============================================================
# 上下文更新（原有4个）
# ============================================================

def update_talk_context(
    talk_context: str = "[]",
    main_intent_id: str = "",
    secondary_intent_id: str = "",
    classification_id: str = ""
) -> Dict[str, Any]:
    """
    更新对话上下文。

    当前使用对象数组格式写入，便于后续统计和调试。

    Returns:
        {"new_talk_context": JSON字符串}
    """
    context_list = _safe_json_loads(talk_context, [])

    if not isinstance(context_list, list):
        context_list = []

    new_entry = {
        "intentionId": main_intent_id,
        "secondaryIntentionId": secondary_intent_id,
        "classificationId": classification_id,
        "timestamp": datetime.now().isoformat()
    }

    # 当前版本把最新一条插到最前面
    context_list.insert(0, new_entry)

    if len(context_list) > 20:
        context_list = context_list[:20]

    return {"new_talk_context": json.dumps(context_list, ensure_ascii=False)}


def update_penalty_context(
    account_penalty_context: str = "{}",
    penalty_type: str = "",
    penalty_reject_data: str = "",
    has_ban: int = 0,
    confirm_liveness_detection: int = 0
) -> Dict[str, Any]:
    """
    更新处罚上下文。

    Returns:
        {"new_penalty_context": JSON字符串}
    """
    penalty_dict = _safe_json_loads(account_penalty_context, {})
    if not isinstance(penalty_dict, dict):
        penalty_dict = {}

    if penalty_type == "feedback":
        penalty_dict["has_ban"] = 1
    elif penalty_type == "liveness_detection":
        penalty_dict["confirm_liveness_detection"] = 2
    elif penalty_type == "manual_reject":
        if penalty_reject_data:
            penalty_dict["reject_data"] = penalty_reject_data

    if has_ban:
        penalty_dict["has_ban"] = has_ban
    if confirm_liveness_detection:
        penalty_dict["confirm_liveness_detection"] = confirm_liveness_detection

    return {"new_penalty_context": json.dumps(penalty_dict, ensure_ascii=False)}


def build_penalty_params(
    raw_query: str = "",
    rewrite_query: str = "",
    user_list: List[str] = None,
    confirm_liveness_detection: int = 0,
    has_ban: int = 0,
    variable_data: Dict = None,
    main_intention_to_human_count: int = 0
) -> Dict[str, Any]:
    """
    构建处罚自动化参数。

    Returns:
        {"json_params": JSON字符串}
    """
    if user_list is None:
        user_list = []
    if variable_data is None:
        variable_data = {}

    params = {
        "raw_query": raw_query,
        "rewrite_query": rewrite_query,
        "user_list": user_list,
        "confirm_liveness_detection": confirm_liveness_detection,
        "has_ban": has_ban,
        "variable_data": variable_data,
        "main_intention_to_human_count": main_intention_to_human_count,
        "timestamp": datetime.now().isoformat()
    }

    return {"json_params": json.dumps(params, ensure_ascii=False)}


def parse_penalty_output(penalty_result: Dict = None) -> Dict[str, Any]:
    """
    解析处罚自动化结果。

    Returns:
        {"message": ..., "type": ..., "data": ..., "reject_data": ...}
    """
    if penalty_result is None:
        penalty_result = {}

    return {
        "message": penalty_result.get("message", ""),
        "type": penalty_result.get("type", ""),
        "data": penalty_result.get("data", ""),
        "reject_data": penalty_result.get("reject_data", "")
    }


def transfer_to_human(user_id: str, conversation_id: str) -> Dict[str, Any]:
    """
    转人工。

    Args:
        user_id: 用户ID
        conversation_id: 会话ID

    Returns:
        {
            "transfer_message": "已为您转接人工客服，请稍候..."
        }
    """
    # TODO: 实际实现应该调用转人工 API
    transfer_message = "已为您转接人工客服，请稍候..."

    return {
        "transfer_message": transfer_message
    }


def wrap_penalty_llm_result(answer: str = "") -> Dict[str, Any]:
    """
    将处罚 LLM 输出包装成统一的 penalty_result 格式。
    """
    return {
        "penalty_result": {
            "message": "success",
            "type": "feedback",
            "data": answer or "创作者大人您好，当前暂未获取到明确处罚详情，建议您查看站内信或违规记录。",
            "reject_data": ""
        }
    }


# ============================================================
# 测试
# ============================================================

if __name__ == '__main__':
    print("=== 百灵AI客服 - CODE函数库测试 ===")

    func_names = [
        name for name in dir()
        if not name.startswith("_") and callable(globals().get(name))
    ]
    print(f"共 {len(func_names)} 个函数")

    # 测试 parse_talk_context（老格式）
    result = parse_talk_context('["1", "1", "2", "1", "1"]')
    print(f"\nparse_talk_context(老格式): {result}")

    # 测试 parse_talk_context（新格式）
    result = parse_talk_context(json.dumps([
        {"intentionId": "1", "secondaryIntentionId": None, "classificationId": "-1", "timestamp": "2026-01-01T10:00:00"},
        {"intentionId": "1", "secondaryIntentionId": None, "classificationId": "-1", "timestamp": "2026-01-01T10:01:00"},
        {"intentionId": "2", "secondaryIntentionId": None, "classificationId": "", "timestamp": "2026-01-01T10:02:00"}
    ], ensure_ascii=False))
    print(f"\nparse_talk_context(新格式): {result}")

    # 测试 merge_user_info
    result = merge_user_info(
        condition_desc_list=["非鼓励层", "工时内"],
        variable_data={"userAccountStatusDesc": "暂未发现异常", "unapprovedCount": "0"}
    )
    print(f"\nmerge_user_info: {result}")

    # 测试 extract_query_entities
    result = extract_query_entities(raw_query="账号出问题了")
    print(f"\nextract_query_entities: {result}")

    # 测试 merge_entity_context
    result = merge_entity_context(
        query_entities=extract_query_entities(raw_query="账号出问题了")["query_entities"],
        user_list=["非鼓励层", "工时内", "非黑名单", "用户账号状态:暂未发现异常", "未审核数:0"],
        has_ban=0,
        confirm_liveness_detection=0,
        reject_data=""
    )
    print(f"\nmerge_entity_context: {result}")

    # 测试 check_slot_completeness
    result = check_slot_completeness(entity_context=result["entity_context"])
    print(f"\ncheck_slot_completeness: {result}")