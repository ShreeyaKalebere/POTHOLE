@echo off
REM Usage: double-click, then type your Person number (1-5)
set /p P=Which Person folder (1-5)? 
set D=%~dp0team_labeling\Person%P%
"%~dp0labelimg_env\Scripts\python.exe" -m labelImg.labelImg "%D%\images" "%D%\labels\classes.txt" "%D%\labels"
