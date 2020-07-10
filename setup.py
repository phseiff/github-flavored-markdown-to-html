#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='gh_md_to_html',
    version='1.0',
    description='Github-flavored Markdown to html python and command line interface.',
    author='phseiff',
    author_email='contact@phseiff.com',
    url='https://github.com/phseiff/github-flavored-markdown-to-html/',
    packages=['gh_md_to_html'],
    package_dir={'gh_md_to_html': 'src'},
    package_data={'gh_md_to_html': ['*']},
    include_package_data=True
)
