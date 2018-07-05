#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT="$( basename $0 )"
ping -c 5 www.google.com  1>/dev/null 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then
  logger "$0 ping failed"
  /usr/bin/pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "help!  no network";/usr/bin/aplay "/tmp/ohgee_help.wav"
  /usr/bin/pico2wave -l en-US --wave "/tmp/ohgee_help.wav" "Rebooting";/usr/bin/aplay "/tmp/ohgee_help.wav"
  logger "$0 is rebooting"
  sudo reboot
  exit 255
else
  jobcount=0
  for job in $(at -l | awk '{print $1}'); do
    pending="$(at -c ${job} | grep ${SCRIPT})"
    if [[ -n "${pending}" ]]; then
      jobcount=$(( jobcount + 1 ))
    fi
  done
  if [[ ${jobcount} -le 1 ]]; then
    echo "${DIR}/${SCRIPT}" | at now + 2 minutes
  fi
  exit 0
fi
