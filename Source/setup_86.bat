echo 86

@echo off

call "D:\Softimage\Softimage_Mod_Tool_7.5\Application\bin\setenv.bat"
call  "D:\Programme (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" x86

set PATH
set "XSISDK_ROOT=D:\Softimage\Softimage_Mod_Tool_7.5\XSISDK"

"D:\Programme (x86)\Microsoft Visual Studio 14.0\Common7\IDE\devenv.exe" /useenv

@echo on