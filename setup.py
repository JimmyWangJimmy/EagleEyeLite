from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="eagleeye-lite",
    version="1.0.0",
    author="JimmyWang",
    author_email="jimmywang@example.com",
    description="Financial Audit Intelligence System with RAG + LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JimmyWangJimmy/EagleEyeLite",
    packages=find_packages(exclude=["tests*", "scripts*", "docs*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
    ],
    python_requires=">=3.8",
    install_requires=[
        "sentence-transformers>=2.2.0",
        "chromadb>=0.3.21",
        "anthropic>=0.7.0",
        "pdfplumber>=0.9.0",
        "langgraph>=0.0.1",
        "langchain>=0.1.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "pylint>=2.17.5",
        ],
        "ocr": ["easyocr>=1.6.0"],
    },
)
