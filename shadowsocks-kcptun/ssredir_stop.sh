#!/bin/bash
# This file is used to find out the ss-redir process id and kill it
# Since the ss-redir runs in the background, so we need 
# to finish it in this way

kill $(ps aux | grep '[s]s-redir' | awk '{print $2}')