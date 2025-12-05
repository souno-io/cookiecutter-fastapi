"""
安全模块，提供 JWT 认证和密码哈希功能。

功能：
- JWT 令牌生成和验证
- 使用 bcrypt 进行密码哈希
- 令牌黑名单支持
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings


class TokenPayload(BaseModel):
    """JWT 令牌负载模式。"""
    sub: str
    exp: datetime
    iat: datetime
    type: str  # access or refresh
    jti: Optional[str] = None  # JWT ID for blacklisting


class TokenData(BaseModel):
    """解码后的令牌数据。"""
    user_id: str
    token_type: str
    jti: Optional[str] = None


class SecurityManager:
    """
    安全管理器，处理认证相关操作。
    
    提供：
    - 密码哈希和验证
    - JWT 令牌创建和验证
    - 令牌刷新机制
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self._blacklisted_tokens: set = set()  # In production, use Redis
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证明文密码与哈希值是否匹配。"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """使用 bcrypt 哈希密码。"""
        return self.pwd_context.hash(password)
    
    def create_access_token(
        self,
        subject: Union[str, int],
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[dict] = None,
    ) -> str:
        """
        创建 JWT 访问令牌。
        
        参数:
            subject: 令牌主题（通常是用户 ID）
            expires_delta: 自定义过期时间
            additional_claims: 要包含在令牌中的额外声明
            
        返回:
            编码后的 JWT 令牌字符串
        """
        import uuid
        
        now = datetime.utcnow()
        expire = now + (expires_delta or self.access_token_expire)
        
        to_encode = {
            "sub": str(subject),
            "exp": expire,
            "iat": now,
            "type": "access",
            "jti": str(uuid.uuid4()),
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        subject: Union[str, int],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        创建 JWT 刷新令牌。
        
        参数:
            subject: 令牌主题（通常是用户 ID）
            expires_delta: 自定义过期时间
            
        返回:
            编码后的 JWT 刷新令牌字符串
        """
        import uuid
        
        now = datetime.utcnow()
        expire = now + (expires_delta or self.refresh_token_expire)
        
        to_encode = {
            "sub": str(subject),
            "exp": expire,
            "iat": now,
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[TokenData]:
        """
        解码并验证 JWT 令牌。
        
        参数:
            token: JWT 令牌字符串
            
        返回:
            如果有效返回 TokenData，否则返回 None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            jti = payload.get("jti")
            if jti and jti in self._blacklisted_tokens:
                return None
            
            return TokenData(
                user_id=payload.get("sub"),
                token_type=payload.get("type"),
                jti=jti,
            )
        except JWTError:
            return None
    
    def blacklist_token(self, jti: str) -> None:
        """
        将令牌添加到黑名单。
        
        在生产环境中，应使用 Redis 实现以支持跨实例持久化。
        """
        self._blacklisted_tokens.add(jti)
    
    def is_token_blacklisted(self, jti: str) -> bool:
        """检查令牌是否在黑名单中。"""
        return jti in self._blacklisted_tokens
    
    def create_token_pair(self, subject: Union[str, int]) -> dict:
        """
        创建访问令牌和刷新令牌对。
        
        参数:
            subject: 令牌主题（通常是用户 ID）
            
        返回:
            包含 access_token 和 refresh_token 的字典
        """
        return {
            "access_token": self.create_access_token(subject),
            "refresh_token": self.create_refresh_token(subject),
            "token_type": "bearer",
        }


# 全局安全管理器实例
security_manager = SecurityManager()
