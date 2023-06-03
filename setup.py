import setuptools

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "pocketsearch",
    version = "0.0.1",
    author = "kaykay-dv",
    author_email = "kaykay2306@gmail.com",
    description = "A simple python search index",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/kaykay-dv/pypermint",
    project_urls = {
        "Bug Tracker": "package issues URL",
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where="src"),
    python_requires = ">=3.6"
)
