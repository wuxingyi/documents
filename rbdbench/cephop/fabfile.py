from fabric.api import *
from fabric.contrib.files import append
import time
import os
import socket

#diskprofile#
diskprofile = "raid0"

#monhostnames#

#osdhostnames#
env.hosts = ["compute-96-10","compute-96-11","compute-96-12","compute-96-13","compute-96-14","compute-96-15","compute-96-16","compute-96-17","compute-96-18","compute-96-19","compute-96-20","compute-96-21","compute-96-22","compute-96-23","compute-96-24","compute-96-25","compute-96-26","compute-96-27","compute-96-28","compute-96-29","compute-96-30","compute-96-31","compute-96-32","compute-96-33","compute-96-34","compute-96-35","compute-96-36","compute-96-37","compute-96-38","compute-96-39","compute-96-40","compute-96-41","compute-96-42","compute-96-43","compute-96-44","compute-96-45","compute-96-46","compute-96-47","compute-96-48","compute-96-49"]

no33 = ["compute-96-10","compute-96-11","compute-96-12","compute-96-13","compute-96-14","compute-96-15","compute-96-16","compute-96-17","compute-96-18","compute-96-19","compute-96-20","compute-96-21","compute-96-22","compute-96-23","compute-96-24","compute-96-25","compute-96-26","compute-96-27","compute-96-28","compute-96-29","compute-96-30","compute-96-31","compute-96-32","compute-96-34","compute-96-35","compute-96-36","compute-96-37","compute-96-38","compute-96-39","compute-96-40","compute-96-41","compute-96-42","compute-96-43","compute-96-44","compute-96-45","compute-96-46","compute-96-47","compute-96-48","compute-96-49"]
firstten = ["compute-96-10","compute-96-11","compute-96-12","compute-96-13","compute-96-14","compute-96-15","compute-96-16","compute-96-17","compute-96-18","compute-96-19"]
firstone = ["compute-96-10"]
firstfive = ["compute-96-10","compute-96-11","compute-96-12","compute-96-13","compute-96-14"]
firstfifteen = ["compute-96-10","compute-96-11","compute-96-12","compute-96-13","compute-96-14","compute-96-15","compute-96-16","compute-96-17","compute-96-18","compute-96-19", "compute-96-20","compute-96-21","compute-96-22","compute-96-23","compute-96-24"]
first20 = ["compute-96-10","compute-96-11","compute-96-12","compute-96-13","compute-96-14","compute-96-15","compute-96-16","compute-96-17","compute-96-18","compute-96-19", "compute-96-20","compute-96-21","compute-96-22","compute-96-23","compute-96-24", "compute-96-25","compute-96-26","compute-96-27","compute-96-28","compute-96-29"]

rackq3 = ["compute-96-27","compute-96-28","compute-96-29","compute-96-30","compute-96-31","compute-96-32","compute-96-33","compute-96-34", "compute-96-35"]
only33 = ["compute-96-33"]
only26 = ["compute-96-26"]

def push_key(key_file='/root/.ssh/id_rsa.pub'):
    key_text = read_key_file(key_file)
    run('chattr -i /root/.ssh/authorized_keys')
    append('/root/.ssh/authorized_keys', key_text);

def read_key_file(key_file):
    key_file = os.path.expanduser(key_file)
    if not key_file.endswith('pub'):
        raise RuntimeWarning('Trying to push non-public part of key pair')
    with open(key_file) as f:
        return f.read()

def updateRepoAddress():
    put('./deployFile/resolv.conf','/etc/resolv.conf')
    run('rm /etc/yum.repos.d/letv-pkgs.repo /etc/yum.repos.d/CentOS.repo -f')
    put('./deployFile/CentOS-Base.repo','/etc/yum.repos.d/CentOS-Base.repo')
    put("./deployFile/ceph.repo","/etc/yum.repos.d/ceph.repo")
    put("./deployFile/watchtv.repo","/etc/yum.repos.d/watchtv.repo")

def testecho():
    run('rpm -qa|grep redhat-lsb-core || yum install redhat-lsb-core -y')
    run('echo hello')

def PurgeCeph():
    local('ceph-deploy purge %s' % env.host)
    local('ceph-deploy purgedata %s' % env.host)
    run('yum remove ceph ceph-common ceph-devel librados2 libcephfs1 python-ceph librbd1 ceph-test  libcephfs_jni1 libcephfs_jni1 libradosstriper1  librbd1 ceph-radosgw  ceph-libs-compat cephfs-java  libcephfs1 rbd-fuse rbd-fuse rest-bench -y')

def InstallCeph():
    run('yum install -y ceph ceph-osd')
    run('echo "kernel.core_pattern = /letv/cores" >> /etc/sysctl.conf;sysctl -p')
    put('./deployFile/ceph-osd@.service', '/usr/lib/systemd/system/ceph-osd@.service')
    run('systemctl reload-daemon')

