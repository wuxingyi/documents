# Pre-check
## Check ss and kcptun
	1. Check if shadowsocks-libev installed, runs:
		rpm -ql shadowsocks-libev
		make sure we have ss-server and ss-redir installed.

	2. Check if shadowsocks server runs well, runs:
		systemctl status shadowsocks-libev
		shadowsocks-libev should run well without any fails.

	3. Check if configuration for shadowsocks-libev good:
		/etc/shadowsocks-libev/config.json
		/etc/shadowsocks-libev/redirect.json

	4. Check if Kcptun applications exist:
		/usr/local/Kcptun/client_linux_amd64
		/usr/local/Kcptun/server_linux_amd64
	   and:
	   	/usr/local/Kcptun/kcpclient_start.sh
	   	/usr/local/Kcptun/kcpclient_stop.sh
	   	/usr/local/Kcptun/kcpserver_start.sh
	   	/usr/local/Kcptun/kcpserver_stop.sh
	   	/usr/local/Kcptun/ssredir_start.sh
	   	/usr/local/Kcptun/ssredir_stop.sh

## Check iptables
	Check iptables if good:
	iptables -t nat --list
	There should be a bunch of SHADOWSOCKS contents, which means we will transfer all tcp request, whose dest ip equals to server ip, to ss-redir's port
	See details in file iptables-rules

# Run
## cd /usr/local/Kcptun/, and:
	1. Run kcp servers:
		./kcpserver_start.sh
	2. Run kcp client:
		./kcpclient_start.sh ${server_ip}
	3. Run ss-redir:
		./ssredir_start.sh

# Stop applications
	Run /usr/local/Kcptun/kcpserver_stop.sh to stop the kcpserver
	Run /usr/local/Kcptun/kcpclient_start.sh to stop the kcpclient
	Run /usr/local/Kcptun/ssredir_stop.sh to stop the ssredir

# Some issues
## In clientlog we can see some log "session expired"
	check if as link said "https://github.com/xtaci/kcptun/issues/429"
	check iptables and firewall
	check if some parameters in the kcpserver_start.sh and kcpclient_start.sh are same
	especially with:
	-nocomp, -datashard, -parityshard, -key, -crypt
	
