echo 64

@echo off

SET "SI_PATH=E:\Program Files\Autodesk\Softimage 2015"
SET "VS_PATH=E:\Programme (x86)\Microsoft Visual Studio 14.0"

call "%SI_PATH%\Application\bin\setenv.bat"
call "%VS_PATH%\VC\vcvarsall.bat" amd64

set PATH
set "XSISDK_ROOT=%SI_PATH%\XSISDK"

"%VS_PATH%\Common7\IDE\devenv.exe" /useenv

@echo on