import os
from setuptools import setup, find_packages
packages = list(find_packages())
try:
    import py2exe
except ImportError:
    pass
else:
    import sys
    sys.path.insert(0, 'win32')


here = os.path.dirname(__file__)
data_files = {}
for path, dirs, files in os.walk(os.path.join(here, 'moonbaseapollo', 'assets')):
    for f in files:
        p = os.path.join(path, f)
        data_files.setdefault(path, []).append(p)

data_files = data_files.items()

setup(
    name='moonbaseapollo',
    version='1.0.1',
    packages=find_packages(),
    description="Moonbase Apollo",
    long_description=open('README.rst').read(),
    author='Daniel Pope/Arnav Khare',
    author_email='lord.mauve@gmail.com',
    url='http://www.pyweek.org/e/wasabi-idli2/',
    install_requires=[
        'pyglet>=1.1.4',
        'wasabi.geom>=0.1.3',
        'lepton==1.0b2',
        'distribute>=0.6'
    ],
    package_data={
        'moonbaseapollo': ['assets/*/*'],
    },
    entry_points={
        'console_scripts': [
            'moonbaseapollo = moonbaseapollo.game:main',
        ]
    },
    windows=['run_game.py'],
    options={
        "py2exe": {
            "packages": ['lepton']
        }
    },
    data_files=data_files
)
