#!/bin/bash
# Use whatever means to turn the screen off
sudo sh -c 'echo "0" > /sys/class/backlight/soc\:backlight/brightness'
echo "sleeping display"
pico2wave -l en-US --wave "/tmp/ohgee_online.wav" "Sleeping";aplay "/tmp/ohgee_online.wav"
exit 0