def DeployOSDs():
    # in rbd case, sdb/sdc/sdd share /dev/sdg as journal disk, sde/sdf share /dev/sdh as journal disk
    run('/usr/sbin/ceph-disk zap /dev/sdg /dev/sdh') 
    local('ceph-deploy osd create --zap-disk %s:/dev/sdb:/dev/sdg %s:/dev/sdc:/dev/sdg %s:/dev/sdd:/dev/sdg %s:/dev/sde:/dev/sdh %s:/dev/sdf:/dev/sdh' % (env.host,env.host,env.host,env.host,env.host))
def prepareDisks():
    if diskprofile == "raid0":
        run('umount /dev/sd{b,b1,c,c1,d,d1,e,e1,f,f1,g,g1,h,h1}')
    elif diskprofile == "noraid":
        run('yum install -y lvm2')
        run('umount /dev/sd{b,c,d,e,f,g,h,i,j,k,l,m}')
        run('pvcreate /dev/sd{b,c,d,e,f,g,h,i,j,k,l,m}')
        run('vgcreate vg /dev/sd{b,c,d,e,f,g,h,i,j,k,l,m}')
        run('lvcreate -l200%PVS -n lv1 vg /dev/sdb /dev/sdc')
        run('lvcreate -l200%PVS -n lv2 vg /dev/sdd /dev/sde')
        run('lvcreate -l200%PVS -n lv3 vg /dev/sdf /dev/sdg')
        run('lvcreate -l200%PVS -n lv4 vg /dev/sdh /dev/sdi')
        run('lvcreate -l200%PVS -n lv5 vg /dev/sdj /dev/sdk')
        run('lvcreate -l200%PVS -n lv6 vg /dev/sdl /dev/sdm')
        run('/sbin/mkfs.xfs -i size=2048 -f /dev/vg/lv1')
        run('/sbin/mkfs.xfs -i size=2048 -f /dev/vg/lv2')
        run('/sbin/mkfs.xfs -i size=2048 -f /dev/vg/lv3')
        run('/sbin/mkfs.xfs -i size=2048 -f /dev/vg/lv4')
        run('/sbin/mkfs.xfs -i size=2048 -f /dev/vg/lv5')
        run('/sbin/mkfs.xfs -i size=2048 -f /dev/vg/lv6')

def CopyCephConf():
    put('./ceph.client.admin.keyring','/etc/ceph/ceph.client.admin.keyring')

def updatecephconf():
    run('echo "osd crush update on start = false" >> /etc/ceph/ceph.conf')
    run('echo "[client]" >> /etc/ceph/ceph.conf')
    run('echo "admin socket = /var/run/ceph/rbd-client-""$""pid.asok" >> /etc/ceph/ceph.conf')

def updatentpconfig():
    put('./deployFile/ntpd', '/etc/sysconfig/ntpd')
    put('./deployFile/ntpd.service', '/etc/systemd/system/multi-user.target.wants/ntpd.service')

def updatefstab():
    run('sed -i "\/data\/slot/d" /etc/fstab')

def startdiamond():
    run('yum install diamond -y')
    put('./deployFile/diamond.conf', '/etc/diamond/diamond.conf')
    run('/etc/init.d/diamond start')
def installfio():
    run('yum install fio -y')
    run('yum downgrade fio -y')

def updatefio():
    put('../fio', '/usr/bin/fio')

def createrules():
    run('ceph osd crush rule create-simple $(hostname -s) $(hostname -s) osd firstn')

def createpools():
    run('ceph osd pool create $(hostname -s) 128 128 $(hostname -s)')

def createimage():
    run('rbd create -p $(hostname -s) --size $((100*1024)) --image-format 2 hehe2')

@hosts(*only26)
def benchsinglehost():
    run('fio -sync=1 -direct=1 -iodepth=32 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60  -pool=$(hostname -s) -rbdname=hehe2 -clientname=admin -group_reporting -name=mytest')

@hosts(*firstfifteen)
def benchcluster():
    #local('ceph osd pool create benchcluster 4096 4096 az1-1')
    #run('rbd create -p benchcluster --size $((100*1024)) --image-format 2 $(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=32 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchcluster -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*firstfive)
def radosbench():
    run('rados bench 300 write  -p radosbench -b 4096  --no-cleanup')

@hosts(*firstfive)
def benchq2cluster():
    #run('rbd create -p onlyq1 --size $((100*1024)) --image-format 2 $(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=32 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60  -pool=onlyq1 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')


@hosts(*no33)
def longrunbenchcluster():
    #local('ceph osd pool create benchcluster2 4096 4096 az1-1')
    #run('rbd create -p benchcluster2 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=4 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchcluster2 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*no33)
