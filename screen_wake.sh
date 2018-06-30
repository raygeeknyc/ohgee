#!/bin/bash
# Use whatever means to turn the screen on
vcgencmd display_power 1
gpio -g write 23 1
pico2wave -l en-US --wave "/tmp/ohgee_online.wav" "Waking";aplay "/tmp/ohgee_online.wav"
exit 0
