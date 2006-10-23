@echo off
echo    -----------------------------------------------
echo    Generate  win32 python excutable for WindowsXP
echo    Copyright (C) Vandy Omall 2006  
echo.
echo    This program is free software; you can redistribute it and/or modify
echo    it under the terms of the GNU General Public License as published by
echo    the Free Software Foundation; either version 2 of the License, or
echo    (at your option) any later version.
echo.
echo    This program is distributed in the hope that it will be useful,
echo    but WITHOUT ANY WARRANTY; without even the implied warranty of
echo    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
echo    GNU General Public License for more details.
echo.
echo    You should have received a copy of the GNU General Public License
echo    along with this program; if not, write to the Free Software
echo    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
echo    -----------------------------------------------
echo.
echo    First we going to check wheter dependencies are met.
echo    Required Dependencies are: Python 2.x, PyGTK, Pysco, 
echo    Pycairo, Pyexe
echo    Optional are PyOgg, PyVorbis
echo.
ping -n 3 localhost > nul
IF EXIST C:\Python23\pythonw.exe (echo [V] Python 2.3) ELSE ( echo [X] Python 2.3)
IF EXIST C:\Python24\pythonw.exe (echo [V] Python 2.4) ELSE (echo [X] Python 2.4)
IF EXIST C:\Python24\Removepy2exe.exe (echo [V] Pyexe) ELSE (echo [X] Pyexe)
IF EXIST C:\Python24\Removepygtk.exe (echo [V] PyGTK) ELSE (echo [X] PyGTK)
IF EXIST C:\Python24\Removepycairo.exe (echo [V] Pycairo) ELSE (echo [X] Pycairo)
IF EXIST C:\Python24\Removepsyco.exe (echo [V] Psyco) ELSE (echo [X] Psyco)
IF EXIST C:\Python24\Removepywin32.exe (echo [V] Pyvorbis) ELSE (echo [X] PyWin32)
IF EXIST C:\Python24\Removepyogg.exe (echo [V] PyOGG) ELSE (echo [X] PyOGG 2.4)
IF EXIST C:\Python24\Removepyvorbis.exe (echo [V] Pyvorbis) ELSE (echo [X] Pyvorbis)
echo.
echo    [V] FOUND [X] NOT FOUND!
echo    If you miss something, close this window and install.
echo    If everything is oke hit a key to continue.
echo.
pause   "Hit a key to continue"
echo ******************************************
echo   Clean /build from previous generate
echo ******************************************
cd ..
rd /S /Q build
echo  Done...
echo ******************************************
echo  Make Nicotine+ excutable
echo ******************************************
ping -n 3 localhost > nul
c:\Python24\python make_exe.py py2exe -O2
echo.
echo ******************************************
echo  Copy NicotinePlusGuide.html to dist\doc
echo ******************************************
ping -n 3 localhost > nul
cd dist
mkdir doc
cd ..
cd doc
xcopy NicotinePlusGuide.html ..\dist\doc /Y
cd ..
echo ******************************************
echo Cleanup directories
echo ******************************************
ping -n 3 localhost > nul
rd /S /Q build
echo ******************************************
echo  Nicotine+ is now ready for distribution.
echo  Thank you for using this Tool.
echo  Exit in 5sec.
echo ******************************************
ping -n 5 localhost > nul