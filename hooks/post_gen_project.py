"""
cookiecutter 生成后钩子。

在项目生成后执行清理和初始化。
"""

import os
import shutil


def remove_file(filepath: str) -> None:
    """如果文件存在则删除。"""
    if os.path.exists(filepath):
        os.remove(filepath)


def remove_dir(dirpath: str) -> None:
    """如果目录存在则删除。"""
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)


def main():
    # 获取 cookiecutter 变量
    include_websocket = '{{ cookiecutter.include_websocket }}' == 'yes'
    include_jinja2 = '{{ cookiecutter.include_jinja2 }}' == 'yes'
    use_redis = '{{ cookiecutter.use_redis }}' == 'yes'
    use_celery = '{{ cookiecutter.use_celery }}' == 'yes'
    
    # 如果不需要则移除可选组件
    if not include_websocket:
        remove_dir('app/websocket')
    
    if not include_jinja2:
        remove_dir('app/templates')
    
    # 从 .env.example 创建 .env
    if os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
    
    print("")
    print("=" * 60)
    print("项目创建成功！")
    print("=" * 60)
    print("")
    print("后续步骤：")
    print("")
    print("1. 进入项目目录：")
    print("   cd {{ cookiecutter.project_slug }}")
    print("")
    print("2. 创建虚拟环境：")
    print("   python -m venv .venv")
    print("   # Windows: .venv\\Scripts\\activate")
    print("   # Linux/Mac: source .venv/bin/activate")
    print("")
    print("3. 安装依赖：")
    print("   pip install -r requirements.txt")
    print("   # 开发环境: pip install -r requirements-dev.txt")
    print("")
    print("4. 配置环境：")
    print("   # 编辑 .env 文件设置配置")
    print("")
    print("5. 运行数据库迁移：")
    print("   alembic upgrade head")
    print("")
    print("6. 启动开发服务器：")
    print("   uvicorn app.main:app --reload")
    print("")
    print("7. 或使用 Docker：")
    print("   docker-compose -f docker-compose.dev.yml up --build")
    print("")
    print("API 文档: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == '__main__':
    main()
