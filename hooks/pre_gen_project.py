"""
Pre-generation hook for cookiecutter.

Validates project configuration before generation.
"""

import re
import sys


def validate_project_slug(slug: str) -> bool:
    """Validate project slug is a valid Python identifier."""
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
