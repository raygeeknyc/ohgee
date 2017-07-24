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
pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "installing";aplay "/tmp/ohgee_help.wav"
if [[ $rc -ne 0 ]]; then
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "help!  no network";aplay "/tmp/ohgee_help.wav"
  echo "sudo reboot" | at now + 1 hour
  pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "Reboot in one hour";aplay "/tmp/ohgee_help.wav"
  exit 255
fi
echo "updating"
./update.sh
if [[ -z "$DISPLAY" ]];then
  export DISPLAY=":0.0"
fi
./setup_auth.sh 2>&1
nohup python ohgee.py &
