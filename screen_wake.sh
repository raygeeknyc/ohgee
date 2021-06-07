#!/bin/bash
# Use whatever means to turn the screen on
sudo sh -c 'echo "1" > /sys/class/backlight/soc\:backlight/brightness'
echo "waking display"
pico2wave -l en-US --wave "/tmp/ohgee_online.wav" "Waking";aplay "/tmp/ohgee_online.wav"
exit 0
