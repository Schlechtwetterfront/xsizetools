# XSIZETools

**Note** If you encounter any problems with this plugin, try an earlier version by choosing one from
[this link][releases].

## Overview

XSIZETools is an addon for Softimage with full export and import of 3D .msh files for ZeroEngine (Star Wars Battlefront I and II). That includes geometry, materials with all ZeroEngine-specific flags, animations, collisions and simulated cloth.

In general, important updates will be gathered into a [release][releases], so choosing the latest release should give you the latest working features. Alternatively you can download the most recent commit directly with the "Download ZIP" button.

For more information on usage go to the [XSIZETools homepage][homepage].

If you encounter bugs or have problems, feel free to post on the [Gametoast forums][gametoast] (you might need to use a proxy) or send me a mail via Github.

## Installation

To use XSIZETools you need the following:

1. Choose one of the [releases from here][releases] and download it.

1. If you **don't** have a Softimage version of 2011 or higher,
   download and install [python][python27] and
   [pywin32][pywin27] (pywin32 must be version 217).

1. Download and install the [Visual C++ 2015 Redistributable](redist15).
   Download both versions by selecting the format and activating the _Download_ button.
   If the page doesn't automatically navigate to the Visual C++ 2015 redist select _Tools for Visual Studio 2015_ on the left and then choose _Microsoft Visual C++ 2015 Redistributable_.

1. Unzip the downloaded archive into
   `C:/users/%user%/Autodesk/Softimage_%version%/Addons/` or `C:/users/%user%/Softimage/Softimage_%version%/Addons/`.
   In the end, the directory including `README.md`, `xsizet.ver`, etc should be `C:/Users/%user%/Autodesk/Softimage_2015/Addons/xsizetools/`.

## Building from source

Currently the solution is set up to use two installations of Softimage (one for x64, one for x86) with the corresponding XSISDK.

Modify `setup_86.bat` and `setup_64.bat` to point it to the correct _SDK paths_ (XSISDK_ROOT) and `setenv.bat`s. After that, use `setup_86.bat` to compile the x86 version and `setup_64.bat` to compile the 64 version.

## Links

- [XSIZETools Homepage][homepage]
- [Gametoast Thread][gametoast]
- [Python Downloads][python]
- [Pywin Downloads][pywin]
- [Python 2.7][python27] + [Pywin][pywin27]
- [Visual C++ 2015 redist][redist15]

[homepage]: http://schlechtwetterfront.github.io/xsizetools/ "XSIZETools Homepage"
[gametoast]: http://gametoast.com/viewtopic.php?f=36&t=26664 "Gametoast Thread"
[releases]: https://github.com/Schlechtwetterfront/xsizetools/releases "Releases"
[python]: https://www.python.org/downloads/ "Python Download"
[python27]: https://www.python.org/ftp/python/2.7.18/python-2.7.18.msi "Python 2.7"
[pywin27]: https://sourceforge.net/projects/pywin32/files/pywin32/Build%20217/pywin32-217.win32-py2.7.exe/download "Pywin for 2.7"
[pywin]: https://github.com/mhammond/pywin32/releases "Pywin Download"
[redist15]: https://www.visualstudio.com/downloads/download-visual-studio-vs#d-visual-c "C++ 2015 redist"
[redist86]: http://www.microsoft.com/download/en/details.aspx?id=5555 "C++ 2010 redist Download"
[redist64]: http://www.microsoft.com/downloads/de-de/details.aspx?FamilyID=bd512d9e-43c8-4655-81bf-9350143d5867 "C++ 2010 redist Download"
