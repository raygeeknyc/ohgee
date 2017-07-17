#!/bin/bash
echo "Waiting for connectivity"
rc=255
while [[ $rc -ne 0 ]];do
  sleep 1
  ping -c 1 www.github.com 2>&1
  rc=$?
done
echo "updating"
git pull 2>&1
./setup_auth.sh 2>&1
nohup python ohgee.py &
