#!/bin/bash
echo "waiting for connectivity"
rc=255
while [[ $rc -ne 0 ]];do
  sleep 1
  ping -c 1 www.github.com 2>&1
  rc=$?
done
if [[ $rc -eq 0 ]];then
   echo "updating"
   git pull 2>&1
else
   echo "not updating" >&2
fi
echo "authenticating"
GOOGLE_APPLICATION_CREDENTIALS=../paidtech-07060b047c89.json
if [[ ! -r "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
  echo "falling back to interactive authentication"
  gcloud auth application-default login
else
  export GOOGLE_APPLICATION_CREDENTIALS
fi
echo "authenticated"
