#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIMP Library for Edges and Stations (Python version)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This is a new protocol designed for instant messaging (IM).
    The software provides accounts(user identity recognition) and
    communications between accounts safely by end-to-end encryption.
"""

import io

from setuptools import setup, find_packages

__version__ = '0.4.2'
__author__ = 'Albert Moky'
__contact__ = 'albert.moky@gmail.com'

with io.open('README.md', 'r', encoding='utf-8') as fh:
    readme = fh.read()

setup(
    name='dimples',
    version=__version__,
    url='https://github.com/dimchat/demo-py',
    license='MIT',
    author=__author__,
    author_email=__contact__,
    description='DIMP Library for Edges and Stations',
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    package_data={
        '': ['res/*.js']
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'dimid=dimples.register.run:main',
            'dims=dimples.station.start:main',
            'dime=dimples.edge.start:main'
        ]
    },
    install_requires=[
        # 'pycryptodome',  # 3.14.1
        # 'base58',  # 1.0.3
        # 'ecdsa',   # 0.16.1
        'dimplugins>=1.0.2',

        'dimsdk>=1.0.3',
        'dimp>=1.0.3',
        'dkd>=1.0.2',
        'mkm>=1.0.2',

        'startrek>=1.0.0',
        'tcp>=1.0.0',
        'udp>=1.0.0',
    ]
)
