"""
cookiecutter 生成前钩子。

在项目生成前验证项目配置。
"""

import re
import sys


def validate_project_slug(slug: str) -> bool:
    """验证项目 slug 是否为有效的 Python 标识符。"""
    pattern = r'^[a-z][a-z0-9_]*$'
    return bool(re.match(pattern, slug))


def main():
    project_slug = '{{ cookiecutter.project_slug }}'
    
    if not validate_project_slug(project_slug):
        print(f"ERROR: '{project_slug}' is not a valid project slug.")
        print("Please use only lowercase letters, numbers, and underscores.")
        print("The slug must start with a letter.")
        sys.exit(1)
    
    print(f"Creating project: {project_slug}")


if __name__ == '__main__':
    main()
