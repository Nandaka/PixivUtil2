#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-


from os import path
import os
import sys

try:
    from setuptools import setup, convert_path, find_packages
    SETUPTOOLS_USED = True
except ImportError:
    from distutils.core import setup, find_packages
    from distutils.util import convert_path
    SETUPTOOLS_USED = False

isWindows = os.name is 'nt'
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


if not isWindows:
    if ranWithPy3:
        print(bcolors.WARNING)
        print("Attention: PixivUtil2 is not yet compatible with Python 3.  You have run this script with Python 3.")
        print("To install dependancies you will need to use a specific version of pip e.g.:\n")
        print("\tpip-2.7 install -r requirements.txt\n")
        print("To run you will need to specify python 2.x:\n")
        print("\tpython2 PixivUtil2.py\n")
        print(bcolors.ENDC)
        exit(-1)
    else:
        print("After installing, run with command:\n")
        print("\tPixivUtil2\n")


if isWindows:
    import py2exe

console = [{"script": "PixivUtil2.py",              # Main Python script
            "icon_resources": [(0, "icon2.ico")]}]  # Icon to embed into the PE file.
requires = ['BeautifulSoup']
options = {'py2exe': {'bundle_files': 3,
                      'compressed': 1,
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
# get program version
main_ns = {}
ver_path = convert_path('PixivConstant.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)
version = main_ns['PIXIVUTIL_VERSION']
v_parts = version.split('-', 1)
main_version = '{0}.{1}.{2}'.format(v_parts[0][0:4], int(v_parts[0][4:6]), int(v_parts[0][6:7]))
if '-' in version:
    version = main_version + '.{}'.format(v_parts[1])
else:
    version = main_version
# get long_description
readme_path = convert_path('readme.txt')
with open(readme_path) as readme_file:
    long_description = readme_file.read()

setup(
    name='PixivUtil2',  # Required
    version=version,
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='pixiv downloader',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=install_requires,
    **setup_kwargs
)

if isWindows:
    # add certify cacert.pem in library.zip/certifi
    import certifi
    import zipfile
    zip = zipfile.ZipFile('./dist/library.zip', 'a')
    zip.write(certifi.where(), "/certifi/cacert.pem")
    zip.close()
