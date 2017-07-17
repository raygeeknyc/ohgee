#!/bin/bash
echo "waiting for connectivity"
echo "updating"
git pull 2>&1
echo "authenticating"
GOOGLE_APPLICATION_CREDENTIALS=../paidtech-07060b047c89.json
if [[ ! -r "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
  echo "falling back to interactive authentication"
  gcloud auth application-default login
else
  export GOOGLE_APPLICATION_CREDENTIALS
fi
echo "authenticated"
