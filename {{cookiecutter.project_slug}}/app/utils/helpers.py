"""
实用辅助函数。
"""

import re
import secrets
import string
from datetime import datetime
from typing import Any, List, Optional, TypeVar

T = TypeVar("T")


def generate_random_string(length: int = 32, include_symbols: bool = False) -> str:
    """
    生成加密安全的随机字符串。
    
    参数：
        length: 字符串长度
        include_symbols: 是否包含特殊字符
        
    返回：
        随机字符串
    """
    characters = string.ascii_letters + string.digits
    if include_symbols:
        characters += string.punctuation
    
    return "".join(secrets.choice(characters) for _ in range(length))


def slugify(text: str, max_length: int = 100) -> str:
    """
    将文本转换为 URL 友好的 slug。
    
    参数：
        text: 要转换的文本
        max_length: 最大 slug 长度
        
    返回：
        URL 友好的 slug
    """
    # 转换为小写
    text = text.lower()
    
    # 用连字符替换空格
    text = re.sub(r"\s+", "-", text)
    
    # 移除非字母数字字符（除了连字符）
    text = re.sub(r"[^a-z0-9-]", "", text)
    
    # 移除多个连续的连字符
    text = re.sub(r"-+", "-", text)
    
    # 移除前导/尾随连字符
    text = text.strip("-")
    
    # 截断到最大长度
    if len(text) > max_length:
        text = text[:max_length].rsplit("-", 1)[0]
    
    return text


def format_datetime(
    dt: Optional[datetime],
    format_str: str = "%Y-%m-%d %H:%M:%S",
    default: str = "",
) -> str:
    """
    将日期时间格式化为字符串。
    
    参数：
        dt: 日期时间对象
        format_str: 格式字符串
        default: dt 为 None 时的默认值
        
    返回：
        格式化的日期时间字符串
    """
    if dt is None:
        return default
    return dt.strftime(format_str)


def paginate(
    items: List[T],
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    对项目列表进行分页。
    
    参数：
        items: 要分页的项目列表
        page: 当前页码（从 1 开始）
        page_size: 每页项目数
        
    返回：
        包含分页信息和项目的字典
    """
    total = len(items)
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    # 验证页码
    page = max(1, min(page, pages)) if pages > 0 else 1
    
    # 计算切片索引
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


def mask_email(email: str) -> str:
    """
    为隐私保护隐藏邮箱地址。
    
    示例：test@example.com -> t***@example.com
    
    参数：
        email: 邮箱地址
        
    返回：
        隐藏后的邮箱
    """
    if "@" not in email:
        return email
    
    local, domain = email.split("@", 1)
    
    if len(local) <= 1:
        masked_local = local
    else:
        masked_local = local[0] + "***"
    
    return f"{masked_local}@{domain}"


def truncate_string(
    text: str,
    max_length: int = 100,
    suffix: str = "...",
) -> str:
    """
    将字符串截断到最大长度。
    
    参数：
        text: 要截断的文本
        max_length: 最大长度（包含后缀）
        suffix: 截断时添加的后缀
        
    返回：
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def snake_to_camel(snake_str: str) -> str:
    """将 snake_case 转换为 camelCase。"""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """将 camelCase 转换为 snake_case。"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_str).lower()
