"""
认证服务。
"""

from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import security_manager
from app.models.user import User
from app.services.user import user_service


class AuthService:
    """
    认证服务，处理登录、注册和令牌操作。
    """
    
    async def login(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        remember_me: bool = False,
    ) -> Optional[Tuple[User, dict]]:
        """
        用户认证并生成令牌。
        
        参数：
            db: 数据库会话
            email: 用户邮箱
            password: 明文密码
            remember_me: 延长令牌过期时间
            
        返回：
            如果成功则返回 (用户, 令牌字典) 元组，否则返回 None
        """
        # 用户认证
        user = await user_service.authenticate(db, email=email, password=password)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        # 确定令牌过期时间
        if remember_me:
            access_expire = timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 7
            )
        else:
            access_expire = timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # 生成令牌
        access_token = security_manager.create_access_token(
            user.id,
            expires_delta=access_expire,
        )
        refresh_token = security_manager.create_refresh_token(user.id)
        
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_expire.total_seconds()),
        }
        
        return user, tokens
    
    async def refresh_tokens(
        self,
        db: AsyncSession,
        *,
        refresh_token: str,
    ) -> Optional[Tuple[User, dict]]:
        """
        使用刷新令牌更新访问令牌。
        
        参数：
            db: 数据库会话
            refresh_token: JWT 刷新令牌
            
        返回：
            如果成功则返回 (用户, 新令牌字典) 元组，否则返回 None
        """
        # 解码刷新令牌
        token_data = security_manager.decode_token(refresh_token)
        
        if not token_data or token_data.token_type != "refresh":
            return None
        
        # 获取用户
        user = await user_service.get(db, int(token_data.user_id))
        
        if not user or not user.is_active:
            return None
        
        # 将旧的刷新令牌加入黑名单
        if token_data.jti:
            security_manager.blacklist_token(token_data.jti)
        
        # 生成新令牌
        tokens = security_manager.create_token_pair(user.id)
        tokens["expires_in"] = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        return user, tokens
    
    async def logout(
        self,
        *,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> bool:
        """
        通过将令牌加入黑名单来登出用户。
        
        参数：
            access_token: 当前访问令牌
            refresh_token: 可选的刷新令牌
            
        返回：
            如果成功则返回 True
        """
        # 解码并将访问令牌加入黑名单
        access_data = security_manager.decode_token(access_token)
        if access_data and access_data.jti:
            security_manager.blacklist_token(access_data.jti)
        
        # 解码并将刷新令牌加入黑名单
        if refresh_token:
            refresh_data = security_manager.decode_token(refresh_token)
            if refresh_data and refresh_data.jti:
                security_manager.blacklist_token(refresh_data.jti)
        
        return True
    
    async def change_password(
        self,
        db: AsyncSession,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> bool:
        """
        更改用户密码。
        
        参数：
            db: 数据库会话
            user: 用户实例
            current_password: 用于验证的当前密码
            new_password: 新密码
            
        返回：
            如果密码更改成功则返回 True
        """
        # 验证当前密码
        if not security_manager.verify_password(
            current_password, user.hashed_password
        ):
            return False
        
        # 更新密码
        user.hashed_password = security_manager.hash_password(new_password)
        db.add(user)
        
        return True


# 全局服务实例
auth_service = AuthService()
