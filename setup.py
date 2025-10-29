from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="iflib-tools",
    version="0.1.13",
    author="IFAKE110",
    author_email="gabko2016@gmail.com",
    description="A collection of utility libraries for database, HTTP, Kafka, logging, config and utils",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=[
        "loguru>=0.7.0",
        "sqlalchemy>=1.4.0",
        "pandas>=1.3.0",
        "requests>=2.25.0",
        "confluent-kafka>=2.3.0",
        "pyyaml>=6.0",
        "python-dotenv>=0.19.0",
        "urllib3>=1.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
        ],
    },
)