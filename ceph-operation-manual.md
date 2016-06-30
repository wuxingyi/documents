# ceph运维手册
ceph是一个复杂的分布式存储系统，运维操作也比较繁杂，为了简化运维操作，本手册首先总结了最常见最实用的ceph命令行，用以方便的对集群进行管理和故障排除。另外，在部署上线、配置项管理、版本升级、系统扩容、磁盘故障、网络故障处理等各个环节都有可能出现一些问题，本手册收集了来自社区相关文档的说明，邮件列表对于这些问题的讨论，以及我们线上出现的问题的总结。

## 一、ceph中的基本概念
1.```monitor```
```monitor```主要有三项职责：一是负责集群member ship管理即颁发osd map和pg map，维护集群状态，二是作为cephx(类kerboros的鉴权协议)的KDC，鉴定各个组件的keyring，三是作为查询入口，接收用户对集群的状态查询。
monitor集群一般至少需要三个成员，在更大的集群中可能需要更多的monitor，请设置monitor个数为奇数个。
monitor会进行形式上的选举，但总是rank最低的monitor获胜，而在所有的monitor都使用默认的6789端口的情况下，rank最低的总是IP地址最小的monitor。
monitor使用keyvalueDB来存储其数据。

2.```osd```
```osd```是运行于存储服务器一个守护进程，通常一个```osd```管理一块磁盘。每个osd可以承载多个pg，承载同一个pg的多个osd互称为```peer```，这也是osd启动或者pg创建之时，经历的```peering```状态的由来，peering过程就是通过将多个peer存储的pg_info_t信息合成出一份权威的pg_info_t。
peer之间需要通过心跳来探测对方是否存活，如果发现某个peer在一定时间内多次探测均无回应，则向monitor举报该peer为down状态，此时monitor并不会立刻将该osd设置为down状态，而是需要收集足够多的这种举报信息之后才设置该osd为down状态。
对于一个osd而言，其职责的就是管理其```资产```，即由CRUSH映射而承载的各个pg。

3.```pg```
pg是一组对象的集合，是集群的最重要```资产```。通过这一逻辑概念，简化了数据的replication和rebalance，同时也使得每个osd不需要对每个对象都维持一个peer列表，简化了心跳流程。
```osd```和```pg```的关系是：每个osd可以承载多个pg，每个pg都会通过CRUSH算法的映射到多个osd上(在多副本的情况)。
pg内的replication和pg的rebalance是最复杂的部分，replication指将数据复制到多个peer，rebalance则是指pg的迁移。如果pg从一个osd迁移走了，那么这个osd会自动的将这个pg的数据删除，这个自动的过程称为```clean```。
每个pg都运行在一个recovery state machine(数据恢复状态机)，这个状态机维护了二十种pg状态以及各个状态下的时间响应，最理想情况下，pg应该处于```active+clean```，当进行数据迁移时，可能会处于多种中间状态，但只要pg是处于```active```状态，那么数据读写操作都不会有问题，```degraded```状态说明有数据的副本数没有达到```pool size```，而```incomplete```通常指pg中的某些对象没有达到```pool min_size```。

4.```acting set```与```up set```
```acting set```是```当前```维护pg的一组osd，而```up set```指的是```将来```维护pg的一组osd，可以通过```ceph pg query```获取命令行查看，在进行数据rebalance时也可以通过```ceph health detail```查看。通常而言两者是一样的，而如果集群磁盘扩容或者pg扩容导致数据pg迁移时，```将来```的osd并不具有全量的数据，因此不能处理读请求，而```当前```的osd组合具有全量的数据，因此只有```当前```的osd组合能够进行读请求，对于写入请求，也是写到```当前```osd组合中，后续再迁入到```将来```osd组合，因此下线机器的时候必须主要保持足够数据的```acting set```的个数，否则新写入的数据将会处于```degraded```(降级)状态。
当两个osd组合不一致时，pg都会处于```remapped```状态，而且```acting set```通常称为```pg_temp```，即这个组合类似于```看守内阁```，等数据迁完之后，```acting set```将转变成```up set```。
当```acting set```与```up set```不一致时，pg内尚未被迁移到```up set```的对象都处于**```misplaced```**状态。
**```注意```**: 在进行backfill的时候，如果有新的数据写入，那么这部分数据只会写到当前的acting set中，如果acting size < pool size，那么这部分数据从出生开始就是出于降级状态的。

