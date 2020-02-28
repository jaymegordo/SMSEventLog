from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='smseventlog', 
    version='3.0.0',
    packages=find_packages(),
    install_requires=[
        'xlwings',
        'pandas',
        'pypika',
        'pyyaml',
        'sqlalchemy',
        'pyodbc==4.0.28',
        'pyqt5',
        'xlrd',
        'bs4'],
    package_data={'': ['*.yaml', '*.png', '*.txt']}, 
    author='Jayme Gordon',
    author_email='',
    description='SMS Event Log',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jaymegordo/SMSEventLog',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)