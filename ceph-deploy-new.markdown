#new markdown for ceph-deploy

##Ceph-deploy 部署流程

##安装ceph-deploy

从github上下载代码，并安装，没有网络的机器可以下载相对较新的rpm包安装
http://download.ceph.com/rpm-hammer/el6/noarch/

##配置ceph-deploy

修改配置文件~/.cephdeploy.conf，添加以下内容，注意区分内外网机器的baseurl不同,
如果要上最新的hammer版本代码，要将URL路径里的ceph替换为ceph-hammer

    [ceph]
    name=ceph
    baseurl=http://115.182.93.170/ceph/el6/update/    
    #baseurl=http://10.200.93.170/ceph/el6/update/
    enabled=1
    gpgcheck=0
    default = True

##安装ceph

###前置条件：

admin节点要求可以免密码SSH登录到全部host节点
admin节点可以通过hostname访问host节点

###清理工作

    Ceph-deploy purge HOST [HOST..] //清理所有节点的安装包
    Ceph-deploy purgedata HOST [HOST..] //清理所有节点的残留ceph数据

###安装流程



asdfadsfasdfasdo

    ceph-deploy new MON [MON..]     //MON 为配置monitor的节点的hostname

完成后会在当前目录生成ceph.conf + ceph.mon.keyring

修改ceph.conf，添加相关内容

    [global]
    fsid = 82a1ab76-0de0-42ee-bf01-ec1910a78970
    mon_initial_members = test-96
    mon_host = 10.180.92.96
    auth_cluster_required = cephx
    auth_service_required = cephx
    auth_client_required = cephx
    filestore_xattr_use_omap = true
    mon_osd_down_out_interval = 900
    mon_osd_min_down_reporters = 6
    
    [osd]
    filestore_journal_writeahead = True
    osd_max_backfills = 2
    osd_recovery_max_chunk = 32M
    osd_heartbeat_interval = 60
    osd_backfill_scan_min = 16
    osd_recovery_max_active = 1
    filestore_op_threads = 4
    filestore_xattr_use_omap = False
    osd_recovery_threads = 1
    osd_backfill_scan_max = 256
    journal_queue_max_bytes = 32M
    journal_max_write_bytes = 32M
    osd_heartbeat_grace = 100
    osd_mkfs_options_xfs = "-i size=2048 -d su=64k -d sw=2"//请按需求加入这行

安装ceph包

    ceph-deploy install HOST [HOST..] // 安装ceph的rpm包，HOST 为全部部署节点的hostname

部署monitor

    ceph-deploy mon create   //要求部署2个mon以上，不然无法创建出ceph.client.admin.keyring

收集keyring

    ceph-deploy gatherkeys HOST [HOST...] //搜集上一步的keyring，HOST是MON的hostname

创建OSD

    ceph-deploy osd create [--no-partition | --zip-disk] HOST:DISK[:JOURNAL] [HOST:DISK[:JOURNAL] ...] //创建OSD,格式举例test-96:/dev/sdb,如果磁盘已经有分区，带上参数 --zap-disk，会自动重建分区PS:要求所有磁盘未使用，如果是LVM设备则必须带--no-partition, --no-partition与—zap-disk 不能同时使用

激活OSD

    ceph-deploy osd activate test-95:/dev/vg/lv2 //激活OSD,仅LVM设备需要执行这一步

关于自动挂载：

对于普通磁盘及RAID盘，重启可以自动挂载，但是对于DM设备无法达到自动挂载，必须在启动时添加脚本执行以下类似语句，且ceph-deploy也无法实现类似pupet的监控效果。

    ceph-disk -v activate --mark-init sysvinit --mount /dev/vg/lv1
    ceph-disk -v activate --mark-init sysvinit --mount /dev/vg/lv2
    ceph-disk -v activate --mark-init sysvinit --mount /dev/vg/lv3
    ceph-disk -v activate --mark-init sysvinit --mount /dev/vg/lv4
    ceph-disk -v activate --mark-init sysvinit --mount /dev/vg/lv5
    ceph-disk -v activate --mark-init sysvinit --mount /dev/vg/lv6

ceph tcp tunning
    net.core.rmem_max = 33554432
    net.core.wmem_max = 33554432
    net.core.rmem_default = 33554432
    net.core.wmem_default = 33554432
    net.core.optmem_max = 40960
    net.ipv4.tcp_rmem = 4096 87380 33554432
    net.ipv4.tcp_wmem = 4096 65536 33554432

    net.core.somaxconn = 1024
    net.core.netdev_max_backlog = 50000
    net.ipv4.tcp_max_syn_backlog = 30000
    net.ipv4.tcp_max_tw_buckets = 2000000
    net.ipv4.tcp_tw_reuse = 1
    net.ipv4.tcp_fin_timeout = 10

    