5.```osd map```
```osd map```反映了集群中各个osd的状态，状态包括了两个维度：UP/DOWN和IN/OUT，UP/DOWN状态表征的是osd是否存活(更深层次决定于是否网络可达)，IN/OUT表征的是是否承载pg。在没有通过```ceph osd set noout```的情况下，处于DOWN状态的osd会自动转为OUT状态。在OUT状态下，CRUSH会认为这个osd无法恢复而重新选择其他副本。
是由monitor颁布的，但monitor并不是独裁者，monitor是充分收集osd上报的消息之后才会做出决策发布新的```osd map```，这些消息包括osd启动时的```BOOT```消息、osd进程挂掉时发送的```DOWN```消息以及osd根据心跳结果上报的peer不可达消息等。

6.```CRUSH map```与```CRUSH rule```
```CRUSH map```维护的是整个存储集群的硬件拓扑结构(维度包括DC,ROOM,PDU,RACK,HOST,OSD等)，这个结构是一个森林，可以包含多颗树，比如树根表示不同类型的存储介质。根据每一块磁盘的容量，再逐级上溯到树根，可以得出一棵树的各级存储的```CRUSH weight```，在前面的```osd map```中，可以通过设置osd的状态为```OUT```来设置```osd weight```为0，但是这个osd还在```CRUSH map```中，因此整个HOST的```CRUSH weight```不变，因此设置一个osd为```OUT```时，通常会造成同HOST上的其他osd承担更多pg。
```CRSUH rule```是选取osd的规则，区别包括是使用多副本还是EC、从哪颗树选取osd等。

7.```file```、```attribute```和```omap```
对于一个分布式存储系统，最终还是要写到本地的，```file```、```attribute```和```omap```三者组合起来构成了本地存储，```file```表示存储本地文件系统的文件，```attribute```表示附加在本地文件系统文件上的扩展属性，```omap```则是存储于key-value DB上的键值对，一般而言大部分数据都是写入到```file```中，而一些key-value则可存储于```attribute```或```omap```中，因为文件系统的扩展属性有存储量的限制，并且高度依赖于底层文件系统的实现，因此现在更倾向于一些元数据于omap之中，比如rbd的应用场景下，就使用omap存储了size，object_prefix等很多元数据。

8.```pg log```
ceph使用```pg log```来保证多副本之间的一致性。```pg log```用来记录做了什么操作，比如修改，删除等，而每一条记录里包含了对象信息，还有版本。ceph使用版本控制的方式来标记一个PG内的每一次更新，每个版本包括一个(epoch，version)来组成：其中epoch是osdmap的版本，每当有OSD状态变化如增加删除等时，epoch就递增；version是PG内每次更新操作的版本号，由PG内的Primary OSD进行分配的。
在```peering```过程中，Primary OSD会向其他osd请求```pg log```并用于合并出一份权威的```pg log```。
```pg log```以前是(2013年前)使用文件系统attribue来存储的，现在的版本已经是使用omap来存储。

8.```unfound```对象
```unfound```对象是在```log-based recovery```的源osd失效时出现的，此时待recover的节点已经知道了缺失哪些```pg log```，并由此知道缺失哪些对象，这些对象此时是处于待recover节点的```missing```列表中的，在recover尚未完成而源osd已经失效的情况下，待recover节点便将此时的```missing```列表中的全部对象置为```unfound```。
有```unfound对象```的情况下，pg实际是处于```active+recovering+degraded```状态的，尽管recover没有完成，但是只要不命中```unfound```对象，其他对象都是可读的，并且此时pg是可写的，但是如果读写```unfound对象```，都会造成```slow request```，并长时间block住，这也是一种相当严重的状况，但是比整个pg处于incomplete、down或卡在peering状态导致完全不可读写要稍微好一些。

