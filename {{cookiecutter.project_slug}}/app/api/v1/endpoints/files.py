"""
文件上传 API 端点。

提供文件上传、下载和管理接口。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.file import file_service, FileInfo
from app.schemas.common import Response
from app.core.exceptions import NotFoundError


router = APIRouter()


@router.post(
    "/upload",
    response_model=Response[FileInfo],
    summary="上传文件",
    description="上传单个文件，返回文件信息",
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    folder: str = Query("", description="存储文件夹"),
    current_user: User = Depends(get_current_user),
) -> Response[FileInfo]:
    """上传文件。"""
    file_info = await file_service.upload(
        file=file,
        folder=folder,
    )
    
    return Response(
        data=file_info,
        message="文件上传成功",
    )


@router.post(
    "/upload/image",
    response_model=Response[FileInfo],
    summary="上传图片",
    description="上传图片文件，支持 JPEG、PNG、GIF、WebP 格式",
)
async def upload_image(
    file: UploadFile = File(..., description="要上传的图片"),
    folder: str = Query("images", description="存储文件夹"),
    current_user: User = Depends(get_current_user),
) -> Response[FileInfo]:
    """上传图片。"""
    file_info = await file_service.upload_image(
        file=file,
        folder=folder,
    )
    
    return Response(
        data=file_info,
        message="图片上传成功",
    )


@router.post(
    "/upload/document",
    response_model=Response[FileInfo],
    summary="上传文档",
    description="上传文档文件，支持 PDF、Word、Excel 格式",
)
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档"),
    folder: str = Query("documents", description="存储文件夹"),
    current_user: User = Depends(get_current_user),
) -> Response[FileInfo]:
    """上传文档。"""
    file_info = await file_service.upload_document(
        file=file,
        folder=folder,
    )
    
    return Response(
        data=file_info,
        message="文档上传成功",
    )


@router.post(
    "/upload/batch",
    response_model=Response[List[FileInfo]],
    summary="批量上传文件",
    description="批量上传多个文件",
)
async def upload_files(
    files: List[UploadFile] = File(..., description="要上传的文件列表"),
    folder: str = Query("", description="存储文件夹"),
    current_user: User = Depends(get_current_user),
) -> Response[List[FileInfo]]:
    """批量上传文件。"""
    file_infos = []
    
    for file in files:
        file_info = await file_service.upload(
            file=file,
            folder=folder,
        )
        file_infos.append(file_info)
    
    return Response(
        data=file_infos,
        message=f"成功上传 {len(file_infos)} 个文件",
    )


@router.delete(
    "/{filepath:path}",
    response_model=Response,
    summary="删除文件",
    description="根据文件路径删除文件",
)
async def delete_file(
    filepath: str,
    current_user: User = Depends(get_current_user),
) -> Response:
    """删除文件。"""
    exists = await file_service.exists(filepath)
    if not exists:
        raise NotFoundError(
            message="文件不存在",
            resource="file",
            resource_id=filepath,
        )
    
    await file_service.delete(filepath)
    
    return Response(
        message="文件删除成功",
    )
