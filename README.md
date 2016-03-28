XSIZETools
========

**Note** If you encounter any problems with this plugin, try an earlier version by choosing one from
[this link][releases].

Overview
--------

XSIZETools is an addon for Softimage with full export and import of 3D .msh files for ZeroEngine (Star Wars Battlefront I and II). That includes geometry, materials with all ZeroEngine-specific flags, animations, collisions and simulated cloth.

In general, important updates will be gathered into a [release][releases], so choosing the latest release should give you the latest working features. Alternatively you can download the most recent commit directly with the "Download ZIP" button.

For more information on usage go to the [XSIZETools homepage][homepage].

If you encounter bugs or have problems, feel free to post on the [Gametoast forums][gametoast] (you might need to use a proxy) or send me a mail via Github.

Required
--------

* XSI 6.0+ (including ModTools)
* [Python 2.x][python download] & [pywin32][pywin download]
* Visual C++ 2010 redistributable: [x86][redist86] | [x64][redist64] (only if x86 didn't work)

Note that Softimage 2011 and higher already includes python and pywin.

Installation
--------

**Install:**
	
Unzip the archive into:

* %user_path%\\Autodesk\\%xsi_version%\\Addons _or_
* %user_path%\\Softimage\\%xsi_version%\\Addons
* Example: C:\\Users\\Ande\\Autodesk\\Softimage_2012\\Addons
	
	
**Uninstall:**

Exit XSI, then remove the XSIZETools folder from the path mentioned in _Install_.

Links
--------

* [XSIZETools Homepage][homepage]
* [Gametoast Thread][gametoast]
* [Python Downloads][python download]
* [Pywin Downloads][pywin download]
* [Python 2.6][python26] + [Pywin][pywin]
* Visual C++ 2010 redist: [x86][redist86] | [x64][redist64]

[homepage]: http://schlechtwetterfront.github.io/xsizetools/ "XSIZETools Homepage"
[gametoast]: http://gametoast.com/forums/viewtopic.php?f=36&t=26664 "Gametoast Thread"
[releases]: https://github.com/Schlechtwetterfront/xsizetools/releases "Releases"
[python download]: https://www.python.org/downloads/ "Python Download"
[python26]: http://www.python.org/ftp/python/2.6.6/python-2.6.6.msi "Python 2.6"
[pywin]: http://sourceforge.net/projects/pywin32/files/pywin32/Build%20217/pywin32-217.win32-py2.6.exe/download "Pywin for 2.6"
[pywin download]: https://sourceforge.net/projects/pywin32/files/ "Pywin Download"
[c++ redist download]: http://www.microsoft.com/download/en/details.aspx?id=5555 "C++ 2010 redist Download"
[redist86]: http://www.microsoft.com/download/en/details.aspx?id=5555 "C++ 2010 redist Download"
[redist64]: http://www.microsoft.com/downloads/de-de/details.aspx?FamilyID=bd512d9e-43c8-4655-81bf-9350143d5867 "C++ 2010 redist Download"