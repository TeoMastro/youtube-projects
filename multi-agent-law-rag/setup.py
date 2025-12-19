"""
Setup configuration for Greek Legal Document RAG system.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="multi-agent-law-rag",
    version="0.1.0",
    description="Multi-agent system for analyzing Greek legal documents (ΦΕΚ PDFs)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/multi-agent-law-rag",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "multi-agent-law-rag=src.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="rag langchain langgraph multi-agent legal greek fek pdf nlp",
    project_urls={
        "Documentation": "https://github.com/yourusername/multi-agent-law-rag#readme",
        "Source": "https://github.com/yourusername/multi-agent-law-rag",
        "Tracker": "https://github.com/yourusername/multi-agent-law-rag/issues",
    },
)
