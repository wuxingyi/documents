#准备环境

## 部署mds

ceph-deploy mds create {host-name}[:{daemon-name}] [{host-name}[:{daemon-name}] ...]

例如

ceph-deploy mds create host

## 创建cephfs文件系统

$ ceph osd pool create cephfs_data &lt;pg_num&gt;

$ ceph osd pool create cephfs_metadata &lt;pg_num&gt;

$ ceph fs new &lt;fs_name&gt; &lt;metadata&gt; &lt;data&gt;

例如

ceph osd pool create cephfs_data 4

ceph osd pool create cephfs_metadata 4

ceph fs new cephfs cephfs_metadata cephfs_data

## mount ceph fs as fuse

拷贝ceph配置文件和keyring

sudo mkdir -p /etc/ceph

sudo scp {user}@{server-machine}:/etc/ceph/ceph.conf /etc/ceph/ceph.conf

sudo scp {user}@{server-machine}:/etc/ceph/ceph.keyring /etc/ceph/ceph.keyring

sudo mkdir /home/usernname/cephfs

sudo ceph-fuse -m 192.168.0.1:6789 /home/username/cephfs

## 在docker中使用cephfs

docker run --privileged=true 方式运行容器

docker run --privileged=true --cap-add=ALL -it -v /dev:/dev -v /lib/modules:/lib/modules 方式运行容器