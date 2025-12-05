"""
自定义验证器模块。

提供常用的数据验证功能，支持：
- 邮箱验证
- 手机号验证
- 密码强度验证
- 身份证验证
- 自定义正则验证
"""

import re
from datetime import date, datetime
from typing import Any, Callable, List, Optional, Pattern, Union

from pydantic import field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo


# ==================== 正则表达式模式 ====================

class Patterns:
    """常用正则表达式模式。"""
    
    # 邮箱
    EMAIL = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    
    # 中国手机号
    PHONE_CN = re.compile(r"^1[3-9]\d{9}$")
    
    # 国际手机号（包含国家代码）
    PHONE_INTL = re.compile(r"^\+?[1-9]\d{1,14}$")
    
    # 用户名（字母开头，字母数字下划线）
    USERNAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{2,29}$")
    
    # 中文用户名
    USERNAME_CN = re.compile(r"^[\u4e00-\u9fa5a-zA-Z][a-zA-Z0-9_\u4e00-\u9fa5]{1,29}$")
    
    # 密码（至少8位，包含大小写和数字）
    PASSWORD_STRONG = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$"
    )
    
    # 中国身份证号（18位）
    ID_CARD_CN = re.compile(
        r"^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$"
    )
    
    # URL
    URL = re.compile(
        r"^https?://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+(/.*)?$"
    )
    
    # IPv4 地址
    IPV4 = re.compile(
        r"^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$"
    )
    
    # 邮政编码（中国）
    POSTAL_CODE_CN = re.compile(r"^\d{6}$")
    
    # 银行卡号
    BANK_CARD = re.compile(r"^\d{16,19}$")
    
    # 只包含字母
    ALPHA_ONLY = re.compile(r"^[a-zA-Z]+$")
    
    # 只包含数字
    NUMERIC_ONLY = re.compile(r"^\d+$")
    
    # 字母数字
    ALPHANUMERIC = re.compile(r"^[a-zA-Z0-9]+$")
    
    # Slug（URL 友好格式）
    SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


# ==================== 验证函数 ====================

def validate_email(value: str) -> str:
    """
    验证邮箱格式。
    
    参数：
        value: 邮箱地址
        
    返回：
        验证通过的邮箱地址（小写）
        
    异常：
        ValueError: 格式无效
    """
    if not value or not Patterns.EMAIL.match(value):
        raise ValueError("邮箱格式无效")
    return value.lower()


def validate_phone(
    value: str,
    country: str = "CN",
) -> str:
    """
    验证手机号格式。
    
    参数：
        value: 手机号
        country: 国家代码（CN: 中国）
        
    返回：
        验证通过的手机号
    """
    # 移除空格和横杠
    value = value.replace(" ", "").replace("-", "")
    
    if country == "CN":
        if not Patterns.PHONE_CN.match(value):
            raise ValueError("手机号格式无效（中国大陆）")
    else:
        if not Patterns.PHONE_INTL.match(value):
            raise ValueError("手机号格式无效")
    
    return value


def validate_password_strength(
    value: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False,
) -> str:
    """
    验证密码强度。
    
    参数：
        value: 密码
        min_length: 最小长度
        require_uppercase: 需要大写字母
        require_lowercase: 需要小写字母
        require_digit: 需要数字
        require_special: 需要特殊字符
        
    返回：
        验证通过的密码
    """
    errors = []
    
    if len(value) < min_length:
        errors.append(f"密码长度至少 {min_length} 位")
    
    if require_uppercase and not re.search(r"[A-Z]", value):
        errors.append("需要包含大写字母")
    
    if require_lowercase and not re.search(r"[a-z]", value):
        errors.append("需要包含小写字母")
    
    if require_digit and not re.search(r"\d", value):
        errors.append("需要包含数字")
    
    if require_special and not re.search(r"[@$!%*?&]", value):
        errors.append("需要包含特殊字符(@$!%*?&)")
    
    if errors:
        raise ValueError("；".join(errors))
    
    return value


def validate_id_card_cn(value: str) -> str:
    """
    验证中国身份证号。
    
    参数：
        value: 身份证号
        
    返回：
        验证通过的身份证号（大写）
    """
    value = value.upper()
    
    if not Patterns.ID_CARD_CN.match(value):
        raise ValueError("身份证号格式无效")
    
    # 校验码验证
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = "10X98765432"
    
    total = sum(int(value[i]) * weights[i] for i in range(17))
    expected_check = check_codes[total % 11]
    
    if value[17] != expected_check:
        raise ValueError("身份证号校验位错误")
    
    return value


def validate_username(
    value: str,
    allow_chinese: bool = False,
) -> str:
    """
    验证用户名格式。
    
    参数：
        value: 用户名
        allow_chinese: 允许中文字符
        
    返回：
        验证通过的用户名
    """
    if allow_chinese:
        if not Patterns.USERNAME_CN.match(value):
            raise ValueError("用户名格式无效（2-30位，可包含字母、数字、下划线和中文）")
    else:
        if not Patterns.USERNAME.match(value):
            raise ValueError("用户名格式无效（3-30位，字母开头，可包含字母、数字、下划线）")
    
    return value


