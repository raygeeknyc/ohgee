#!/bin/bash
PYTHON=$(which python3)
if [[ -z "$DISPLAY" ]];then
  export DISPLAY=":0.0"
fi
echo "Waiting for connectivity"
timeout_secs=90
endTime=$(( $(date +%s) + timeout_secs )) # Calculate end time.
rc=255
while [ $(date +%s) -lt $endTime ]; do  # Loop until interval has elapsed.
  sleep 1
  ping -c 1 www.github.com 2>&1
  rc=$?
  if [[ $rc -eq 0 ]]; then
    break
  fi
done
if [[ $rc -eq 0 ]]; then
  MY_ADDRESS=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')
  echo "ADDRESS $MY_ADDRESS"
  pico2wave -l en-US --wave "/tmp/ohgee_online.wav" "My address is $MY_ADDRESS";aplay "/tmp/ohgee_online.wav"
else
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "help!  no network";aplay "/tmp/ohgee_help.wav"
  echo "sudo reboot" | at now + 5 minutes
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "Reboot in 5 minutes";aplay "/tmp/ohgee_help.wav"
  exit 255
fi
sleep 1
pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "updating";aplay "/tmp/ohgee_help.wav"
chmod a+x *.sh

####
# Temporary fix for a conflict in update.sh
# git fetch origin master
# git reset --hard FETCH_head
####

./update.sh 2>&1
. ./setup_auth.sh
./pre_launch_hook.sh 2>&1
nohup $PYTHON ohgee.py &
exit 0
