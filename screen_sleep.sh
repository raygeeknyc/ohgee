#!/bin/bash
# Use whatever means to turn the screen off
vcgencmd display_power 0
gpio -g write 23 0
exit 0
