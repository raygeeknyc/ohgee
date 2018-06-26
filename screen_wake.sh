#!/bin/bash
# Use whatever means to turn the screen on
vcgencmd display_power 1
gpio -g write 23 1
exit 0
