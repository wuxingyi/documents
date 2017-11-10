#!/bin/bash
# This file is used to find out the kcp server process id and kill it
# Since the kcp application server runs in the background, so we need 
# to finish it in this way

kill $(ps aux | grep '[s]erver_linux_amd64' | awk '{print $2}')
