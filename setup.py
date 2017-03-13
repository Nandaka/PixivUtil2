#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-

from distutils.core import setup

import os

isWindows = os.name is 'nt'

if not isWindows:
    print "____________________________"
    print "          Notice            "
    print "----------------------------"
    print "Setup.py is used to generate executable under Windows systems\n"
    print "For non windows systems please run:\n\tpip install -r requirements.txt\n"
    print "Note: PixivUtil2 is not yet compatible with Python 3. If Python 3 is your default"
    print "interpreter you will need to use a specific version of pip e.g.:\n"
    print "\tpip-2.7 install -r requirements.txt\n"
    print "After installing requirements run with command:\n"
    print "\tpython PixivUtil2.py\n"
    print "or if you need to specify python 2.x:\n"
    print "\tpython2 PixivUtil2.py\n"
    exit(-1)


import py2exe

console = [{"script": "PixivUtil2.py",              # Main Python script
            "icon_resources": [(0, "icon2.ico")]}]  # Icon to embed into the PE file.
requires = ['BeautifulSoup']
options = {'py2exe': {'compressed': 1, 'excludes': ['Tkconstants', 'Tkinter']}, }

setup(console, requires, options, )
