#!/usr/bin/env python

from setuptools import setup

setup(
    name='gh_md_to_html',
    version='1.0.5',
    description='Github-flavored Markdown to html python and command line interface.',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    scripts=['./scripts/gh-md-to-html'],
    author='phseiff',
    author_email='contact@phseiff.com',
    url='https://github.com/phseiff/github-flavored-markdown-to-html/',
    packages=['gh_md_to_html'],
    package_dir={'gh_md_to_html': 'src'},
    package_data={'gh_md_to_html': ['*']},
    include_package_data=True,
    install_requires=open("requirements.txt", "r").read().splitlines(),
    license="LICENSE.txt",
    extras_require={
        'pdf_export': ["pdfkit"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.5",
)
