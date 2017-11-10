#!/bin/bash
# This file is used to find out the kcp client process id and kill it
# Since the kcp application client runs in the background, so we need 
# to finish it in this way

kill $(ps aux | grep '[c]lient_linux_amd64' | awk '{print $2}')