#!/bin/bash

# This file is used to start the kcptun service in the background,
# and the process could be killed by run:
# ./kcpserver_stop.sh
# Related information about KCPtun could be found at https://github.com/xtaci/kcptun

KCP_LOCAL=/usr/local/Kcptun
KCP_SERVER_NAME=server_linux_amd64
SERVER=$KCP_LOCAL$server_linux_amd64

# check if kcp server application exists, quit immediately if not
if [ -e $SERVER ];then 
	echo "server exists, start it..."
else
	echo -e "server doesn't exsits, please download it"
	exit -1
fi

# Since we have checked existence of server application, start it in some mode
# Parameters can be found if we run:
# $ ./server_darwin_amd64 -h
# Some important parameters are:
# --listen value, -l value         kcp server listen address (default: ":29900")
# --target value, -t value         target server address (default: "127.0.0.1:12948")
# --mode value                     profiles: fast3, fast2, fast, normal (default: "fast")
# --sndwnd value                   set send window size(num of packets) (default: 1024)
# --rcvwnd value                   set receive window size(num of packets) (default: 1024)
# --datashard value, --ds value    set reed-solomon erasure coding - datashard (default: 10)
# --parityshard value, --ps value  set reed-solomon erasure coding - parityshard (default: 3)

$KCP_LOCAL/server_linux_amd64 -l :21 -t 127.0.0.1:8388 --crypt none --mtu 1200 --nocomp --mode normal --datashard 0 --parityshard 0 --dscp 46 --sndwnd 4096 --rcvwnd 4096 --log serverlog &
