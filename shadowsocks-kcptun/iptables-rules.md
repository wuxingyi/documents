# This script is used to set iptables ruls for ss-redir
# There are little differences with https://github.com/shadowsocks/shadowsocks-libev
# We will deploy a round-trip communication environment, since we wish to be able to
# send and receive data from server and client in the same time

# Create new chain
root@Wrt:~# iptables -t nat -N SHADOWSOCKS
root@Wrt:~# iptables -t mangle -N SHADOWSOCKS

# Ignore your shadowsocks server's addresses
# It's very IMPORTANT, just be careful.
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d ${server ip} -j RETURN

# Ignore LANs and any other addresses you'd like to bypass the proxy
# See Wikipedia and RFC5735 for full list of reserved networks.
# See ashi009/bestroutetb for a highly optimized CHN route list.
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 0.0.0.0/8 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 10.0.0.0/8 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 127.0.0.0/8 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 169.254.0.0/16 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 172.16.0.0/12 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 192.168.0.0/16 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 224.0.0.0/4 -j RETURN
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -d 240.0.0.0/4 -j RETURN

# Anything else should be redirected to shadowsocks's local port
root@Wrt:~# iptables -t nat -A SHADOWSOCKS -p tcp -j REDIRECT --to-ports 12345

# Add any UDP rules
root@Wrt:~# ip route add local default dev lo table 100
root@Wrt:~# ip rule add fwmark 1 lookup 100
root@Wrt:~# iptables -t mangle -A SHADOWSOCKS -p udp --dport 53 -j TPROXY --on-port 12345 --tproxy-mark 0x01/0x01

# Apply the rules
root@Wrt:~# iptables -t nat -A PREROUTING -p tcp -d ${specific ips} -j SHADOWSOCKS
root@Wrt:~# iptables -t mangle -A PREROUTING -d ${specific ips} -j SHADOWSOCKS

# Start the shadowsocks-redir
root@Wrt:~# ss-redir -u -c /etc/config/shadowsocks.json -f /var/run/shadowsocks.pid