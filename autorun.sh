#!/bin/bash
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
  MY_ADDRESS=$(ifconfig | grep "inet addr" | grep -v "127.0.0.1" | awk '{print $2}' | awk 'BEGIN { FS = ":" } ; { print $2 }')
  pico2wave -l en-US --wave "/tmp/ohgee_online.wav" "My address is $MY_ADDRESS";aplay "/tmp/ohgee_online.wav"
else
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "help!  no network";aplay "/tmp/ohgee_help.wav"
  echo "sudo reboot" | at now + 30 minutes
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "Reboot in 30 minutes";aplay "/tmp/ohgee_help.wav"
  exit 255
fi
pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "updating";aplay "/tmp/ohgee_help.wav"
chmod a+x *.sh

####
# Temporary fix for a conflict in update.sh
# git fetch origin master
# git reset --hard FETCH_head
####

./setaudio.sh
./update.sh 2>&1
if [[ -z "$DISPLAY" ]];then
  export DISPLAY=":0.0"
fi
eval `./setup_auth.sh` # sets rc
if [[ $rc -ne 0 ]]; then
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "HELP!  Error authenticating cloud services";aplay "/tmp/ohgee_help.wav"
  exit 255
fi
nohup python ohgee.py &
exit 0
