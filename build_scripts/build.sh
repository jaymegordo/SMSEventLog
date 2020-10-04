#!/bin/zsh

# create exe/keys/versions, zip package, sign, and move files to pyu-data/deploy ready for deployment
# run from terminal with: zsh build.sh {version} > eg zsh build.sh 3.0.4

upload=$1
version="3.2.3"
echo "version: $version, upload: $upload"

# scripts in build_scripts for organization, but run commands from project root
cd .
pyupdater build --app-version=$version smseventlog.spec
pyupdater pkg --process --sign

if [ $upload = true ]; then
    zsh build_scripts/upload.sh
fi