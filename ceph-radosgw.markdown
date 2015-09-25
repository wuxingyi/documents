
http://docs.ceph.com/docs/master/install/install-ceph-gateway/ 官方的配置文档
详细步骤指南


安装apache和fastcgi

        sudo yum install httpd mod_fastcgi
        sudo vim /etc/httpd/conf/httpd.conf


修改/etc/init.d/httpd文件

改为HTTPD=/usr/sbin/httpd.worker, 用线程模型启动

修改/etc/httpd/conf/httpd.conf

	LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
	LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %D" combined

在日志中记录响应时间

重启Apache服务

        sudo /etc/init.d/httpd restart

安装SSL（勿信官方文档）

先安装mod_ssl和openssl

        sudo yum install mod_ssl openssl,后续操作参考：http://wiki.centos.org/HowTos/Https

为支持https访问，请参考第15步的操作，添加443端口的相关字段。
安装守护进程

        sudo yum install ceph-radosgw ceph

建立radosgw的pool

        .rgw
        .rgw.root
        .rgw.control
        .rgw.gc
        .rgw.buckets
        .rgw.buckets.index
        .log
        .intent-log
        .usage
        .users
        .users.email
        .users.swift
        .users.uid

单节点配置（多节点配置请参考官方文档）（另：若ceph_mon已经配置好，osd节点配置时可略过9、10两步）

生成keyring：

        sudo ceph-authtool --create-keyring /etc/ceph/ceph.client.radosgw.keyring
        sudo chmod +r /etc/ceph/ceph.client.radosgw.keyring

生成user和key，并添加权限

        sudo ceph-authtool /etc/ceph/ceph.client.radosgw.keyring -n client.radosgw.gateway --gen-key
        sudo ceph-authtool -n client.radosgw.gateway --cap osd 'allow rwx' --cap mon 'allow rwx' /etc/ceph/ceph.client.radosgw.keyring

将key添加到ceph集群

    sudo ceph -k /etc/ceph/ceph.client.admin.keyring auth add client.radosgw.gateway -i /etc/ceph/ceph.client.radosgw.keyring
    注：若提示gateway已存在而keyring不匹配，删除client.radosgw.gateway
    ceph auth del client.radosgw.gateway

在各节点ceph.conf添加如下内容（替换{}为当前机器的hostname）：

    [client.radosgw.gateway]
    host = {hostname}
    keyring = /etc/ceph/ceph.client.radosgw.keyring
    rgw socket path = /var/run/ceph/ceph.radosgw.gateway.fastcgi.sock
    log file = /var/log/radosgw/client.radosgw.gateway.log
    rgw enable usage log = true
    rgw usage log tick interval = 30
    rgw usage log flush threshold = 1024
    rgw usage max shards = 32
    rgw usage max user shards = 1


添加gateway脚本s3gw.fcgi于/var/www/html

    #!/bin/sh
    exec /usr/bin/radosgw -c /etc/ceph/ceph.conf -n client.radosgw.gateway
    sudo chmod +x s3gw.fcgi
    sudo chown apache:apache s3gw.fcgi


建立文件目录

    sudo mkdir -p /var/lib/ceph/radosgw/ceph-radosgw.gateway
    sudo chown apache:apache /var/lib/ceph/radosgw/

添加rgw.conf于 /etc/httpd/conf.d （修改ServerName，ServerAdmin）

        FastCgiExternalServer /var/www/html/s3gw.fcgi -socket /var/run/ceph/ceph.radosgw.gateway.fastcgi.sock
        <VirtualHost *:80>
        ServerName ceph_mon
        ServerAdmin root
        DocumentRoot /var/www/html
        RewriteEngine On
        RewriteRule ^/(.*) /s3gw.fcgi?%{QUERY_STRING} [E=HTTP_AUTHORIZATION:%{HTTP:Authorization},L]

        <IfModule mod_fastcgi.c>
        <Directory /var/www/html>
        Options +ExecCGI
        AllowOverride All
        SetHandler fastcgi-script
        Order allow,deny
        Allow from all
        AuthBasicAuthoritative Off
        </Directory>
        </IfModule>

        AllowEncodedSlashes On
        ErrorLog /var/log/httpd/error.log
        CustomLog /var/log/httpd/access.log combined
        ServerSignature Off

        </VirtualHost>
修改/etc/httpd/conf.d/fastcgi.conf
将里面的FastCgiWrapper 改为 off
修改Path权限

        sudo chown apache:apache /var/run/ceph
        sudo chown apache:apache /var/log/radosgw/
        getenforce
        sudo setenforce 0


启动radosgw

        sudo /etc/init.d/httpd restart
        sudo /etc/init.d/ceph-radosgw start
        sudo chkconfig ceph-radosgw on


建立用户，增加Access Key，增加权限，配置使用User Quota，Bucket Quota（替换{}里的内容）

        radosgw-admin user create --uid={urID} --display-name="{urName}" --email={urEM}
        radosgw-admin key create --uid={urID}--key-type=s3 --gen-access-key --gen-secret
        radosgw-admin caps add --uid={urID} --caps="users=*"
        radosgw-admin quota set --quota-scope=user --uid={urID} --max-objects=1024 --max-size=1024
        radosgw-admin quota enable --quota-scope=user --uid={urID}
        radosgw-admin quota set --quota-scope=bucket--uid={urID} --max-objects=1024 --max-size=1024
        radosgw-admin quota enable --quota-scope=bucket --uid={urID}


s3cmd配置

        [default]
        access_key = SNR4XB2265AFASRD01AV
        secret_key = 1uqEmrBFvfx/oPhkiDH8/awQ84qecNzEnORsQvqp
        default_mime_type = binary/octet-stream
        enable_multipart = True
        encoding = UTF-8
        encrypt = False
        host_base = s3.lecloud.com
        host_bucket = %(bucket)s.s3.lecloud.com
        use_https = True
