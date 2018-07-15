#!/bin/bash
# Reboot
pico2wave -l en-US --wave "/tmp/ohgee_reboot.wav" "rebooting";aplay "/tmp/ohgee_reboot.wav"
sudo reboot
exit 0