def validate_url(value: str) -> str:
    """验证 URL 格式。"""
    if not Patterns.URL.match(value):
        raise ValueError("URL 格式无效")
    return value


def validate_ip_address(value: str) -> str:
    """验证 IPv4 地址格式。"""
    if not Patterns.IPV4.match(value):
        raise ValueError("IP 地址格式无效")
    return value


def validate_date_range(
    start_date: date,
    end_date: date,
    max_days: int = None,
) -> tuple:
    """
    验证日期范围。
    
    参数：
        start_date: 开始日期
        end_date: 结束日期
        max_days: 最大天数限制
        
    返回：
        验证通过的日期元组
    """
    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")
    
    if max_days:
        delta = (end_date - start_date).days
        if delta > max_days:
            raise ValueError(f"日期范围不能超过 {max_days} 天")
    
    return start_date, end_date


def validate_age(
    birth_date: date,
    min_age: int = 0,
    max_age: int = 150,
) -> int:
    """
    根据出生日期计算并验证年龄。
    
    参数：
        birth_date: 出生日期
        min_age: 最小年龄
        max_age: 最大年龄
        
    返回：
        计算出的年龄
    """
    today = date.today()
    age = today.year - birth_date.year
    
    # 检查是否已过生日
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    if age < min_age:
        raise ValueError(f"年龄不能小于 {min_age} 岁")
    if age > max_age:
        raise ValueError(f"年龄不能大于 {max_age} 岁")
    
    return age


def validate_file_extension(
    filename: str,
    allowed_extensions: List[str],
) -> str:
    """
    验证文件扩展名。
    
    参数：
        filename: 文件名
        allowed_extensions: 允许的扩展名列表
        
    返回：
        验证通过的文件名
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    allowed = [e.lower().lstrip(".") for e in allowed_extensions]
    
    if ext not in allowed:
        raise ValueError(f"不支持的文件类型，允许: {', '.join(allowed_extensions)}")
    
    return filename


def validate_json(value: str) -> dict:
    """
    验证 JSON 字符串。
    
    参数：
        value: JSON 字符串
        
    返回：
        解析后的字典
    """
    import json
    
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 格式无效: {e}")


# ==================== Pydantic 验证器工厂 ====================

def create_pattern_validator(
    pattern: Pattern,
    error_message: str,
) -> Callable:
    """
    创建正则表达式验证器。
    
    用法：
        class MyModel(BaseModel):
            code: str
            
            _validate_code = field_validator("code")(
                create_pattern_validator(
                    re.compile(r"^[A-Z]{3}\d{3}$"),
                    "代码格式无效（3个大写字母+3个数字）"
                )
            )
    """
    def validator(cls, v):
        if not pattern.match(v):
            raise ValueError(error_message)
        return v
    
    return validator


def create_length_validator(
    min_length: int = None,
    max_length: int = None,
    field_name: str = "字段",
) -> Callable:
    """
    创建长度验证器。
    
    用法：
        class MyModel(BaseModel):
            name: str
            
            _validate_name = field_validator("name")(
                create_length_validator(min_length=2, max_length=50, field_name="名称")
            )
    """
    def validator(cls, v):
        if min_length and len(v) < min_length:
            raise ValueError(f"{field_name}长度不能少于 {min_length}")
        if max_length and len(v) > max_length:
            raise ValueError(f"{field_name}长度不能超过 {max_length}")
        return v
    
    return validator


def create_range_validator(
    min_value: Union[int, float] = None,
    max_value: Union[int, float] = None,
    field_name: str = "数值",
) -> Callable:
    """
    创建数值范围验证器。
    
    用法：
        class MyModel(BaseModel):
            age: int
            
            _validate_age = field_validator("age")(
                create_range_validator(min_value=0, max_value=150, field_name="年龄")
            )
    """
    def validator(cls, v):
        if min_value is not None and v < min_value:
            raise ValueError(f"{field_name}不能小于 {min_value}")
        if max_value is not None and v > max_value:
            raise ValueError(f"{field_name}不能大于 {max_value}")
        return v
    
    return validator


def create_enum_validator(
    allowed_values: List[Any],
    field_name: str = "值",
) -> Callable:
    """
    创建枚举验证器。
    
    用法：
        class MyModel(BaseModel):
            status: str
            
            _validate_status = field_validator("status")(
                create_enum_validator(["active", "inactive", "pending"], field_name="状态")
            )
    """
    def validator(cls, v):
        if v not in allowed_values:
            raise ValueError(f"{field_name}无效，允许: {', '.join(str(x) for x in allowed_values)}")
        return v
    
    return validator


# ==================== 常用验证器装饰器 ====================

def strip_whitespace(cls, v: str) -> str:
    """去除字符串首尾空白。"""
    if isinstance(v, str):
        return v.strip()
    return v


def lowercase(cls, v: str) -> str:
    """转换为小写。"""
    if isinstance(v, str):
        return v.lower()
    return v


def uppercase(cls, v: str) -> str:
    """转换为大写。"""
    if isinstance(v, str):
        return v.upper()
    return v


def normalize_phone(cls, v: str) -> str:
    """规范化手机号（移除空格和横杠）。"""
    if isinstance(v, str):
        return v.replace(" ", "").replace("-", "")
    return v
