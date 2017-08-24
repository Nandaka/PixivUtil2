#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-

from distutils.core import setup

import os
import sys

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
    print (bcolors.FAIL)
    print ("____________________________")
    print ("          ERROR           ")
    print ("----------------------------")

    print ("Setup.py is used to generate executable under Windows systems\n")
    print ("For non windows systems please run:\n\n\tpip install -r requirements.txt")
    print (bcolors.ENDC)
    if ranWithPy3:
        print (bcolors.WARNING)
        print ("Attention: PixivUtil2 is not yet compatible with Python 3.  You have run this script with Python 3.")
        print ("To install dependancies you will need to use a specific version of pip e.g.:\n")
        print ("\tpip-2.7 install -r requirements.txt\n")
        print ("To run you will need to specify python 2.x:\n")
        print ("\tpython2 PixivUtil2.py\n")
        print (bcolors.ENDC)
    else:
        print ("After installing requirements run with command:\n")
        print ("\tpython PixivUtil2.py\n")
    exit(-1)


import py2exe

console = [{"script": "PixivUtil2.py",              # Main Python script
            "icon_resources": [(0, "icon2.ico")]}]  # Icon to embed into the PE file.
requires = ['BeautifulSoup']
options = {'py2exe': {'compressed': 1, 'excludes': ['Tkconstants', 'Tkinter']}, }

setup(console=console, requires=requires, options=options, )
