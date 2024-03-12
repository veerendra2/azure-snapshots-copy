#!/usr/bin/python3
import sys
import setuptools
from setuptools.command.install import install

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='azure-snapshots-copy',
    author='veerendra2',
    author_email='vk.tyk23@simplelogin.com',
    description='A script to copy azure snapshots to a specified region and automatically delete them upon expiration.',
    keywords='azure, snapshot, pypi, package',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/veerendra2/azure-snapshots-copy',
    project_urls={
        'Documentation': 'https://github.com/veerendra2/azure-snapshots-copy',
        'Bug Reports':
        'https://github.com/veerendra2/azure-snapshots-copy/issues',
        'Source Code': 'https://github.com/veerendra2/azure-snapshots-copy',
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Utilities',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=['azure-identity==1.15.0',
                      'azure-mgmt-compute==30.5.0'],
    entry_points={
        'console_scripts': ['run=azure_snapshots_copy:main'],
    },
)