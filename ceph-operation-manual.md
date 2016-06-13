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
通过```ceph daemon osd.0 config set debug_osd 20/20```可以设置osd.0的日志级别为20/20，查看osd的最完整日志。

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

14.```ceph pg repair <pgid>```
修复inconsistent的pg

15.```osd pool set <poolname> size/min_size/pg_num/pgp_num```
设置pool的size和pg个数参数，减少min_size为1在三个副本中的某一个数据还在的情况下，可以解决incomplete pg的问题，但是在数据不全的情况下，incomplete pg的问题只能依靠```ceph_objectstore_tool```尝试解决(事实上也不一定能百分之百解决)。
扩充pg能够让每个osd里的数据更加均匀，但是扩充pg_num和扩充pgp_num表现上是不一样的，扩充pg_num时，尽管每个osd上的pg个数都会增加，但是新增加的pg并不会在osd上重新分布，比如之前是1个pg，负责的osd为(0,1,2)，此时如果扩充pg_num为2，此时两个pg都仍然是映射到(0,1,2)而不会在整个crushmap上重新映射，另外，表现上扩充pg_num就是在current目录下新建一个目录，并且把原pg的一半内容挪到新pg上，可想而知，扩pg需要filestore层的很多hard link操作，因此会耗费一定时间，因此，扩充pg_num不应在业务量高的时候做。扩充pgp_num之后，就会实现新pg的重新分布，比如上述1扩为2的情况，可能新pg就会映射到(2,3,4)上，并且会引起数据的backfill。
总结如下：
一、扩pg_num不会带来数据迁移，但是会引起filestore的文件操作，并且不像backfill或者recover可以暂停，这个过程是不可中断的，并且新增的pg个数越多，这些新pg也会需要做经历creating和peering阶段，对于系统CPU和内存都有消耗，因此不要在高业务量的情况下进行操作。建议：扩充pg时，必须小步走，一次不要扩太多。
二、扩pgp_num时，会引起数据的迁移，请合理使用```nobackfill```来控制迁移的节奏。

16.```rados pgls -p <poolname> -pg <pgid>```
通过这条命令可以list出一个pg内的所有对象，而不需要像```rados ls```那样把整个pool都list出来。

17.```ceph health detail```
通过这条命令可以查看出集群的运行状态，包括发生slow request的osd，出现clock skew的monitor等等，方便后续决策。

18.```ceph_objectstore_tool```
这个命令行工具是由ceph-test包提供的，是大杀器，在面临极端情况下(最坏的情况就是出现incomplete pg的情况)十分有用。
通过这个命令行，除了可以进行对象的操作之外，还可以对非常危险的pg元数据进行操作，另外也可以查看一个pg的pg log，也可以进行pg数据的import和export，还可以挽救incomplete的pg，但是务必慎重使用，因为可能会造成整个filestore或者journal损坏。
因此，线上环境下，使用这个命令时，请务必跟开发人员沟通好，明确危险性。

19.```rados stat -p <poolname> <objectname>```
通过这条命令行可以查看对象的写入时间和对象大小等参数。

20.```ceph osd getcrushmap -o map``` ```ceph osd setcrushmap -i map```
前者表示获取crushmap并保存到本地map文件中，后者表示将本地已编译的二进制map文件设置为新的crushmap。

21.```crushtool -d map -o txt``````crushtool -c txt -o map```
crushmap在osd上是使用二进制进行存取的，而我们队crushmap进行编辑操作需要使用文本格式，前者将二进制的crushmap解码为ASCII文本，后者将ASCII版本的crushmap编码为二进制。

22.```rados listomapkeys/listomapvals/getomapval```
omap是rados存储数据的一种形式，采用key/value的方式进行存储，rbd中关于image的元数据即是使用omap进行存储的。

23.```rados listxattr/getxattr```
xattr是rados存储数据的一种形式，底层使用的是文件系统的扩展属性进行存储的，rbd中基本上没有使用rados的xattr进行存储，但是在rgw大量使用到了xattr，但是底层的filestore还是大量的使用了文件系统扩展属性，对于这些扩展属性，可以通过```attr -g```进行获取。

24.```ceph auth```
```ceph auth```这一族命令行都是用于cephx认证相关的，```ceph auth list```用户查看所有entity的keyring，```ceph auth caps```用于给一个entity增加权限。```auth export```用于到处keyring到本地文件。


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

