# 在ceph jewel上快速部署rgw

## 0. 部署好ceph集群
## 1. 创建相关pool

```
ceph osd pool create .rgw.root 8 8 rack
ceph osd pool create default.rgw.control 8 8 rack
ceph osd pool create default.rgw.data.root 8 8 rack
ceph osd pool create default.rgw.gc 8 8 rack
ceph osd pool create default.rgw.log 8 8 rack
ceph osd pool create default.rgw.users.uid 8 8 rack
ceph osd pool create default.rgw.users.email 8 8 rack
ceph osd pool create default.rgw.users.keys 8 8 rack
ceph osd pool create default.rgw.meta 8 8 rack
ceph osd pool create default.rgw.users.swift 8 8 rack
```

## 2. 创建admin的keyring和日志目录
```
sudo ceph-authtool --create-keyring /etc/ceph/ceph.client.radosgw.keyring
sudo chmod +r /etc/ceph/ceph.client.radosgw.keyring
sudo ceph-authtool /etc/ceph/ceph.client.radosgw.keyring -n client.radosgw.gateway --gen-key
sudo ceph-authtool -n client.radosgw.gateway --cap osd 'allow rwx' --cap mon 'allow rwx' /etc/ceph/ceph.client.radosgw.keyring
sudo ceph -k /etc/ceph/ceph.client.admin.keyring auth add client.radosgw.gateway -i /etc/ceph/ceph.client.radosgw.keyring
mkdir /var/log/radosgw
```

## 3. 更新ceph.conf中rgw的配置
```
[client.radosgw.gateway]
host = hainan-haikou-rgw-106-242 #需要根据hostname更改
rgw dns name = s3.hnaobjs.com    #需要根据域名更改
#rgw reserved origin = cn-north-1.console.lecloud.com 10.112.32.159 cn-test-1.console.lecloud.com
keyring = /etc/ceph/ceph.client.radosgw.keyring
#rgw socket path = /var/run/ceph/ceph.radosgw.gateway.fastcgi.sock
log file = /var/log/radosgw/client.radosgw.gateway.log
rgw_thread_pool_size = 2000
rgw_num_async_rados_threads = 32
rgw frontends = civetweb port=8080 request_timeout_ms=30000 access_log_file=/var/log/radosgw/access.log
rgw_override_bucket_index_max_shards = 16

```

## 4. 启动服务 
```
systemctl enable ceph-radosgw@radosgw.gateway
systemctl start ceph-radosgw@radosgw.gateway
```

## 5. 创建一个admin用户
```
radosgw-admin user create --uid=admin --display-name=admin --email=admin@admin.com --system

```

## 6. 来一个s3cmd的配置文件, 并通过s3cmd验证配置。为支持泛域名，需要改dnsmasq和resolv.onf。

```
[default]
 access_key = N8E1K384YS5CV6RB4CAY
 secret_key = TnDmwfs07m1VgevieeWG83TqX1NrTHUGgXuRcaPi
 default_mime_type = binary/octet-stream
 enable_multipart = True
 encoding = UTF-8
 encrypt = False
 host_base = s3.hnaobjs.com
 host_bucket = %(bucket)s.s3.hnaobjs.com
 use_https = False
```


## 7.配置负载均衡haproxy服务
```
#---------------------------------------------------------------------
# Example configuration for a possible web application.  See the
# full configuration options online.
#
#   http://haproxy.1wt.eu/download/1.4/doc/configuration.txt
#
#---------------------------------------------------------------------

#---------------------------------------------------------------------
# Global settings
#---------------------------------------------------------------------
global
    # to have these messages end up in /var/log/haproxy.log you will
    # need to:
    #
    # 1) configure syslog to accept network log events.  This is done
    #    by adding the '-r' option to the SYSLOGD_OPTIONS in
    #    /etc/sysconfig/syslog
    #
    # 2) configure local2 events to go to the /var/log/haproxy.log
    #   file. A line like the following can be added to
    #   /etc/sysconfig/syslog
    #
    #    local2.*                       /var/log/haproxy.log
    #
    log         127.0.0.1 local2

    chroot      /var/lib/haproxy
    pidfile     /var/run/haproxy.pid
    maxconn     4000
    user        haproxy
    group       haproxy
    daemon

    # turn on stats unix socket
    stats socket /var/lib/haproxy/stats

#---------------------------------------------------------------------
# common defaults that all the 'listen' and 'backend' sections will
# use if not designated in their block
#---------------------------------------------------------------------
defaults
    mode                    http
    log                     global
    option                  httplog
    option                  dontlognull
    option http-server-close
    option forwardfor       except 127.0.0.0/8
    option                  redispatch
    retries                 3
    timeout http-request    10s
    timeout queue           1m
    timeout connect         10s
    timeout client          1m
    timeout server          1m
    timeout http-keep-alive 10s
    timeout check           10s
    maxconn                 3000

#---------------------------------------------------------------------
# main frontend which proxys to the backends
#---------------------------------------------------------------------
frontend  rgw-frontend
    bind 10.48.109.19:80
    default_backend             rgw-backend


#---------------------------------------------------------------------
# static backend for serving up images, stylesheets and such
#---------------------------------------------------------------------
backend static
    balance     roundrobin
    server      static 127.0.0.1:4331 check

#---------------------------------------------------------------------
# round robin balancing between the various backends
#---------------------------------------------------------------------
backend rgw-backend
    balance     roundrobin
    server  rgw1 10.48.106.242:8080 check
    server  rgw2 10.48.106.244:8080 check
```

## 8.配置keepalived服务(两个机器稍微有不同，需要改state和priority)
```
global_defs {
   notification_email {
    wuxingyi2015@outlook.com
   }
   notification_email_from wuxingyi2015@outlook.com
   smtp_server 127.0.0.1
   smtp_connect_timeout 30
   router_id LVS_DEVEL
}
vrrp_script chk_http_port {
                script "/etc/keepalived/check_haproxy.sh"
                interval 2
                weight 2
}
vrrp_instance VI_1 {
    state MASTER        ############ 辅机为 BACKUP
    interface bond0.1609
    virtual_router_id 51
    priority 150                  ########### 权值要比 back 高
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass 1111
    }
track_script { 
        chk_http_port ### 执行监控的服务 
        }
    virtual_ipaddress {
       10.48.109.19
    }
}

```

## 9. 添加```/etc/keepalived/check_haproxy.sh```文件：
```
#!/bin/bash
if [ $(ps -C haproxy --no-header | wc -l) -eq 0 ]; then
     systemctl restart haproxy
fi
sleep 2
if [ $(ps -C haproxy --no-header | wc -l) -eq 0 ]; then
       /etc/init.d/keepalived stop
fi

```

## 10. enable和启动相关服务
```
systemctl disable NetworkManger 
systemctl enable keepalived.service 
systemctl enable haproxy
systemctl start keepalived.service 
systemctl start haproxy
```

## 11. 验证服务
可通过curl验证，不赘述。
