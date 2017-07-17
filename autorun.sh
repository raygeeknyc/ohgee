#!/bin/bash
./setup_auth.sh 2>&1
nohup python ohgee.py &
