from setuptools import find_packages, setup

setup(
    name='pdf2tables',
    version='0.3.1',
    packages=find_packages(where='.', exclude=(), include=('*',)),
    url='',
    license='BSD License',
    author='yitian.chen',
    author_email='48295852@qq.com',
    description='extract tables from pdf using camelot, if page is image-base, use ocr to extract',
    install_requires=[
        'opencv-python >= 4.0.0.21',
        'pytesseract >= 0.2.6',
        'camelot-py >= 0.7.3',
        'numpy >= 1.16.0'
    ]
)

# if __name__ == "__main__":
#     a = find_packages(where='.', exclude=(), include=('*',))
#     print(a)
