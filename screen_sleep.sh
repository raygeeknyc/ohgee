#!/bin/bash
# Use whatever means to turn the screen off
vcgencmd display_power 0
gpio -g write 23 0
echo "sleeping display"
pico2wave -l en-US --wave "/tmp/ohgee_online.wav" "Sleeping";aplay "/tmp/ohgee_online.wav"
exit 0
