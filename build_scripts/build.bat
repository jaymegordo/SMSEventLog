@echo off

set upload=%1
set version="3.5.0"

echo version=%version%, upload=%upload%

poetry run pyupdater build --log-level=WARN --app-version=%version% smseventlog.spec
poetry run pyupdater pkg --process --sign

if %upload%==true (
    echo "uploading..."
    call build_scripts\upload.bat)