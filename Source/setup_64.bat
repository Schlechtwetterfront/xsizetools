@echo off

call "D:\Program Files\Autodesk\Softimage 2015\Application\bin\setenv.bat"
call  "D:\Programme (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" amd64

set PATH
set "XSISDK_ROOT=D:\Program Files\Autodesk\Softimage 2015\XSISDK"

"D:\Programme (x86)\Microsoft Visual Studio 14.0\Common7\IDE\devenv.exe" /useenv

echo on