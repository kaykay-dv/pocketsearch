import setuptools

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "pocketsearch",
    version = "0.21.1",
    author = "kaykay-dv",
    author_email = "kaykay2306@gmail.com",
    description = "A pure-Python full text indexing search library based on sqlite and the FTS5 extension.",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/kaykay-dv/pocketsearch/",
    project_urls = {
        "Bug Tracker": "https://github.com/kaykay-dv/pocketsearch/issues",
        "Change log" : "https://github.com/kaykay-dv/pocketsearch/blob/main/CHANGELOG.md",
        "Documentation" : "https://pocketsearch.readthedocs.io/"
    },
    classifiers = [
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Indexing"
    ],
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where="src"),
    python_requires = ">=3.8"
)
