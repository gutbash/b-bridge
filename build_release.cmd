@echo off
rem Usage: build_release.cmd x64 | x86
set ARCH=%1
if "%ARCH%"=="" set ARCH=x64
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" %ARCH% -vcvars_ver=14.42 >nul 2>&1
cd /d C:\dev\bridge-remix
set "PATH=%PATH:C:\Strawberry\c\bin;=%"
rem _tools holds a copy of python.exe named python3.exe: meson.build does find_program('python3', 'python')
rem and the Windows Store alias python3.exe would otherwise win and abort the vsgen step.
set "PATH=C:\dev\bridge-remix\_tools;C:\Users\4gutz\AppData\Local\Programs\Python\Python312;C:\Users\4gutz\AppData\Local\Programs\Python\Python312\Scripts;%PATH%"
set CC=cl
set CXX=cl
set CCACHE_DISABLE=1
set BUILDDIR=_compRelease_%ARCH%
if exist %BUILDDIR%\build.ninja goto compile
meson setup --buildtype release --backend ninja %BUILDDIR% || exit /b 1
:compile
meson compile -C %BUILDDIR%