## 二、运维必备命令行
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
14.```ceph pg repair <pgid>```与```ceph osd repair <osdid>```
修复inconsistent的pg，前者是对一个pg触发repair操作，后者则是对一个osd承载的所有pg做repair。
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
25.```ceph osd reweight 0 0.9```
将osd.0的weight降低为0.9，这种情况下，因为osd.0的crush weight并没有改变，所以osd.0上的很多数据都大概率会迁移到osd.0所在host的其他osd上，因此使用这条命令时，应该注意观察本host上的其他osd的磁盘使用率，如果是只有一个osd到了near full报警，而且有其他osd已经到了80%左右，那么这种reweight就是毫无意思的，因为大概率会出现拆东墙补西墙的情况，另外一个osd会冒出来报near full。

## 三、有关ceph的日志
ceph的日志包括osd的日志和monitor的日志，位于```/var/log/ceph```目录下，osd的日志文件名称是ceph-osd.0.log，monitor日志名称是ceph-mon.a.log，默认情况下7天做一次log rotate。
可以通过调高日志级别来数据更详细的日志，但是要注意monitor和osd在最高日志级别下日志写入非常快，别把分区刷满了。
另外，ceph的日志是分模块进行的，合理使用debug_osd和debug_filestore能够知道osd daemon做的所有事情，只需使用下面的命令行即可：

```
	ceph daemon osd.0 config set debug_osd 20/20
	ceph daemon osd.0 config set debug_filestore 20/20
```

类似的，对于monitor，设置debug_mon日志等级为20/20即可。
需要注意的是，对于rados和rbd命令行，其实也是可以设置debug参数的，比如使用使用如下命令行可以查看到完整的client和monitor、osd交互的过程：

```
	rados ls -p rbd --debug_objecter 20/20 --debug_rados 20/20 --debug_client 20/20
```

除了以上直接有ceph提供的日志之外，```/var/log/messages```会提供关于ntpd和磁盘驱动方面的日志信息，ceph monitor的运行依赖于准确的时钟，如果monitor运行不正常导致osd member ship大幅抖动，可以从日志中找找看有没有有关ntpd的信息。另外，磁盘坏道会导致osd coredump，此时也可以从日志文件中找到信息。
另外，在centos 7环境下，osd启动失败的日志有可能会写到```/var/log/messages```。

## 四、ceph常见问题分级及处理方式
### 一、简单级别
这类问题处理时比较简单，并且不会影响数据安全，包括：
1.osd的crush weight与其实际容量不符：
这个问题是在部署时出现的，此时系统尚未正式写入数据，但这类问题必须得到快速处理，如果存在这些问题，则必须先解决才能接入正式的生产环境。
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

3.ceph -s报“too few pgs per osd”
ceph报这一问题的条件是每个osd上的pg个数小于20个，而根据我们目前的最佳实践，为每个osd数据的相对均匀，我们都会要求每个osd承载200个pg左右，因此这个问题在线上出现的概率几乎为0。如果出现是因为扩容了十倍以上的osd导致每个osd上的pg个数小于20，那么就必须采用```一、运维必备命令行```中提到的扩容pg_num和pgp_num进行操作了。

4.内存不足导致osd进程因pthread_create失败而退出
这个问题在线上出现过，某个osd因为pthread_create失败而打断言并退出，后来看了是因为系统内存不足，重启osd之后，问题就解决了。

5.EC环境下，进行recovery时看不到recover IO
这个问题已经在giant上修复，考虑到rbd并不会使用到EC，所以这个问题不会再出现。

6.degraded或者misplaced的objects为负数
这个问题是ceph统计上的bug，比如出现```-2630/2182927064 objects degraded```，2182927064是这个pool中所有的对象个数*副本数，-2603这个负数可以理解为有些副本本应被clean掉，即它们是多出来的，所以成了负数，总之，这个问题都可以放任不管，待backfill完成之后，就没有负数了。

7.pg状态为active后加degraded、remapped、remapped、backfilling、wait_backfill、recovering、wait_recover、undersized等状态
这是做recover/backfill过程中的中间状态，只有pg是active的就没有问题，无需干预。

