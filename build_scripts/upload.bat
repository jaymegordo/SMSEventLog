@ECHO OFF

REM Read variables from Windows_NT.env file, each dev will need to get a copy of the file first
for /f "eol=- delims=" %%a in (.vscode\Windows_NT.env) do set "%%a"

ECHO PYU_AWS_ID=%PYU_AWS_ID%
ECHO PYU_AWS_SECRET=%PYU_AWS_SECRET%

pipenv run pyupdater upload --service s3