import os
import sys

import setuptools  # Don't delete, hook for distutils

from distutils.core import setup


setup(
	name="pssq",
	version="0.0.1",
	long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
	long_description_content_type="text/markdown",
	package_dir={"pssq": "src/pssq"},
	packages=["pssq"],
    author="Alexander Ptakhin",
    author_email="me@aptakhin.name",
    description="Prepares PostgreSQL queries for execution in more useful Pythonic way. Not ORM.",
    license="MIT",
    keywords="pssq",
    url="https://github.com/aptakhin/pssq",
    project_urls={
        "Source Code": "https://github.com/aptakhin/pssq",
    },
	classifiers=[
		"Development Status :: 3 - Alpha",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Programming Language :: Python",
		"Topic :: Software Development",
	],
)
