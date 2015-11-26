#准备环境

## 准备/etc/hosts

## 规划网络，分为public_network 和 cluster_network

## 增加ceph的yum repo

编辑文件/etc/yum.repos.d/ceph.repo

    [ceph-updates]
    gpgcheck=0
    enabled=1
    name=Letv Cloud's Ceph packages
    priority=1
    baseurl=http://10.200.93.170/ceph/el6/update/
    [letv-ceph]
    gpgcheck=0
    enabled=1
    name=Letv Cloud's Ceph packages
    priority=1
    baseurl=http://10.200.93.170/ceph/el6/update/

## 配置ntp

    就算是配置好了ntp服务，经过长时间运行，系统也可能出现时钟skew的情况，此时重启ntp服务即可

## 增加新用户cephadmin

    ssh root@ceph-server
    useradd -d /home/cephadmin -m cephadmin
    passwd cephadmin

    echo "cephadmin ALL = (root) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/cephadmin
    chmod 0440 /etc/sudoers.d/cephadmin

## 配置用户cephadmin ssh无密码登陆

## 打开防火墙

* 端口 6789 用于monitor
* 端口 6800:7100 用于osd

## 禁用SELINUX

    sudo setenforce 0

# 安装monitor节点

    yum install ceph-deploy


## 开始配置ceph.conf
    
    
    su - cephadmin
    mkdir mycluster

此后所有操作都用cephadmin用户在mycluster下进行
    
    ceph-deploy new 初始moniter节点
    
## 修改ceph.conf文件


如果确定osd的文件系统是xfs, filestore xattr use omap 为false. 同时filestore journal writeahead为true

如果使用自定义的crushmap, 设置osd crush update on start = false

如果使用osd-domain, 设置osd crush chooseleaf type = {osd-domain-num}


    [global]
    auth service required = cephx
    filestore xattr use omap = true
    auth client required = cephx
    auth cluster required = cephx
    mon host = 10.182.200.24,10.182.200.78,10.182.200.77
    mon initial members = <初始moniter节点>
    fsid = ee4ea70c-093f-4797-8d3d-871c0aacc92b
    osd pool default size = 3
    osd pool default min size = 2
    osd pool default pg num = 128
    osd pool default pgp num = 128
    public network = x.x.x.x/x
    cluster network = x.x.x.x/x

    [mon]
    mon compact on start = true
    
    [osd]
    osd max backfills = 1
    osd backfill scan min = 16
    osd backfill scan max = 256
    filestore op threads = 4
    osd recovery max active = 1
    osd recovery max chunk = 32M
    osd recovery threads = 1
    journal max write bytes = 32M
    journal queue max bytes = 32M
    mon osd down out interval  = 900
    osd heartbeat interval = 180
    osd heartbeat grace = 360



## 根据之前会议的结论，每台机器是10 HDD（两两做RAID 0） + 2 SSD, ssd做journal，其中一块SSD作为2个OSD的journal，另一块作为3个OSD的journal：

## 如果使用使用ssd做journal，则每个host上的ceph.conf都略有不同，因为journal的配置是针对每个osd的：

    #将osd.x的日志的位置设置为/data/slotb/journal_x
    [osd.x]
        osd_journal = /data/slotb/journal_x
        

## 安装monitor节点
    
    ceph-deploy mon create-initial
    
## 推送admin keyring到所有节点
    
    sudo chmod +r /etc/ceph/ceph.client.admin.keyring
    ceph-deploy admin <所有节点>

保留mycluster文件架，为以后自动添加monitor节点准备

## 检查
    
    ceph -s

状态是HEALTH_ERR,无osd，mon节点都已经加入



# 手动安装OSD节点


所有osd节点用手动安装的方式, 使用root用户

创建osd号
    
    ceph osd create

返回一个数字，这个数字就是osd的唯一号,记录为{osd-number}

    ceph osd tree

检查出现osd.{osd-number},状态是down.

准备ceph osd文件夹
    
    mkdir /var/lib/ceph/osd/ceph-{osd-number}
    #如果是普通硬盘
    mkfs -t xfs -i size=2048 /dev/disk
    #如果是RAID0
    mkfs -t xfs -i size=2048 -d su=64k -d sw=2 /dev/disk
    mount -o noatime,nodiratime,inode64 /dev/disk /var/lib/ceph/osd/ceph-{osd-number}

在文件夹内建立osd keyring等数据
    
    ceph-osd -i {osd-num} --mkfs --mkkey

检查文件夹/var/lib/ceph/osd/ceph-{osd-number}内容, 并建立sysvinit

    touch  /var/lib/ceph/osd/ceph-{osd-number}/sysvinit

添加osd权限

    ceph auth add osd.{osd-num} osd 'allow *' mon 'allow rwx' -i /var/lib/ceph/osd/ceph-{osd-num}/keyring   
    
检查权限是否已经添加

    ceph auth list

检查osd列表
    
    ceph osd tree

启动ceph osd

    /etc/init.d/ceph start osd.{osd-number}

检查是否加入集群

    ceph osd tree
    ceph -s
    
注意事项：

    1.monitor节点一开始就使用ceph-deploy部署好三个，比后来手工加要简单得多
    2.采用手工部署时，为保证机器重启时osd能够也随之重启，需要根据mount参数修改启动脚本，对osd相关目录进行挂载
    3.部署完成后，添加自动启动：chkconfig ceph on
    4.使用的ceph版本应该由前面提到的源提供
    5.配置一个monitor节点到所有其他节点免密码登陆
    
