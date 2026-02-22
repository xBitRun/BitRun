"""名称去重工具函数

提供名称解析和后缀生成的工具函数，用于策略和代理的名称去重。

示例:
    "BTC策略" -> "BTC策略-1" -> "BTC策略-2"
    "My Strategy" -> "My Strategy-1" -> "My Strategy-2"
"""

import re
from typing import Callable, Optional, Tuple


# 匹配名称末尾的数字后缀，支持中划线格式
# 示例: "BTC策略-1", "My Strategy-2", "Test-10"
_SUFFIX_PATTERN = re.compile(r"^(.+?)-(\d+)$")


def parse_name_with_suffix(name: str) -> Tuple[str, int]:
    """
    解析名称，提取基础名称和数字后缀。

    Args:
        name: 原始名称，可能包含数字后缀

    Returns:
        Tuple[str, int]: (基础名称, 后缀数字)
        如果没有后缀，返回 (原名称, 0)

    Examples:
        >>> parse_name_with_suffix("BTC策略")
        ("BTC策略", 0)
        >>> parse_name_with_suffix("BTC策略-1")
        ("BTC策略", 1)
        >>> parse_name_with_suffix("My Strategy-10")
        ("My Strategy", 10)
    """
    match = _SUFFIX_PATTERN.match(name)
    if match:
        base_name = match.group(1)
        suffix = int(match.group(2))
        return base_name, suffix
    return name, 0


def add_numeric_suffix(name: str, suffix: int) -> str:
    """
    为名称添加数字后缀。

    Args:
        name: 基础名称
        suffix: 后缀数字

    Returns:
        str: 带后缀的名称

    Examples:
        >>> add_numeric_suffix("BTC策略", 1)
        "BTC策略-1"
        >>> add_numeric_suffix("BTC策略", 0)
        "BTC策略"
    """
    if suffix <= 0:
        return name
    return f"{name}-{suffix}"


async def generate_unique_name(
    name: str,
    user_id: str,
    exists_check: Callable[[str, str], bool],
    max_attempts: int = 1000,
) -> str:
    """
    生成唯一名称，如冲突则添加数字后缀。

    这是一个异步版本的生成器，适用于异步的名称存在检查。

    Args:
        name: 期望的名称
        user_id: 用户 ID
        exists_check: 异步函数，检查名称是否存在
        max_attempts: 最大尝试次数

    Returns:
        str: 唯一的名称

    Examples:
        >>> await generate_unique_name("BTC策略", user_id, check_func)
        "BTC策略"  # 无冲突
        >>> await generate_unique_name("BTC策略", user_id, check_func)
        "BTC策略-1"  # 第一个冲突
        >>> await generate_unique_name("BTC策略", user_id, check_func)
        "BTC策略-2"  # 第二个冲突
    """
    import asyncio

    # 如果原名称可用，直接返回
    if not await exists_check(name, user_id):
        return name

    # 解析原名称的基础部分
    base_name, original_suffix = parse_name_with_suffix(name)

    # 从 suffix=1 开始尝试
    suffix = 1
    while suffix <= max_attempts:
        candidate = add_numeric_suffix(base_name, suffix)
        if not await exists_check(candidate, user_id):
            return candidate
        suffix += 1

    # 如果超过最大尝试次数，使用时间戳作为后缀
    import time
    timestamp = int(time.time())
    return add_numeric_suffix(base_name, timestamp)


def generate_unique_name_sync(
    name: str,
    user_id: str,
    exists_check: Callable[[str, str], bool],
    max_attempts: int = 1000,
) -> str:
    """
    生成唯一名称的同步版本。

    Args:
        name: 期望的名称
        user_id: 用户 ID
        exists_check: 同步函数，检查名称是否存在
        max_attempts: 最大尝试次数

    Returns:
        str: 唯一的名称
    """
    # 如果原名称可用，直接返回
    if not exists_check(name, user_id):
        return name

    # 解析原名称的基础部分
    base_name, original_suffix = parse_name_with_suffix(name)

    # 从 suffix=1 开始尝试
    suffix = 1
    while suffix <= max_attempts:
        candidate = add_numeric_suffix(base_name, suffix)
        if not exists_check(candidate, user_id):
            return candidate
        suffix += 1

    # 如果超过最大尝试次数，使用时间戳作为后缀
    import time
    timestamp = int(time.time())
    return add_numeric_suffix(base_name, timestamp)
