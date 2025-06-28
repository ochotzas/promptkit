#!/usr/bin/env python3
"""
Setup script for PromptKit.
This is a fallback for environments that don't support pyproject.toml.
"""

import re
from pathlib import Path

from setuptools import find_packages, setup

readme_path = Path(__file__).parent / "README.md"
long_description = (
    readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
)


# Read version from __init__.py
def get_version() -> str:
    init_file = Path(__file__).parent / "promptkit" / "__init__.py"
    content = init_file.read_text(encoding="utf-8")
    match = re.search(r'__version__ = ["\']([^"\']*)["\']', content)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string")


setup(
    name="promptkit",
    version=get_version(),
    description="A dependable, production-quality solution for structured prompt engineering in LLM applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Olger Chotza",
    author_email="olgerdev@icloud.com",
    url="https://github.com/ochotzas/promptkit",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "jinja2>=3.0.0",
        "PyYAML>=6.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "openai>=1.0.0",
        "requests>=2.28.0",
        "tiktoken>=0.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=2.0.0",
            "myst-parser>=2.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    keywords="llm prompt engineering ai openai ollama yaml jinja2",
    entry_points={
        "console_scripts": [
            "promptkit=promptkit.cli.main:app",
        ],
    },
)
