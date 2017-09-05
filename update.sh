#!/bin/bash
git pull
#sudo apt-get -y --force-yes install python-imaging-tk
#sudo pip install --upgrade google-api-python-client
pico2wave -l en-US --wave "/tmp/ohgee_update.wav" "updated";aplay "/tmp/ohgee_update.wav"
sudo echo "display_rotate=2" >> /boot/config.txt
pico2wave -l en-US --wave "/tmp/ohgee_update.wav" "Display rotate installed";aplay "/tmp/ohgee_update.wav"

