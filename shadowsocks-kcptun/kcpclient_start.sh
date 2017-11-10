#!/bin/bash

# This file is used to start the kcptun client, and run it in the background
# Related information about KCPtun could be found at https://github.com/xtaci/kcptun

KCP_LOCAL=/usr/local/Kcptun
KCP_CLIENT_NAME=client_linux_amd64
CLIENT=$KCP_LOCAL$KCP_CLIENT_NAME
SERVER_IP=$1

# Ensure we have at least one arguement
if (( $# < 1 ));then
        echo -e "Error! Please input the server ip"
        exit -1
fi

# check if kcp client application exists, quit immediately if not
if [ -e $KCP_LOCAL/client_linux_amd64 ];then 
	echo "client exists, start it..."
else
	echo -e "client application doesn't exsits, please download it"
	exit -1
fi

# Since we have checked existence of client application, start it in some mode
# Parameters can be found if we run:
# $ ./client_darwin_amd64 -h
# Some important parameters are:
# --localaddr value, -l value      local listen address (default: ":12948")
# --remoteaddr value, -r value     kcp server address (default: "vps:29900")
# --mode value                     profiles: fast3, fast2, fast, normal (default: "fast")
# --sndwnd value                   set send window size(num of packets) (default: 128)
# --rcvwnd value                   set receive window size(num of packets) (default: 512)
# --datashard value, --ds value    set reed-solomon erasure coding - datashard (default: 10)
# --parityshard value, --ps value  set reed-solomon erasure coding - parityshard (default: 3)

$KCP_LOCAL/client_linux_amd64 -l 127.0.0.1:1090 -r $SERVER_IP:21 --crypt none --mtu 1200 --nocomp --mode normal --datashard 0 --parityshard 0 --dscp 46 --log clientlog &
