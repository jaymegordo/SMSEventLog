#!/bin/zsh

# push files from deploy folder to s3 bucket
# run from terminal with: zsh upload.sh

# set AWS ID/Secret in .vscode/.env file to keep secret
. .vscode/.env

export PYU_AWS_ID=$PYU_AWS_ID
export PYU_AWS_SECRET=$PYU_AWS_SECRET
echo "PYU_AWS_ID: $PYU_AWS_ID"
echo "PYU_AWS_SECRET: $PYU_AWS_SECRET"

pipenv run pyupdater upload --service s3