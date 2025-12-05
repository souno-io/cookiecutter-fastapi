"""
邮件相关任务。

提供异步邮件发送功能。
"""

import logging
from typing import List, Optional

from app.core.celery_app import celery_app
from app.services.email import email_service, EmailMessage, EmailTemplates


logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_email_task(
    self,
    to: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
):
    """
    异步发送邮件任务。
    
    参数：
        to: 收件人列表
        subject: 邮件主题
        body: 邮件正文
        html_body: HTML 正文（可选）
    """
    import asyncio
    
    async def _send():
        message = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        return await email_service.send(message)
    
    try:
        result = asyncio.run(_send())
        if result:
            logger.info(f"邮件发送成功 | 收件人: {to}")
        else:
            logger.warning(f"邮件发送失败 | 收件人: {to}")
            raise Exception("邮件发送失败")
        return result
    except Exception as e:
        logger.error(f"邮件发送异常 | 收件人: {to} | 错误: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3)
def send_welcome_email_task(self, email: str, username: str, login_url: str):
    """
    发送欢迎邮件。
    
    参数：
        email: 用户邮箱
        username: 用户名
        login_url: 登录链接
    """
    subject, body, html_body = EmailTemplates.welcome_email(username, login_url)
    return send_email_task.apply(args=[[email], subject, body, html_body])


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_email_task(
    self,
    email: str,
    username: str,
    reset_url: str,
    expires_in: int = 30,
):
    """
    发送密码重置邮件。
    
    参数：
        email: 用户邮箱
        username: 用户名
        reset_url: 重置密码链接
        expires_in: 链接有效期（分钟）
    """
    subject, body, html_body = EmailTemplates.password_reset_email(
        username, reset_url, expires_in
    )
    return send_email_task.apply(args=[[email], subject, body, html_body])


@celery_app.task(bind=True, max_retries=3)
def send_verification_email_task(self, email: str, username: str, verify_url: str):
    """
    发送邮箱验证邮件。
    
    参数：
        email: 用户邮箱
        username: 用户名
        verify_url: 验证链接
    """
    subject, body, html_body = EmailTemplates.verification_email(username, verify_url)
    return send_email_task.apply(args=[[email], subject, body, html_body])
