#!/usr/bin/env python

from setuptools import setup
# import glob

setup(
    name='gh_md_to_html',
    version='1.21.2',
    description='Feature-rich Github-flavored Markdown to html python and command line interface.',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    scripts=['./scripts/gh-md-to-html'],
    author='phseiff',
    author_email='phseiff@phseiff.com',
    url='https://github.com/phseiff/github-flavored-markdown-to-html/',
    packages=['gh_md_to_html'],
    package_dir={'gh_md_to_html': 'src'},
    # data_files=[
    #     ('src', glob.glob("src/*")),
    # ],
    package_data={'gh_md_to_html': ['*']},
    include_package_data=True,
    install_requires=["Pillow>=8.0.1", "requests", "shellescape", "webcolors", "beautifulsoup4", "emoji"],
    license="LICENSE.txt",
    extras_require={
        'pdf_export': ["pdfkit"],
        'offline_conversion': ["mistune==2.0.0rc1", "pygments"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6",
)