def longrunbenchcluster2():
    #local('ceph osd pool create benchcluster2 4096 4096 az1-1')
    run('rbd create -p benchcluster2 --size $((60*1024)) --image-format 2 $(hostname -s)$(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=4 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchcluster2 -rbdname=$(hostname -s)$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*no33)
def longrunbenchcluster3():
    #local('ceph osd pool create benchcluster2 4096 4096 az1-1')
    #run('rbd create -p benchcluster2 --size $((60*1024)) --image-format 2 $(hostname -s)$(hostname -s)$(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=4 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchcluster2 -rbdname=$(hostname -s)$(hostname -s)$(hostname -s) -clientname=admin -group_reporting -name=mytest')
@hosts(*no33)
def longrunbenchcluster4():
    #local('ceph osd pool create benchcluster2 4096 4096 az1-1')
    #run('rbd create -p benchcluster2 --size $((60*1024)) --image-format 2 $(hostname -s)$(hostname -s)$(hostname -s)$(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=4 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchcluster2 -rbdname=$(hostname -s)$(hostname -s)$(hostname -s)$(hostname -s) -clientname=admin -group_reporting -name=mytest')
@hosts(*no33)
def longrunbenchcluster5():
    #local('ceph osd pool create benchcluster2 4096 4096 az1-1')
#    run('rbd create -p benchcluster2 --size $((60*1024)) --image-format 2 $(hostname -s)$(hostname -s)$(hostname -s)$(hostname -s)$(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=4 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchcluster2 -rbdname=$(hostname -s)$(hostname -s)$(hostname -s)$(hostname -s)$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*firstfifteen)
def hostlevelbench():
    #local('ceph osd pool create benchcluster 4096 4096 az1-1')
    #run('rbd create -p hostlevelbench --size $((100*1024)) --image-format 2 $(hostname -s)')
    run('fio -sync=1 -direct=1 -iodepth=1 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=hostlevelbench -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')
    #run('rados bench 120 write  -p hostlevelbench -b 4096  --no-cleanup')

def getdate():
    run('date')

def updatecephconf():
    put('ceph.conf', '/etc/ceph/ceph.conf')
def restartosds():
    run('systemctl restart ceph-osd.target')

#bench 200 images
@hosts(*firstone)
def create200images():
    for i in range(0,199):
        run('rbd create -p 200bench --size $((100*1024)) --image-format 2 image'  + str(i))

@hosts(*firstone)
def benchimages():
    for i in range(0,199):
        run('fio -sync=1 -direct=1 -iodepth=1 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=100G -numjobs=1 -run time=60 -pool=200bench -rbdname=image' + str(i) + ' -clientname=admin -group_reporting -name=mytest')

@hosts(*firstten)
def benchq5():
    #run('rbd create -p onlyq5 --size $((100*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=14 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=onlyq5 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*firstten)
def benchq2():
    #run('rbd create -p onlyq2 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=28 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=onlyq2 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')
@hosts(*firstten)
def benchq1():
    #run('rbd create -p benchonlyq1 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=28 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchonlyq1 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*firstten)
def benchq3():
    #run('rbd create -p benchonlyq3_3 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=20 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchonlyq3_3 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*firstten)
def benchq4():
    #run('rbd create -p benchonlyq4 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=20 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=benchonlyq4 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*only33)
def bench33():
    #run('rbd create -p compute-96-33-2 --size $((60*1024)) --image-format 2 hehe2')
    run('fio -sync=1 -direct=1 -iodepth=32 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=compute-96-33-2 -rbdname=hehe2 -clientname=admin -group_reporting -name=mytest')

def getcache():
    run(' /opt/MegaRAID/MegaCli/MegaCli64  -LDGetProp -Cache -LALL  -a0')

@hosts(*firstten)
def benchq3without33():
#    run('rbd create -p onlyq3_3 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=20 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -run time=60 -pool=onlyq3_3 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')






@hosts(*firstten)
def rackbenchq1():
    #run('rbd create -p rackbench1 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=22 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -runtime=60 -pool=rackbench1 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')
@hosts(*firstten)
def rackbenchq2():
    #run('rbd create -p rackbench2 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=18 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -runtime=60 -pool=rackbench2 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')

@hosts(*firstten)
def rackbenchq3():
    #run('rbd create -p rackbench3 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=21 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -runtime=60 -pool=rackbench3 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')
@hosts(*firstten)
def rackbenchq4():
    #run('rbd create -p rackbench4 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=20 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -runtime=60 -pool=rackbench4 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')
@hosts(*firstten)
def rackbenchq5():
    #run('rbd create -p rackbench5 --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=10 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -runtime=60 -pool=rackbench5 -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')


@hosts(*firstfifteen)
def finalbench():
    #run('rbd create -p finalbench --size $((60*1024)) --image-format 2 $(hostname -s)')
    run('fio -iodepth=40 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=60G -numjobs=1 -runtime=60 -pool=finalbench -rbdname=$(hostname -s) -clientname=admin -group_reporting -name=mytest')
