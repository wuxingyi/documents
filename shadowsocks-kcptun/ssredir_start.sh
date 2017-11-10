#!/bin/bash

# This file is used to start the ss-redir application
# We will deploy the ss-server and ss-redir in same host
# ,so that we can transfer data in a round way, so we need to
# set two configuration files to ss-server and ss-redir indepently
# That means we have:
# /etc/shadowsocks-libev/config.json for ss-server, and
# /etc/shadowsocks-libev/redirect.json for ss-redir which two are in same format
# The original file could be find at https://github.com/shadowsocks/shadowsocks-libev

ss-redir -c /etc/shadowsocks-libev/redirect.json -u &
