"""
文件上传和存储服务模块。

提供文件上传、下载和管理功能，支持：
- 本地存储
- 文件类型验证
- 文件大小限制
- 图片处理
- 云存储扩展接口
"""

import hashlib
import logging
import mimetypes
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple, Union

from fastapi import UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import FileError, ValidationError


logger = logging.getLogger(__name__)


class FileInfo(BaseModel):
    """文件信息模型。"""
    
    filename: str
    original_filename: str
    filepath: str
    url: str
    size: int
    content_type: str
    checksum: str
    created_at: datetime


class StorageBackend(ABC):
    """
    存储后端抽象基类。
    
    实现此类以支持不同的存储方式（本地、S3、OSS 等）。
    """
    
    @abstractmethod
    async def save(
        self, 
        file: BinaryIO, 
        filename: str, 
        folder: str = "",
    ) -> str:
        """
        保存文件。
        
        参数：
            file: 文件对象
            filename: 文件名
            folder: 文件夹路径
            
        返回：
            保存后的文件路径
        """
        pass
    
    @abstractmethod
    async def delete(self, filepath: str) -> bool:
        """
        删除文件。
        
        参数：
            filepath: 文件路径
            
        返回：
            删除成功返回 True
        """
        pass
    
    @abstractmethod
    async def exists(self, filepath: str) -> bool:
        """
        检查文件是否存在。
        
        参数：
            filepath: 文件路径
            
        返回：
            存在返回 True
        """
        pass
    
    @abstractmethod
    def get_url(self, filepath: str) -> str:
        """
        获取文件访问 URL。
        
        参数：
            filepath: 文件路径
            
        返回：
            文件访问 URL
        """
        pass