8.monitor所在磁盘空间不足
默认情况下，monitor都会把数据写到/var/lib/ceph/mon目录下，如果日志、coredump等存储没有跟monitor目录分开，则可能会出现monitor空间不足的情况，一般报错都形如“mon.bj-yz2-ceph-12-102 low disk space -- 29% avail”，此时就需要删除相关coredump文件和日志文件。
如果是因为monitor写的文件过大，则需要在```ceph.conf```中添加一下配置并重启monitor：

```
[mon]
mon compact on start = true
```
如果monitor使用的空间较大，那么做compaction会消耗较长时间。
如果monitor的sst文件存储过多，会造成monitor越来越慢，而线上数据显示一次compact能够把原来20G的monitor磁盘占用缩减至不到1G，所以说监控minitor占用的空间并在超过一定空间之后通过重启monitor进行compact，是非常有用的。

二、关注级别

这类问题需要运维人员根据实际情况作出一些处理，但危险性基本可控。
1.磁盘坏道或其他磁盘故障导致osd无法启动
首先明确在```/var/log/messages```中能够看到磁盘硬件故障的信息，如果已明确，通知IDC更换磁盘，如果IDC短期内没有办法更换磁盘，那么就应该把这个osd out掉，避免有数据处于降级状态。IDC更换磁盘成功之后，执行以下操作(以下以osd.12为例讨论)：

```
ceph osd rm osd.12 #这一步操作不能少
ceph osd create    #必须保证这一步返回的是12，如果是小于12的数字，那就多create几次知道12为止
cd /var/lib/ceph/osd/ceph-12
ceph-osd -i 12 --mkfs
touch /var/lib/ceph/osd/ceph-12/sysvinit
ceph auth export osd.12 > /var/lib/ceph/osd/ceph-12/keyring
/etc/init.d/ceph start osd.12
```

对于被手动out掉的osd，应该手动把它设置为in状态:

```
ceph osd in osd.12
```

2.monitor出现clock skew
这个问题可大可小，必须要区分对待，因此把这个问题放到了关注级别。因为默认是0.05秒skew就报警，如果是通过```ceph health detail```得到的clock skew时间是一个稍大的数字比如0.1或者0.5之类的，那么重启不从重启ntpd都可以。但线上出现过长达220天的clock skew，这种情况下如果重启ntpd，一般都会带来非常严重的cephx认证失败，造成大量的osd down，大量的pg出现peering状态，从而造成整个集群的服务不可用。出现这一问题，应该首先设置osd为nodown：

```
ceph osd set nodown
```
目的是为了防止大量osd down掉，然后再重启ntpd，重启完了也需要继续关注osd和集群的状态。

3.出现inconsistent的pg
根据线上rgw运行情况，几乎没有出现inconsistent pg的情况，但是rbd出现过多次因为磁盘坏道导致读不到primary osd上的副本而出现的inconsistent pg的情况，这个首先参考```磁盘坏道或其他磁盘故障导致osd无法启动```把osd创建并加进来，待数据迁移完了之后运行：

```
ceph pg repair pgid   #pgid为出现inconsistent的pgid
```

事实上，因为所有的副本都已经被拷贝了，并且不存在读不到某一个副本的情况，所以待repair完，pg将会是摆脱inconsistent状态。

4.osd占用过多内存或CPU资源
这个也要分情况进行处理，此处重点区分两种情况：一是做backfill时，另一种是常规时间。
在做backfill的时候，osd会需要占用一些内存来存储迁入或者迁出的数据，但是内存占用一般不会超过2GB，如果超过2GB很多，那说明数据迁移太猛了，应该降低一下迁移的速度(前文提到过怎样增减osd的迁移速度)，CPU方面主要是看15分钟的load average，rgw的数据迁移一般控制在load average在6左右，具体要跟存储服务器的核数来定。
在常规时间，内存一般在1GB左右，5分钟load average一般都在0附近，如果超出很多，则需要关注是否跟别的问题相关，因为在大部分情况下，耗费CPU和内存是现象，而问题的根源则需要再进一步深究。
rgw场景下曾经出现过一次因为某一个对象的omap过大，而ceph在删除对象时，会在一个事务中把整个omap全部load到内存中，导致耗光了系统的内存而core dump，为此我们还打了个patch让删除这个对象时不删omap。
总之，占用过多CPU和内存时，首先需要判断的是是否是处于backfill状态，如果是就降迁移速度，否则，就需要综合各种因素来判读。

