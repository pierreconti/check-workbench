#!/usr/bin/env python

from setuptools import setup

setup(
    name='check',
    version='0.0.1',
    description='Import Check data into Workbench',
    author='Karim Ratib',
    author_email='karim@meedan.com',
    url='https://github.com/meedan/check-workbench',
    packages=[''],
    py_modules=['check'],
    install_requires=['pandas==0.23.4']
)