class LocalStorageBackend(StorageBackend):
    """本地文件存储后端。"""
    
    def __init__(
        self, 
        base_path: str = None,
        base_url: str = None,
    ):
        """
        初始化本地存储。
        
        参数：
            base_path: 文件存储根目录
            base_url: 文件访问 URL 前缀
        """
        self.base_path = Path(base_path or getattr(settings, 'UPLOAD_DIR', 'uploads'))
        self.base_url = base_url or getattr(settings, 'UPLOAD_URL', '/static/uploads')
        
        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save(
        self, 
        file: BinaryIO, 
        filename: str, 
        folder: str = "",
    ) -> str:
        """保存文件到本地。"""
        # 构建保存路径
        if folder:
            save_dir = self.base_path / folder
            save_dir.mkdir(parents=True, exist_ok=True)
            filepath = folder + "/" + filename
        else:
            save_dir = self.base_path
            filepath = filename
        
        full_path = save_dir / filename
        
        # 写入文件
        with open(full_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        logger.info(f"文件保存成功: {filepath}")
        return filepath
    
    async def delete(self, filepath: str) -> bool:
        """删除本地文件。"""
        full_path = self.base_path / filepath
        
        if full_path.exists():
            full_path.unlink()
            logger.info(f"文件删除成功: {filepath}")
            return True
        
        return False
    
    async def exists(self, filepath: str) -> bool:
        """检查本地文件是否存在。"""
        return (self.base_path / filepath).exists()
    
    def get_url(self, filepath: str) -> str:
        """获取文件访问 URL。"""
        return f"{self.base_url}/{filepath}"


class FileService:
    """
    文件服务类。
    
    提供文件上传、下载和管理功能。
    """
    
    # 默认允许的文件类型
    DEFAULT_ALLOWED_TYPES = {
        "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "document": [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
        "video": ["video/mp4", "video/mpeg", "video/quicktime", "video/webm"],
        "audio": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/webm"],
    }
    
    # 默认文件大小限制（字节）
    DEFAULT_MAX_SIZES = {
        "image": 10 * 1024 * 1024,     # 10MB
        "document": 50 * 1024 * 1024,  # 50MB
        "video": 500 * 1024 * 1024,    # 500MB
        "audio": 50 * 1024 * 1024,     # 50MB
    }
    
    def __init__(self, storage: StorageBackend = None):
        """
        初始化文件服务。
        
        参数：
            storage: 存储后端实例
        """
        self.storage = storage or LocalStorageBackend()
    
    async def upload(
        self,
        file: UploadFile,
        folder: str = "",
        allowed_types: List[str] = None,
        max_size: int = None,
        rename: bool = True,
    ) -> FileInfo:
        """
        上传文件。
        
        参数：
            file: 上传的文件
            folder: 保存的文件夹
            allowed_types: 允许的文件类型
            max_size: 最大文件大小
            rename: 是否重命名文件（使用 UUID）
            
        返回：
            文件信息对象
        """
        # 验证文件类型
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        if allowed_types and content_type not in allowed_types:
            raise ValidationError(
                message=f"不支持的文件类型: {content_type}",
                errors=[{"field": "file", "message": f"允许的类型: {allowed_types}"}],
            )
        
        # 读取文件内容
        contents = await file.read()
        file_size = len(contents)
        
        # 验证文件大小
        if max_size and file_size > max_size:
            raise ValidationError(
                message=f"文件过大，最大允许 {max_size / 1024 / 1024:.1f}MB",
                errors=[{"field": "file", "message": f"当前大小: {file_size / 1024 / 1024:.1f}MB"}],
            )
        
        # 计算文件哈希
        checksum = hashlib.md5(contents).hexdigest()
        
        # 生成文件名
        original_filename = file.filename
        if rename:
            ext = Path(original_filename).suffix
            filename = f"{uuid.uuid4().hex}{ext}"
        else:
            filename = original_filename
        
        # 按日期组织文件夹
        date_folder = datetime.now().strftime("%Y/%m/%d")
        if folder:
            full_folder = f"{folder}/{date_folder}"
        else:
            full_folder = date_folder
        
        # 保存文件
        from io import BytesIO
        filepath = await self.storage.save(
            BytesIO(contents),
            filename,
            full_folder,
        )
        
        return FileInfo(
            filename=filename,
            original_filename=original_filename,
            filepath=filepath,
            url=self.storage.get_url(filepath),
            size=file_size,
            content_type=content_type,
            checksum=checksum,
            created_at=datetime.now(),
        )
    
    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "images",
        max_size: int = None,
        resize: Tuple[int, int] = None,
    ) -> FileInfo:
        """
        上传图片（带类型和大小验证）。
        
        参数：
            file: 上传的图片文件
            folder: 保存的文件夹
            max_size: 最大文件大小
            resize: 调整尺寸 (width, height)
        """
        return await self.upload(
            file=file,
            folder=folder,
            allowed_types=self.DEFAULT_ALLOWED_TYPES["image"],
            max_size=max_size or self.DEFAULT_MAX_SIZES["image"],
        )
    
    async def upload_document(
        self,
        file: UploadFile,
        folder: str = "documents",
        max_size: int = None,
    ) -> FileInfo:
        """上传文档。"""
        return await self.upload(
            file=file,
            folder=folder,
            allowed_types=self.DEFAULT_ALLOWED_TYPES["document"],
            max_size=max_size or self.DEFAULT_MAX_SIZES["document"],
        )
    
    async def delete(self, filepath: str) -> bool:
        """删除文件。"""
        try:
            return await self.storage.delete(filepath)
        except Exception as e:
            logger.error(f"文件删除失败: {filepath} - {e}")
            raise FileError(message="文件删除失败", filename=filepath)
    
    async def exists(self, filepath: str) -> bool:
        """检查文件是否存在。"""
        return await self.storage.exists(filepath)
    
    def get_url(self, filepath: str) -> str:
        """获取文件 URL。"""
        return self.storage.get_url(filepath)
    
    @staticmethod
    def get_file_type(content_type: str) -> Optional[str]:
        """
        根据 MIME 类型获取文件类别。
        
        返回：
            文件类别（image, document, video, audio）或 None
        """
        for category, types in FileService.DEFAULT_ALLOWED_TYPES.items():
            if content_type in types:
                return category
        return None
    
    @staticmethod
    def validate_extension(
        filename: str,
        allowed_extensions: List[str],
    ) -> bool:
        """
        验证文件扩展名。
        
        参数：
            filename: 文件名
            allowed_extensions: 允许的扩展名列表（如 ['.jpg', '.png']）
        """
        ext = Path(filename).suffix.lower()
        return ext in [e.lower() for e in allowed_extensions]


# 全局文件服务实例
file_service = FileService()
