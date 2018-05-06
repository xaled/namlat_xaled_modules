#!/usr/bin/env python3

from distutils.core import setup

import os


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            if not path.endswith('__pycache__') and not filename.endswith(".pyc"):
                paths.append(os.path.relpath(os.path.join(path, filename), directory))
    return paths


extra_files = package_files('namlat_ext/')

# print extra_files

setup(
    name='namlat_xaled_modules',
    version='0.0.0',
    description='My personal modules for namlat.',
    long_description='My personal modules for namlat.',
    long_description_content_type='text/rst',
    keywords='distributed monitoring reporting',
    author='Khalid Grandi',
    author_email='kh.grandi@gmail.com',
    license='MIT',
    url='https://github.com/xaled/namlat_xaled_modules/',
    install_requires=['namlat', 'requests', 'lxml'],
    python_requires='>=3',
    packages=['namlat_ext'],
    package_data={'': extra_files},
)
