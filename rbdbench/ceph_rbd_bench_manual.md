#ceph benchmark manual

1.创建一个新的目录cephop, 把刚部署完ceph的cephseed-rgw目录中把fabfile.py拷贝到cephop目录，后续都需要调动整个集群的所有存储节点，而做到这一点，仅仅需要在fabfile.py添加相应的函数即可。(```./cephop```中有一个```fabfile.py```样例)。

2.在所有节点上安装fio，注意版本号必须为我们自己编译打包的fio-2.13.1000(此包由ceph-jewel源提供)，epel提供的fio容易经常出现segment fault，不利于我们进行测试。

3.单机磁盘iops、吞吐测试：

通过测试单台服务器的每一块磁盘的iops和吞吐数据，得到每一台存储服务器能够提供的性能参数，另外也有利于尽早找出性能较差的磁盘并进行替换。

注意，在测试时通过```iostat -x 1```观察读写情况及磁盘使用率(%util)。

注意，测试必须在机器的每一块磁盘上同时进行，因为如果只跑在一块磁盘上，结果就是这一块盘独占RAID cache，这与我们实际跑IO时的情况是不一样的。
注意，在测试读时，请通过```echo 3 > /proc/sys/vm/drop_caches```清空page cache，否则在写完就进行读测试，读的全部都是page cache，结果毫无意义。

注意，在测试时，不要过大的增加iodepth等参数，否则延迟会达到无法接受的地步，可以确定一个标杆是99% io在延迟为12ms。进行fio测试时，不要看average的延迟，99%等数据。后续的所有使用fio进行的测试，都是使用这种指标进行的。

注意，因为SSD是采用裸盘的方式被osd当做journal使用，因此相关测试最好在ceph上线之前进行。

注意，因为RBD使用了巨大的raid cache，因此随机写iops要比读要好很多，不要被惊到。我这边测得随机写iops单盘能有1000左右，而随机读只有大概170左右。

3.1、单盘4k随机写iops

```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=randwrite -bs=4k -size=30G -numjobs=1 -runtime=300 -group_reporting  -name=test -filename=/var/lib/ceph/osd/ceph-$i/disktest/1.txt -ioengine=sync```

3.2、单盘4k随机读iops

```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=randread -bs=4k -size=30G -numjobs=1 -runtime=300 -group_reporting  -name=test -filename=/var/lib/ceph/osd/ceph-$i/disktest/1.txt -ioengine=sync```

3.3、单盘4m顺序写吞吐量

```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=write -bs=4m -size=30G -numjobs=1 -runtime=300 -group_reporting  -name=test -filename=/var/lib/ceph/osd/ceph-$i/disktest/1.txt -ioengine=sync```

3.4、单盘4m顺序读吞吐量

```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=read -bs=4m -size=30G -numjobs=1 -runtime=300 -group_reporting  -name=test -filename=/var/lib/ceph/osd/ceph-$i/disktest/1.txt -ioengine=sync```

4.单机ceph性能指标测试

单机ceph性能指标是通过fio的rbd engine测得的，要限制所有的IO全部压在一台机器上，需要创建新的crush rule(注意，单机测试必须要做，某台服务器可能会存在性能显著差于其他服务器的情况，这种情况应该发现的越早越好，另外，为了节省时间，所有的服务器可以同时进行压测，以下都是以一台服务器为例)：

```ceph osd crush rule create-simple only10 compute-96-10 osd firstn```

这条命令行能够创建一个crush rule，以这条rule创建的pool，都只会跑在compute-96-10这一个节点上。

以这条rule创建一个pool(128个pg就够了，不需要太多，因为后面的测试我们都会创建很多pool，到时候pg总量就会特别多)：

```ceph osd pool create only102 128 128 only10```

在only102这个pool上创建一个100G的名为hehe2的rbd image：

```rbd create -p only102 --size $((100*1024)) --image-format 2 hehe2```

后续的随机、顺序读写都是基于这个image进行的。

注意，使用fio进行rbd测试时，有可能会出现fio长时间全部iops都是0的情况，这时候一般都是因为这个client被blacklist了，可以通过一下命令行查看：

```
ceph osd blacklist ls
```

对于这种情况，关闭这个fio实例并重新启动一个即可。

4.1、4k随机写iops
```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=randwrite -ioengine=rbd -bs=4k -size=100G -numjobs=1 -runtime=180 -pool=only102 -rbdname=hehe2 -clientname=admin -group_reporting -name=mytest```

注意，这个脚本跑的时间为3分钟，是为了模拟虚机较长时间的高IO情况，从而得出ceph是否能够得到长时间稳定的性能，在脚本运行时，注意观察服务器load average、内存、各磁盘使用率等情况，当然最重要的是收集99%这个关口的服务质量。

