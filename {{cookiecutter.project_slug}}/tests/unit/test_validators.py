"""
工具函数测试。

测试验证器和工具函数。
"""

import pytest
from datetime import date

from app.utils.validators import (
    validate_email,
    validate_phone,
    validate_password_strength,
    validate_id_card_cn,
    validate_username,
    validate_url,
    validate_date_range,
    validate_age,
    Patterns,
)


class TestEmailValidator:
    """邮箱验证器测试。"""
    
    def test_valid_email(self):
        """测试有效邮箱。"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
        ]
        
        for email in valid_emails:
            result = validate_email(email)
            assert result == email.lower()
    
    def test_invalid_email(self):
        """测试无效邮箱。"""
        invalid_emails = [
            "notanemail",
            "@nodomain.com",
            "no@domain",
            "",
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError):
                validate_email(email)


class TestPhoneValidator:
    """手机号验证器测试。"""
    
    def test_valid_cn_phone(self):
        """测试有效的中国手机号。"""
        valid_phones = [
            "13812345678",
            "15912345678",
            "18812345678",
        ]
        
        for phone in valid_phones:
            result = validate_phone(phone, "CN")
            assert result == phone
    
    def test_invalid_cn_phone(self):
        """测试无效的中国手机号。"""
        invalid_phones = [
            "1234567890",
            "12345678901",
            "23812345678",
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValueError):
                validate_phone(phone, "CN")


class TestPasswordValidator:
    """密码强度验证器测试。"""
    
    def test_strong_password(self):
        """测试强密码。"""
        strong_passwords = [
            "Password123",
            "Abc12345678",
            "StrongPass1",
        ]
        
        for password in strong_passwords:
            result = validate_password_strength(password)
            assert result == password
    
    def test_weak_password_too_short(self):
        """测试太短的密码。"""
        with pytest.raises(ValueError) as exc_info:
            validate_password_strength("Pass1")
        assert "长度" in str(exc_info.value)
    
    def test_weak_password_no_uppercase(self):
        """测试没有大写字母的密码。"""
        with pytest.raises(ValueError) as exc_info:
            validate_password_strength("password123")
        assert "大写" in str(exc_info.value)
    
    def test_weak_password_no_digit(self):
        """测试没有数字的密码。"""
        with pytest.raises(ValueError) as exc_info:
            validate_password_strength("PasswordABC")
        assert "数字" in str(exc_info.value)


class TestUsernameValidator:
    """用户名验证器测试。"""
    
    def test_valid_username(self):
        """测试有效用户名。"""
        valid_usernames = [
            "john",
            "john_doe",
            "John123",
        ]
        
        for username in valid_usernames:
            result = validate_username(username)
            assert result == username
    
    def test_invalid_username(self):
        """测试无效用户名。"""
        invalid_usernames = [
            "1john",  # 数字开头
            "ab",     # 太短
            "_john",  # 下划线开头
        ]
        
        for username in invalid_usernames:
            with pytest.raises(ValueError):
                validate_username(username)
    
    def test_valid_chinese_username(self):
        """测试有效的中文用户名。"""
        valid_usernames = [
            "张三",
            "用户123",
            "测试_user",
        ]
        
        for username in valid_usernames:
            result = validate_username(username, allow_chinese=True)
            assert result == username


class TestURLValidator:
    """URL 验证器测试。"""
    
    def test_valid_url(self):
        """测试有效 URL。"""
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path/to/page",
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            assert result == url
    
    def test_invalid_url(self):
        """测试无效 URL。"""
        invalid_urls = [
            "not a url",
            "ftp://example.com",
            "example.com",
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                validate_url(url)


class TestDateRangeValidator:
    """日期范围验证器测试。"""
    
    def test_valid_date_range(self):
        """测试有效日期范围。"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        
        result = validate_date_range(start, end)
        assert result == (start, end)
    
    def test_invalid_date_range(self):
        """测试无效日期范围（开始晚于结束）。"""
        start = date(2024, 2, 1)
        end = date(2024, 1, 1)
        
        with pytest.raises(ValueError) as exc_info:
            validate_date_range(start, end)
        assert "不能晚于" in str(exc_info.value)
    
    def test_date_range_exceeds_max_days(self):
        """测试超出最大天数限制。"""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        
        with pytest.raises(ValueError) as exc_info:
            validate_date_range(start, end, max_days=30)
        assert "不能超过" in str(exc_info.value)


class TestAgeValidator:
    """年龄验证器测试。"""
    
    def test_valid_age(self):
        """测试有效年龄。"""
        birth_date = date(2000, 1, 1)
        age = validate_age(birth_date, min_age=18, max_age=100)
        
        assert age >= 18
        assert age <= 100
    
    def test_age_too_young(self):
        """测试年龄太小。"""
        birth_date = date.today().replace(year=date.today().year - 10)
        
        with pytest.raises(ValueError) as exc_info:
            validate_age(birth_date, min_age=18)
        assert "不能小于" in str(exc_info.value)


class TestPatterns:
    """正则表达式模式测试。"""
    
    def test_email_pattern(self):
        """测试邮箱正则。"""
        assert Patterns.EMAIL.match("test@example.com")
        assert not Patterns.EMAIL.match("invalid")
    
    def test_phone_cn_pattern(self):
        """测试中国手机号正则。"""
        assert Patterns.PHONE_CN.match("13812345678")
        assert not Patterns.PHONE_CN.match("12345678901")
    
    def test_slug_pattern(self):
        """测试 Slug 正则。"""
        assert Patterns.SLUG.match("hello-world")
        assert Patterns.SLUG.match("test123")
        assert not Patterns.SLUG.match("Hello-World")  # 大写
        assert not Patterns.SLUG.match("hello_world")  # 下划线