5.出现near full的osd
默认情况下，osd的磁盘使用率超过了85%之后，即会报出near full的warning。首先应该极力避免将集群的使用率达到如此高的程度，这就需要对集群的超售比做出限制，并规划好进行扩容的比例，rgw集群一般在60%左右就会进行扩容。
如果出现了near full的osd，首先看是否是这个osd一枝独秀，即达到85%的osd是否只有这一个或一两个，并且其他所有的osd的使用率都远低于85%，如果是这样，可以一下命令行降低一下osd的weight:

```
ceph osd reweight 0 0.9
```
如果有多个osd都是near full状态，那就找尽快扩容吧。

6.某些pg出现backfill_toofull状态
backfill_toofull出现时，数据将不能正常backfill到已经过满的osd上，在处理上，这个问题跟前面的```出现near full的osd```一样，不能reweight就扩容吧。

7.osd因为心跳不达而suicide
目前线上集群已经配置了一个非常宽容的心跳检测条件：

```
osd_heartbeat_grace = 500
osd_heartbeat_interval = 180
mon osd min down reporters = 3
mon osd min down reports = 4
```
这导致出现心跳问题的概率降到非常低了，如果出现了这种情况，首先还是检查是否用户IO负载过重或者数据迁移速度是否过快，一般而言重启就能解决问题。

8.数据不均匀，max/avg超过1.4
通过配置每个osd承载200个pg，一般而言max/avg都在1.2到1.3左右，即最满的osd与平均值的比例在1.2到1.3之间，如果超过1.4了，那就代表数据严重不均匀了，这个时候需要考虑是不是因为集群扩容导致每个osd承载的osd的个数减少了，如果是的话，就需要增加pg个数了。
在rbd场景下，数据不均匀性可能会比存储大文件的rgw集群严重，因为对于rbd而言，可能仅仅写文件的开头一些字节，从而存储了很多小的文件，这个需要到线上验证。

9.某些osd的commit时间百毫秒以上
commit时间可以通过```ceph osd perf```获得，如果这个值特别大，超过百毫秒以上，说明如果是单块磁盘这样，说明这块磁盘性能严重降低了，如果大部分磁盘都这样，则需要联系开发人员进行性能分析来判断了。

10.某些osd出现了slow request
这个时候需要查日志，看看slow request的延迟时间，前面提到的clock skew也会造成slow request，如果没有clock skew，那么就看出现slow request的osd的个数，如果是仅仅一两个osd出现，那么可以不处理，或者是重启这个slow request的osd。

11.简单版的incomplete的pg
这种情况的简单之处在于，尽管当前的acting set已经小于min_size了，但是acting set中至少有一个osd，这种incomplete的特征就是```ceph health detail```可以看到：

```
pg 10.0 is incomplete, acting [0](reducing pool rbd min_size from 2 may help; search ceph.com/docs for 'incomplete')
```
如果其他osd在想尽办法之后仍然无法恢复，可以改变min_size的方式将pg恢复过来：

```
ceph osd pool set rbd min_size 1
```
之后，就是通过把起不来的osd out掉，此时crush算法会重新选择另外两个osd存储这个pg，这样数据会重新进入到backfill状态并最终恢复。

三、严重级别
严重级别操作具有危险性，特别是涉及到操作pg的元数据，因此需要谨慎。
1.恶劣版的incomplete pg
这种情况下，集群已经处于错误状态，此时肯定是有osd处于down状态，如果能把down的osd全部拉起来，那么就不存在什么问题了，down的pg在重新peering之后应该能恢复。
如果发现多个osd不能启动，首先应该做的是确认osd不能启动的原因，原因可能有磁盘硬件故障和ceph本身的bug。如果是ceph本身的bug，则需参考```四、疑难杂症```中的```1.挂掉的osd重启之后仍然打断言```收集信息做进一步分析。
如果是硬件故障导致数据已经无法恢复，则通过```ceph pg 10.0 query```查看出past_intervals内的所有osd，并尝试查看这些osd上是否有这个pg 10.0的数据，如果有，那么可以看看这个目录中文件的个数，那么可以把这些数据当做是这个pg的最终版本的数据，即把这个osd当做authority，这可能会造成丢失一部分数据，类似于git的revert到历史上的一个版本，通过下面命令行即可：

