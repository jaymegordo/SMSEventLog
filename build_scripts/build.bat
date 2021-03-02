@echo off

set upload=%1
set version="3.4.0a1"

echo version=%version%, upload=%upload%

pipenv run pyupdater build --log-level=WARN --app-version=%version% smseventlog.spec
pipenv run pyupdater pkg --process --sign

if %upload%==true (
    call build_scripts\upload.bat)