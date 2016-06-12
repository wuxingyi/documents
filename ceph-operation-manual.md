# ceph运维手册
ceph是一个复杂的分布式存储系统，运维操作也比较繁杂，为了简化运维操作，本手册首先总结了最常见最实用的ceph命令行，用以方便的对集群进行管理和故障排除。另外，在部署上线、配置项管理、版本升级、系统扩容、磁盘故障、网络故障处理等各个环节都有可能出现一些问题，本手册收集了来自社区相关文档的说明，邮件列表对于这些问题的讨论，以及我们线上出现的问题的总结。

## 常用命令行总结


1.```ceph tell osd.* injectargs “--config value”```
该命令行可对批量osd进行配置项的更新操作，其中，```* ```表示所有的osd，也可使用某一个osd的编号来更新这个osd的配置,```--config```表示某一个配置项，```value```表示配置项的值，例如更新所有osd的```osd_max_backfills```配置项为1的命令行如下：

```
ceph tell osd.* injectargs "--osd_max_backfills 1"
```
2.```ceph osd set nodown/noout/nobackfill/norecover/noscrub/nodeep-scrub```
这几个命令行的目的是分别是：禁止标志osd为down状态，禁止down的osd被monitor标志位out，禁止进行backfill，禁止进行recover，禁止进行noscrub，禁止进行deep scrub。相应的可以使用：```ceph osd unset nodown/noout/nobackfill/norecover/noscrub/nodeep-scrub```来取消这几项配置。
建议系统设置noout，避免无谓的数据迁移；
nobackfill和norecover标志禁止进行数据的rebalance，在用户流量较大的情况下可以暂时关闭，在用户请求量下降的情况下在unset；
从线上运行的情况下，线上并没有出现过inconsistent的pg的情况，并且deep scrub会消耗较多的资源，可酌情开启或关闭deep scrub。

3.```ceph osd df```
该命令行可查看每个osd的磁盘使用情况，并查看磁盘的平均使用率以及使用率最高的osd的磁盘用量，是衡量是否需要进行扩容的重要指标。

4.```ceph daemon osd.0 config show/get/set/diff```
这几个命令行可以显示/获取/更行某个osd的配置项。
注意：这几个命令行只能运行于osd所在的服务器上，不能远程运行。

5.```ceph osd pool stats```
这条命令行可以查看每一个pool的IO情况，包括client IO和recovery IO，因此比```ceph -s```命令行得出的数据要高明许多，另外也可以指定poolname来查看某个pool的IO情况。

6.```ceph osd find```
查看某一个osd所运行的host以及这个osd所处的crushmap的位置。

7.```ceph --show-config```
查询某一个ceph配置项的默认值

8.```ceph pg map```
查看一个pg映射的osd集合。

9.```ceph pg query```
查看某个pg的状态，这些状态包括了pg_info_t和pg_stat_t内容，也包含了recovery state machine的运行状态，另外，对于正在peering的pg，可以通过peering_blocked_by来查看具体peering是被哪个osd所阻塞的。

10.```ceph osd out osd.0```
表示将osd.0 out掉，原本存储于osd.0的数据都会重新找一个副本进行存储，并且如果用户不显示的使用```ceph osd in osd.0```将osd加入进来，那么即使osd处于up状态也不会有任何数据写入进来。

11.```ceph osd perf```
查看系统中所有osd的日志commit延时和文件系统的apply延时，是检测磁盘是否正常运行的重要指标，commit延时一般在10毫秒一下，而apply延时一般在100毫秒一下，否则改磁盘就处于不佳的状态了。

12.```ceph osd map objectname```
这个命令与```ceph pg map```都可以查询一个对象映射的osd集合，但是还有一个更精巧的运用场景，即它可以用户查询一个对象在filestore上的存储位置，比如:

```
[root@ceph54 osd0]# ceph osd map rbd benchmark_data_ceph54_361925_object482
osdmap e120 pool 'rbd' (8) object 'benchmark_data_ceph54_361925_object482' -> pg 8.4f7490ff (8.0) -> up ([1,0,2], p1) acting ([1,0,2], p1)
[root@ceph54 osd0]# find . -name "*object482_*"
./current/8.0_head/DIR_F/DIR_F/benchmark\udata\uceph54\u361925\uobject482__head_4F7490FF__8
```
在这个命令行中，```4f7490ff```为```benchmark_data_ceph54_361925_object482```这个对象的哈希值，而在filestore中，是按照哈希值的逆排序来存储文件的，所以它存储的位置为DIR_F/DIR_F,当然随着这个DIR_F里的文件越来越多，就会进一步split出新的目录来，那时候，这个文件就会存储在DIR_F/DIR_F/DIR_0这个目录中了。

13.```ceph daemon osd.0 dump_reservations```
查看osd的backfill和recovery的槽位情况，即有哪几个osd处于等待槽位，这对于了解正在做backfill的pg进而估算backfill需要耗费的时间比较有帮助。



## 1、部署上线
这类问题是在部署时出现的，此时系统尚未正式写入数据，但这类问题必须得到快速处理，如果存在这些问题，则必须先解决才能接入正式的生产环境。

1.osd的crush weight与其实际容量不符：
这个问题在上线的时候出现过，现象就是一块12TB的磁盘，通过
```ceph osd tree```命令行看到的crush weight为1。这个问题可以通过手动修改crushmap来快速解决问题：
	
```
ceph osd getcrushmap -o map #将crushmap保存到本地map文件中
crushtool -d map -o txt     #将map文件转化为txt文本格式
vim txt                     #修改正确的crush weight
crushtool -c txt -o map     #将txt文本格式的crushmap编译成二进制文件并保存到map文件中
ceph osd setcrushmap -i map #设置crushmap
```

2.osd重启时打印Resource temporarily unavailable:
打印的日志形如：

> lock_fsid failed to lock /root/cephcode/src/dev/osd0/fsid, is another ceph-osd still running? (11) Resource temporarily unavailable

这说明在stop的时候osd并没有死，此时需要手工杀死此osd，如果`kill`也杀不掉就`kill -9`杀之。

3.osd
现将ceph问题区分为两种类型，关注级别的问题可通过较简单的操作进行处理，而致命问题需要可能需要通过详细研究日志、搜索社区类似问题、查看代码等方式解决。
需要注意的是，这些问题都需要通过完善的监控和报警机制才发现和处理，对于osd down、monitor down等

