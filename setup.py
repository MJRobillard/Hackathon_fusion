"""
Setup script for AONP - Agent-Orchestrated Neutronics Platform
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    with open(readme_file, encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "AONP - Agent-Orchestrated Neutronics Platform"

setup(
    name="aonp",
    version="0.1.0",
    author="AONP Development Team",
    description="High-integrity neutronics simulation platform with deterministic provenance",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/aonp",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0,<3.0.0",
        "pyyaml>=6.0",
        "pandas>=2.0.0",
        "pyarrow>=12.0.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "openmc": [
            "openmc>=0.14.0",  # Only works on Linux/macOS/WSL
        ],
        "dev": [
            "pytest>=7.4.0",
            "httpx>=0.25.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
        "agents": [
            "langchain>=0.1.0",
            "langgraph>=0.2.0",
            "langchain-openai>=0.0.5",
            "langchain-anthropic>=0.1.0",
            "python-dotenv>=1.0.0",
            "pymongo>=4.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aonp-run=aonp.runner.entrypoint:main",
        ],
    },
    include_package_data=True,
    package_data={
        "aonp": ["examples/*.yaml", "examples/*.py"],
    },
)

