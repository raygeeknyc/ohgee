#!/bin/bash
logger "autostart of ohgeetoo"
cd Documents/workspace/ohgee;pwd;./autorun.sh > /var/log/ohgee.out 2>&1