```
ceph_objectstore_tool --op mark-complete --pgid 7.0 --data osd1 --journal osd1.journal
```
如果都没有，那就可以宣布这个pg上的数据已经丢失，incomplete的pg不可读写，为了让这个pg可写，可以通过下面的命令行将这个pg设置为complete：

```
ceph_objectstore_tool --op mark-complete --pgid 7.0 --data osd1 --journal osd1.journal
```
这条命令行结果仅仅是pg可写，原有的数据全部丢失了。

2.出现full的osd
在有osd的磁盘使用率超过95%的情况下，monitor会报full，并且系统变成不可读写，处于ERROR状态。
前面提到了，在osd进行near full状态之前就需要进行扩容，在出现了full的osd之后，能做的就是把full的osd关掉并out掉，然后删除这个osd上的部分pg，在使用率低于95%之后即可把osd拉起来并设置为in状态，并参考near full状态下的处理进行操作。

3.多台存储服务器同时宕机
通知IDC启动服务器，尝试启动osd并进行处理

4.网络抖动等导致的心跳异常，并因此引起的membership剧烈变动
此时需要进行一下设置：

```
ceph osd set nodown
ceph osd set noup
ceph osd set noout
```
5.时钟严重不同步导致的cephx验证失败
前面已有提到，此时需要在重启ntpd前做以下配置：

```
ceph osd set nodown
```
6.EC场景下osd成组的core dump
这个问题在rgw使用EC的环境下出现过，原因在于同时处理同名文件的删除和上传时，文件删除操作导致偏移变成0，而文件上传操作仍然以之前的偏移进行文件写入，EC认为这个不为0所以core dump了。EC采用使用第一个osd进行对象的切分和分发，在第一个osd core dump之后，写入会重新进行retry并把下一个osd也搞core dump，最终导致这个pg为incomplete，如果这些core dump的osd全部被out掉了，那么再retry又可以把新补位的osd也搞core dump，最终的结果就是所有的osd只剩下```min_size-1```个。
所幸，这个bug已经修了。

7.来自librbd的bug
因为librbd是被qemu-kvm进程加载的lib，如果发现librbd的重要bug，修复的时候可能需要重启虚拟机(通过虚拟机迁移方式应该也可行，但没有验证过).

四、疑难杂症
1.挂掉的osd重启之后仍然打断言
出现了前面都没提到的原因，导致osd重启后打断言并启动失败，那么需要提高osd的日志等级，收集日志，并联系开发人员处理.
提高日志等级的方式是在```/etc/init.d/ceph.conf```的```[osd.0]```段下配置日志等级，形如：

```
[osd.0]
debug_osd = 20/20
debug_filestore = 20/20
```
注意要在问题解决之后把上述配置删除，因为过高的日志等级既降低性能，也可能会把var分区占满。

## 五、ceph的监控与报警 
ceph并不是一个很好运维的存储系统，因此需要一些监控和报警来帮助运维人员进行运维工作。
1.monitor、osd状态短信电话告警
需要部署watchceph并发信给ops-noc来实现monitor、osd状态变化时的告警。watchceph会关注检测是否有osd down，monitor down以及near full的osd，当出现这些情况时，会触发短信告警，以便及时处理。
2.常规监控
需要关注的监控项包括：数据使用量、osd数据均匀性、client/recovery io大小(包括iops和带宽两个维度)、是否有非active的pg、misplaced的对象个数、misplaced的对象比例、各个存储节点的load average、各个存储节点的网卡流量、各个磁盘的disk utitity等


## 六、ceph运维中的危险操作总结
1、跨大版本升级
尽管社区会对各个大版本升级做测试并给出升级步骤，但是仅限于社区发布的大版本之间的升级，我们经常会从upstream backport很多patch回来，导致出现问题

