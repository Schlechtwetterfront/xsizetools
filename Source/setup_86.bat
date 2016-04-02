@echo off

call "D:\Program Files\Autodesk\Softimage 2015\Application\bin\Setenv.bat"
call  "D:\Programme (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" x86

set PATH
set "XSISDK_ROOT=.\XSISDK"

"D:\Program Files (x86)\Microsoft Visual Studio 14.0\Common7\IDE\devenv.exe" /useenv

echo on