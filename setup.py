#!C:/Python37-32/python
# -*- coding: utf-8 -*-
import platform
import sys
from os import path

try:
    from setuptools import convert_path, find_packages, setup
    SETUPTOOLS_USED = True
except ImportError:
    from distutils.core import find_packages, setup
    from distutils.util import convert_path
    SETUPTOOLS_USED = False

isWindows = (platform.system() == "Windows")
ranWithPy3 = sys.version_info >= (3, 0)


# Terminal colors on *nix systems
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_version():
    main_ns = {}
    ver_path = convert_path('PixivConstant.py')
    with open(ver_path) as ver_file:
        exec(ver_file.read(), main_ns)
    version = main_ns['PIXIVUTIL_VERSION']
    v_parts = version.split('-', 1)
    # 20201231
    main_version = '{0}.{1}.{2}'.format(v_parts[0][0:4], int(v_parts[0][4:6]), int(v_parts[0][6:8]))
    if '-' in version:
        version = main_version + '.{}'.format(v_parts[1])
    else:
        version = main_version
    return version


if not isWindows:
    if ranWithPy3:
        print("After installing, run with command:\n")
        print("\tPixivUtil2\n")
    else:
        print(bcolors.WARNING)
        print("Attention: This PixivUtil2 is Python 3 version. You have run this script with Python 3.")
        print("To install dependancies you will need to use a specific version of pip e.g.:\n")
        print("\tpip-3.7 install -r requirements.txt\n")
        print("To run you will need to specify python 3.x:\n")
        print("\tpython3 PixivUtil2.py\n")
        print(bcolors.ENDC)
        exit(-1)


if isWindows:
    import py2exe

console = [{"script": "PixivUtil2.py",              # Main Python script
            "icon_resources": [(0, "icon2.ico")]}]  # Icon to embed into the PE file.
requires = ['bs4', 'html5lib', 'sqlite3']
options = {'py2exe': {'bundle_files': 3,
                      'compressed': 1,
                      "packages": ['html5lib', 'sqlite3', 'cloudscraper'],
                      'excludes': ['Tkconstants', 'Tkinter']}, }

setup_kwargs = dict(console=console, requires=requires, options=options)

if not isWindows:
    setup_kwargs = dict(
        entry_points={'console_scripts': ['PixivUtil2 = PixivUtil2:main', ]})

if SETUPTOOLS_USED:
    setup_kwargs['project_urls'] = {
        'Bug Reports': 'https://github.com/Nandaka/PixivUtil2/issues',
        'Funding': 'https://bit.ly/PixivUtilDonation',
        'Source': 'https://github.com/Nandaka/PixivUtil2',
    }

# get install_requires
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'requirements.txt')) as f:
    install_requires = f.read().split('\n')
install_requires = [x.strip() for x in install_requires]

# get long_description
readme_path = convert_path('readme.md')
with open(readme_path, 'r', encoding='utf-8') as readme_file:
    long_description = readme_file.read()

setup(
    name='PixivUtil2',  # Required
    version=get_version(),
    description='Download images from Pixiv and more',
    long_description=long_description,
    url='https://github.com/Nandaka/PixivUtil2',
    author='Nandaka',
    # author_email='<>@<>.com',
    classifiers=[  # Optional
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='pixiv downloader',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=install_requires,
    **setup_kwargs
)

if isWindows:
    print("Adding cacert.pem.")
    # add certify cacert.pem in library.zip/certifi
    import zipfile

    import certifi
    zip2 = zipfile.ZipFile('./dist/library.zip', 'a')
    zip2.write(certifi.where(), "/certifi/cacert.pem")
    zip2.close()

    print("Adding browsers.json.")
    import shutil
    import cloudscraper
    # need to bundle browser json
    browser_json_location = cloudscraper.__file__.replace('__init__.py', 'user_agent\\browsers.json')
    shutil.copy(browser_json_location, "dist/browsers.json")

    print("update done.")
