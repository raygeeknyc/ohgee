#!/bin/sh
gpio -g mode 13 Alt0
gpio -g mode 19 Alt5
#pulseaudio -k
#pulseaudio --start
#echo "disconnect 11:58:02:B4:02:50" | bluetoothctl
#echo "trust 11:58:02:B4:02:50" | bluetoothctl
#echo "connect 11:58:02:B4:02:50" | bluetoothctl
#sleep 2
#pacmd set-default-sink bluez_sink.11_58_02_B4_02_50
#pactl -- set-sink-volume 1 40%
