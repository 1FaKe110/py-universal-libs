from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="lib",
    version="0.1.1",
    author="IFAKE110",
    author_email="gabko2016@gmail.com",
    description="A collection of utility libraries for database, HTTP, Kafka, logging, config and utils",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(include=['my_libs', 'my_libs.*']),
    package_dir={'my_libs': 'my_libs'},
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
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
        ],
    },
)