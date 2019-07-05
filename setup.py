from setuptools import setup, find_packages

setup(
    name='postprocess',
    version='0.3.0',
    description='Re-implementation of PDFNLT/postprocess in Python',
    author='The PDFNLT Project Team',
    author_email='PDFNLT@nii.ac.jp',
    install_requires=['lxml', 'nltk', 'docopt', 'python-crfsuite', 'regex'],
    url='https://github.com/KMCS-NII/postprocess',
    packages=find_packages(exclude=('tests', 'docs')),
    test_suite='tests')
