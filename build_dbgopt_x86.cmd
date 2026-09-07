@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x86 -vcvars_ver=14.42 >nul 2>&1
cd /d C:\dev\bridge-remix
set "PATH=%PATH:C:\Strawberry\c\bin;=%"
set "PATH=C:\dev\bridge-remix\_tools;C:\Users\4gutz\AppData\Local\Programs\Python\Python312;C:\Users\4gutz\AppData\Local\Programs\Python\Python312\Scripts;%PATH%"
set CC=cl
set CXX=cl
set CCACHE_DISABLE=1
if exist _compDbgOpt_x86\build.ninja goto compile
meson setup --buildtype release -Dcpp_args=/Zi -Dcpp_link_args=/DEBUG --backend ninja _compDbgOpt_x86 || exit /b 1
:compile
meson compile -C _compDbgOpt_x86
