"""
邮件服务模块。

提供邮件发送功能，支持：
- HTML 和纯文本邮件
- 附件支持
- 模板渲染
- 异步发送
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Union
import aiosmtplib

from pydantic import BaseModel, EmailStr

from app.core.config import settings


logger = logging.getLogger(__name__)


class EmailMessage(BaseModel):
    """邮件消息模型。"""
    
    to: List[EmailStr]
    subject: str
    body: str
    html_body: Optional[str] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    reply_to: Optional[EmailStr] = None
    attachments: Optional[List[str]] = None  # 文件路径列表


class EmailService:
    """
    邮件服务类。
    
    支持 SMTP 发送邮件，包括 HTML 和附件。
    """
    
    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        smtp_tls: bool = True,
        from_email: str = None,
        from_name: str = None,
    ):
        """
        初始化邮件服务。
        
        参数：
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 服务器端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码
            smtp_tls: 是否使用 TLS
            from_email: 发件人邮箱
            from_name: 发件人名称
        """
        self.smtp_host = smtp_host or getattr(settings, 'SMTP_HOST', 'localhost')
        self.smtp_port = smtp_port or getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = smtp_user or getattr(settings, 'SMTP_USER', '')
        self.smtp_password = smtp_password or getattr(settings, 'SMTP_PASSWORD', '')
        self.smtp_tls = smtp_tls
        self.from_email = from_email or getattr(settings, 'FROM_EMAIL', 'noreply@example.com')
        self.from_name = from_name or getattr(settings, 'FROM_NAME', settings.APP_NAME)
    
    async def send(self, message: EmailMessage) -> bool:
        """
        发送邮件。
        
        参数：
            message: 邮件消息对象
            
        返回：
            发送成功返回 True
        """
        try:
            msg = self._build_message(message)
            
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_tls,
            ) as smtp:
                if self.smtp_user and self.smtp_password:
                    await smtp.login(self.smtp_user, self.smtp_password)
                
                await smtp.send_message(msg)
            
            logger.info(f"邮件发送成功 | 收件人: {message.to} | 主题: {message.subject}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败 | 收件人: {message.to} | 错误: {str(e)}")
            return False
    
    def _build_message(self, message: EmailMessage) -> MIMEMultipart:
        """构建邮件消息对象。"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = ", ".join(message.to)
        
        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        
        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        
        # 添加纯文本内容
        msg.attach(MIMEText(message.body, "plain", "utf-8"))
        
        # 添加 HTML 内容
        if message.html_body:
            msg.attach(MIMEText(message.html_body, "html", "utf-8"))
        
        # 添加附件
        if message.attachments:
            for filepath in message.attachments:
                self._attach_file(msg, filepath)
        
        return msg
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str) -> None:
        """添加附件到邮件。"""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"附件不存在: {filepath}")
            return
        
        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={path.name}",
            )
            msg.attach(part)
    
    async def send_simple(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """
        发送简单邮件。
        
        参数：
            to: 收件人邮箱（单个或列表）
            subject: 邮件主题
            body: 邮件正文
            html_body: HTML 正文（可选）
        """
        if isinstance(to, str):
            to = [to]
        
        message = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        
        return await self.send(message)
    
    async def send_template(
        self,
        to: Union[str, List[str]],
        subject: str,
        template_name: str,
        context: dict,
    ) -> bool:
        """
        使用模板发送邮件。
        
        参数：
            to: 收件人邮箱
            subject: 邮件主题
            template_name: 模板名称
            context: 模板上下文
        """
        {%- if cookiecutter.include_jinja2 == "yes" %}
        from pathlib import Path
        from jinja2 import Environment, FileSystemLoader
        
        templates_dir = Path(__file__).parent.parent / "templates" / "emails"
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        
        try:
            template = env.get_template(template_name)
            html_body = template.render(**context)
            
            # 生成纯文本版本（简单处理）
            import re
            body = re.sub(r'<[^>]+>', '', html_body)
            
            return await self.send_simple(to, subject, body, html_body)
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return False
        {%- else %}
        logger.warning("模板功能需要启用 Jinja2 支持")
        return False
        {%- endif %}


# 全局邮件服务实例
email_service = EmailService()


# 常用邮件模板
class EmailTemplates:
    """预定义的邮件模板。"""
    
    @staticmethod
    def welcome_email(username: str, login_url: str) -> tuple:
        """
        欢迎邮件模板。
        
        返回：
            (主题, 纯文本正文, HTML 正文)
        """
        subject = "欢迎注册"
        
        body = f"""
您好 {username}，

欢迎加入我们！

您可以通过以下链接登录您的账户：
{login_url}

如有任何问题，请随时联系我们。

此致
{settings.APP_NAME} 团队
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">欢迎加入 {settings.APP_NAME}！</h2>
        <p>您好 <strong>{username}</strong>，</p>
        <p>感谢您的注册！</p>
        <p>
            <a href="{login_url}" 
               style="display: inline-block; padding: 12px 24px; 
                      background-color: #2563eb; color: white; 
                      text-decoration: none; border-radius: 4px;">
                登录账户
            </a>
        </p>
        <p>如有任何问题，请随时联系我们。</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">
            此邮件由 {settings.APP_NAME} 自动发送，请勿回复。
        </p>
    </div>
</body>
</html>
        """
        
        return subject, body, html_body
    
    @staticmethod
    def password_reset_email(username: str, reset_url: str, expires_in: int = 30) -> tuple:
        """
        密码重置邮件模板。
        
        返回：
            (主题, 纯文本正文, HTML 正文)
        """
        subject = "密码重置请求"
        
        body = f"""
您好 {username}，

我们收到了您的密码重置请求。

请点击以下链接重置密码（{expires_in} 分钟内有效）：
{reset_url}

如果您没有请求重置密码，请忽略此邮件。

此致
{settings.APP_NAME} 团队
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #dc2626;">密码重置请求</h2>
        <p>您好 <strong>{username}</strong>，</p>
        <p>我们收到了您的密码重置请求。</p>
        <p>
            <a href="{reset_url}" 
               style="display: inline-block; padding: 12px 24px; 
                      background-color: #dc2626; color: white; 
                      text-decoration: none; border-radius: 4px;">
                重置密码
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            此链接将在 {expires_in} 分钟后失效。
        </p>
        <p>如果您没有请求重置密码，请忽略此邮件。</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">
            此邮件由 {settings.APP_NAME} 自动发送，请勿回复。
        </p>
    </div>
</body>
</html>
        """
        
        return subject, body, html_body
    
    @staticmethod
    def verification_email(username: str, verify_url: str) -> tuple:
        """
        邮箱验证邮件模板。
        
        返回：
            (主题, 纯文本正文, HTML 正文)
        """
        subject = "请验证您的邮箱"
        
        body = f"""
您好 {username}，

请点击以下链接验证您的邮箱地址：
{verify_url}

此致
{settings.APP_NAME} 团队
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #16a34a;">验证您的邮箱</h2>
        <p>您好 <strong>{username}</strong>，</p>
        <p>请点击下方按钮验证您的邮箱地址。</p>
        <p>
            <a href="{verify_url}" 
               style="display: inline-block; padding: 12px 24px; 
                      background-color: #16a34a; color: white; 
                      text-decoration: none; border-radius: 4px;">
                验证邮箱
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">
            此邮件由 {settings.APP_NAME} 自动发送，请勿回复。
        </p>
    </div>
</body>
</html>
        """
        
        return subject, body, html_body