注意，fio并不会耗费太多资源，因此运行在待测服务器上即可。

注意，在测试随机写时，一开始数据会不太稳定(即有一个warm up的过程)，但是经过一分钟左右就会稳定到一个较高的水平，如果iops较低，可以关掉这个fio实例再重启即可。

注意，iodepth和fio实例个数需要进行机动的调整，最好从1，2，4，8，16，32往上加，如果在iodepth=16时未超过12ms的延迟，而在32超过了，那么可以把iodepth设置成20再测试一次。


4.2、4k随机读iops
```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=randread -ioengine=rbd -bs=4k -size=100G -numjobs=1 -runtime=180 -pool=only102 -rbdname=hehe2 -clientname=admin -group_reporting -name=mytest```

4.3、4m顺序写吞吐
```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=write -ioengine=rbd -bs=4k -size=100G -numjobs=1 -runtime=180 -pool=only102 -rbdname=hehe2 -clientname=admin -group_reporting -name=mytest```

4.4、4m顺序读吞吐
```fio -sync=1 -direct=1 -iodepth=64 -thread -rw=write -ioengine=rbd -bs=4k -size=100G -numjobs=1 -runtime=180 -pool=only102 -rbdname=hehe2 -clientname=admin -group_reporting -name=mytest```

4m的顺序读写可以采用rados bench的方式测试，但是要根据延迟情况调整rados bench实例的个数，命令行为：

```rados bench 300 write -p radosbench --no-cleanup```


5、针对rack的性能测试

并发的对每个host进行压测时，能够得到一个巨大的随机写iops(香港的机器测得大约是600k左右)，然而这个值没有实际意义，主要原因在于，因为把IO落到同一个host的多个osd上，相对于完全屏蔽了网络IO对性能的影响，作为一个分布式的存储系统，通过把数据分割、打散到多台服务器上，才达到更高的可用性和可靠性，而打散意味着服务器之间交互需要通过网络，因此在进行benchamrk时，有必要做一下针对rack的压测。

注意，针对rack的压测可以同时进行，因为IO是以rack为单位进行隔离的，IO不会在rack之间流动，相互之间不会有影响。

注意，针对rack的压测必须要进行，不能漏掉，这对于得到一个合理的性能数值十分重要。

rack级别的压测跟前述针对单机的压测类似，首先需要创建基于一个rack的crush rule，以host为单位进行隔离:

```ceph osd crush rule create-simple onlyq1 Q01 host firstn```

之后就是根据此crush rule创建一个pool，pg数为512：

```ceph osd pool create onlyq1 512 512  onlyq1```

之后，创建10个rbd image，并在10个存储节点上跑10个fio实例，对这10个rbd image进行顺序、随机读写的测试(```fabfile.py```中定义了这些函数，修改一下即可)。

测试时，请密切关注延迟和磁盘利用率数据，如果延迟超过了前面所述的关口，那么就不应该再继续增加fio实例。

针对香港集群的4台机器的一个rack会是一个很好的开始，通过测试测得一个rack能够压到22370 iops(iodepth=12,10个client，latency指标为avg=12ms)。这个baseline后面还需要用到，从这里我们知道了一个host的平均iops约为5000，如果是40台机器，并且能够完美的线性扩展，那么计算出来的值将是200k。事实上，在5个rack机器数为8,9,8,9,4(踢掉了两台性能有问题的机器)，得到的随机写iops数据为：50761,46202,36498,39487,22370，总数为195318，从rack级别看，ceph基本上能够按照线性扩展，但rack之间性能存在较大差异，也是客观事实。

需要十分注意的是，单个host的性能不行会拖累整个rack，而单个rack的性能问题会拖累整个集群，在测试过程中就发现compute-96-33这台机器的性能数据拖累了rack Q03，把它踢掉之后，性能反而有提升。

6.针对集群的性能测试

基本与针对rack的性能压测方式一致，不赘述。
还是采用香港的那40台机器中的38台，测得随机写113488，虽然还可以继续增加，但是延迟会超过12ms。
注意，要根据实际情况去调整两个最重要的参数：一是fio实例个数，二是每个fio实例的iodepth，在99% IO延迟为12ms内进行调整，目标就是把总iops测到最高。

7.关于测试脚本和香港集群的测试数据

请参考```./cephop```目录提供的fabfile.py脚本和两个数据分析脚本，另外，```./cephop/rackresult```和```./cephop./clusterresult```提供了香港集群的随机写测试数据.

8.关于破坏性测试和服务器压测

除了性能测试之外，还需要测试服务器重启、服务器crash、机架掉电等情况，具体的指标是所有pg恢复为active状态所消耗的时间。

