from setuptools import find_packages, setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='pdf2tables',
    version='0.3.2',
    packages=find_packages(where='.', exclude=(), include=('*',)),
    url='https://github.com/chen1tian/pdf2tables',
    license='BSD 2-Clause License',
    author='yitian.chen',
    author_email='48295852@qq.com',
    description='extract tables from pdf using camelot, if page is image-base, use ocr to extract',
    long_description_content_type='text/markdown',
    long_description=long_description,
    install_requires=[
        'opencv-python >= 4.0.0.21',
        'pytesseract >= 0.2.6',
        'camelot-py >= 0.7.3',
        'numpy >= 1.16.0'
    ]
)
