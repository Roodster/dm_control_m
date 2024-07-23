import os
from setuptools import setup
from setuptools import find_packages

setup(
    name='dm_control_m',
    version='0.1.0',
    author='Rody Haket',
    description=('Custom DeepMind Control Suite'),
    license='MIT',
    keywords='gym dm_control openai deepmind',
    packages=find_packages(),	
    include_package_data = True,
    install_requires=[
        'gym',
    ],
)
