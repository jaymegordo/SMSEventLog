import os
import shutil
import sys
from pathlib import Path

from setuptools import Command, find_packages, setup

VERSION = '3.2.0'

# Remove leftover folders from setuptools
class CleanCommand(Command):
    user_options = [
        ('all', None, 'delete everything'),
        ('pre', None, 'same as all'),
        ('post', None, 'delete .egg-info after build')]

    def initialize_options(self):
        self.all = None
        self.pre = None
        self.post = None

    def finalize_options(self):
        pass

    def run(self):
        if self.all or self.pre:
            remove = ['*.egg-info', 'build', 'dist']
        elif self.post:
            remove = ['*.egg-info']

        lst = []
        for r in remove:
            lst.extend([p for p in Path.cwd().glob(r)])
        
        for p in lst:
            shutil.rmtree(p)
            print('removing folder: {}'.format(str(p)))

cmd_classes = dict(clean=CleanCommand)

# Names of required packages
requires = [
    'bs4>=0.0.1',
    'pandas>=1.0.1',
    'pyodbc==4.0.28',
    'pypika>=0.35.21',
    'pyqt5>=5.14.1',
    'pyyaml>=5.3',
    'sqlalchemy>=1.3.13',
    'xlrd>=1.2.0',
    'xlwings>=0.18.0']

package_data = {'smseventlog': [
    'data/images/*',
    'data/apikeys/*',
    'data/config.yaml',
    'data/email.yaml',
    'data/db_secret.txt']}

setup(
    name='smseventlog', 
    version=VERSION,
    packages=find_packages(),
    install_requires=requires,
    package_data=package_data, 
    author='Jayme Gordon',
    author_email='',
    description='SMS Event Log',
    long_description='',
    long_description_content_type='text/markdown',
    url='https://github.com/jaymegordo/SMSEventLog',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    cmdclass=cmd_classes
)
