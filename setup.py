#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-

from distutils.core import setup
import py2exe

setup(
    console = [
        {
            "script": "PixivUtil2.py",               # Main Python script
            "icon_resources": [(0, "icon2.ico")]     # Icon to embed into the PE file.
        }
    ], requires=['BeautifulSoup'],
    options = {'py2exe': {'compressed':1,
                            'bundle_files': 1,
                            'excludes': ['Tkconstants', 'Tkinter']
                            },
                 },
)
