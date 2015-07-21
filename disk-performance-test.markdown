# 磁盘性能测试

linux下磁盘性能测试工具有很多种，例如fio, iozone, 还有dd, 查询设置磁盘参数的工具hdparm, 磁盘smart功能工具smartctl等等，下面分别介绍一下。

##FIO

fio 是一个 I/O 工具用来对硬件进行压力测试和验证，支持13种不同的I/O引擎，包括：sync, mmap, libaio等等, I/O priorities (for newer Linux kernels), rate I/O, forked or threaded jobs, 等等。fio可以使用job描述文本作为输入进行测试，也可以使用命令行进行测试。

fio可以在直接测试块设备，也可以基于文件测试。直接在块设备上测试可以不受文件系统的干扰。如果在文件系统上测试，文件系统的碎片问题可能会影响到测试结果。

###FIO测试命令例子
    fio -directory=.  --sync=1  -rw=write -iodepth=1  -bs=4k -size=1G -numjobs=1 -runtime=30 -group_reporting -name=mytest -exit_all

说明

directory=.              指定测试目录

rw=write                 测试顺序写的I/O

sync=1                   测试时候同步到磁盘表面

iodepth=1                io队列的深度

bs=4k                    单次io的块文件大小为4k

size=1G                  本次的测试文件大小为1g，以每次4k的io进行测试。

numjobs=1                本次的测试线程为1.

runtime=30               测试时间为30秒

group_reporting          关于显示结果的，汇总每个进程的信息。

name=mytest              测试文件的名字

direct=1                 测试过程绕过机器自带的buffer。使测试结果更真实。 

ioengine=psync           io引擎即发起IO的方式使用方式.

lockmem=1g               只使用1g内存进行测试。 

zero_buffers             用0初始化系统buffer。 

nrfiles=8                每个进程生成文件的数量。

filename=/dev/sdb1       测试文件名称，通常选择需要测试的盘的data目录。 

详细说一下

ioengine引擎即发起IO的方式。

sync 基本的read,write.lseek用来作定位。

psync 基本的pread,pwrite。

vsync 基本的readv,writev。

libaio Linux专有的异步IO。

mmap 文件通过内存映射到用户空间，使用memcpy写入和读出数据。

还有其他的方式，posixaio，solarisaio，null， net等等。

rw参数设置

有write, read, randwrite, randread等等。

###FIO输出

    mytest: (g=0): rw=write, bs=4K-4K/4K-4K/4K-4K, ioengine=sync, iodepth=1
    fio-2.0.13
    Starting 1 process
    mytest: Laying out IO file(s) (1 file(s) / 1024MB)
    Jobs: 1 (f=1): [W] [100.0% done] [0K/151K/0K /s] [0 /37 /0  iops] [eta      00m:00s]
    mytest: (groupid=0, jobs=1): err= 0: pid=18374: Mon Jul 13 18:48:11 2015
    write: io=4932.0KB, bw=168205 B/s, iops=41 , runt= 30025msec
      clat (msec): min=16 , max=124 , avg=24.34, stdev= 5.70
       lat (msec): min=16 , max=124 , avg=24.34, stdev= 5.70
       clat percentiles (msec):
     |  1.00th=[   17],  5.00th=[   17], 10.00th=[   17], 20.00th=[   25],
     | 30.00th=[   25], 40.00th=[   25], 50.00th=[   25], 60.00th=[   25],
     | 70.00th=[   25], 80.00th=[   25], 90.00th=[   26], 95.00th=[   34],
     | 99.00th=[   35], 99.50th=[   42], 99.90th=[  117], 99.95th=[  126],
     | 99.99th=[  126]
    bw (KB/s)  : min=  124, max=  240, per=100.00%, avg=164.19, stdev=24.76
    lat (msec) : 20=16.55%, 50=83.21%, 100=0.08%, 250=0.16%
    cpu          : usr=0.04%, sys=0.47%, ctx=2478, majf=0, minf=24
    IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued    : total=r=0/w=1233/d=0, short=r=0/w=0/d=0

    Run status group 0 (all jobs):
    WRITE: io=4932KB, aggrb=164KB/s, minb=164KB/s, maxb=164KB/s, mint=30025msec, maxt=30025msec

    Disk stats (read/write):
    sdm: ios=0/2472, merge=0/0, ticks=0/29691, in_queue=29710, util=98.36%


这里我们先关注吞吐量和IOPS

    write: io=4932.0KB, bw=168205 B/s, iops=41 , runt= 30025msec

####IOPS

即每秒的输入输出量(或读写次数)，是衡量磁盘性能的主要指标之一。IOPS是指单位时间内系统能处理的I/O请求数量，一般以每秒处理的I/O请求数量为单位，I/O请求通常为读或写数据操作请求。

####IOPS计算方法

 传统磁盘本质上一种机械装置，如FC, SAS, SATA磁盘，转速通常为5400/7200/10K/15K rpm不等。影响磁盘的关键因素是磁盘服务时间，即磁盘完成一个I/O请求所花费的时间，它由寻道时间、旋转延迟和数据传输时间三部分构成。

寻道时间Tseek是指将读写磁头移动至正确的磁道上所需要的时间。寻道时间越短，I/O操作越快，目前磁盘的平均寻道时间一般在3－15ms。

旋转延迟Trotation是指盘片旋转将请求数据所在扇区移至读写磁头下方所需要的时间。旋转延迟取决于磁盘转速，通常使用磁盘旋转一周所需时间的1/2表示。比如，7200 rpm的磁盘平均旋转延迟大约为60*1000/7200/2 = 4.17ms，而转速为15000 rpm的磁盘其平均旋转延迟约为2ms。

数据传输时间Ttransfer是指完成传输所请求的数据所需要的时间，它取决于数据传输率，其值等于数据大小除以数据传输率。目前IDE/ATA能达到133MB/s，SATA II可达到300MB/s的接口数据传输率，数据传输时间通常远小于前两部分时间。因此，理论上可以计算出磁盘的最大IOPS，即IOPS = 1000 ms/ (Tseek + Troatation)，忽略数据传输时间。假设磁盘平均物理寻道时间为3ms, 磁盘转速为7200,10K,15K rpm，则磁盘IOPS理论最大值分别为，

IOPS = 1000 / (3 + 60000/7200/2) = 140
IOPS = 1000 / (3 + 60000/10000/2) = 167
IOPS = 1000 / (3 + 60000/15000/2) = 200

这里没有考虑传输时间。如果是顺序写，那么省去寻址时间和旋转延时，IOPS就会很大了。

另外测试时候需要考虑sync参数，因为如果不设置这个参数，那么写入只是写入到page cache里，如果加了direct参数，虽然绕过了pagecache，但是还有硬件cache,要想把硬件cache里的数据刷到磁盘表面需要使用sync参数。

IOPS的参考数据https://en.wikipedia.org/wiki/IOPS

其他的参数的解释后续再增加

##IOzone

IOzone是一个文件系统测试基准工具。可以测试不同的操作系统中文件系统的读写性能。可以通过 write, re-write, read, re-read, random read, random write, random mix, backwards read, record rewirte, strided read, fwrite, frewrite, fread, freread, mmap, async I/0 等不同的模式下的硬盘的性能。

测试例子

    # /root/iozone -a -n 4m -g 4m -i 0 -f ./mytest_iozone -o
    .....
    Auto Mode
	Using minimum file size of 4096 kilobytes.
	Using maximum file size of 4096 kilobytes.
	SYNC Mode. 
	Command line used: /root/iozone -a -n 4m -g 4m -i 0 -f ./mytest_iozone -o
	Output is in kBytes/sec
	Time Resolution = 0.000001 seconds.
	Processor cache size set to 1024 kBytes.
	Processor cache line size set to 32 bytes.
	File stride size set to 17 * record size.
                                                              random    random     bkwd    record    stride                                    
              kB  reclen    write  rewrite    read    reread    read     write     read   rewrite      read   fwrite frewrite    fread  freread
            4096       4      165      162                                                                                            
            4096       8      429      426                                                                                            
            4096      16      620      611                                                                                            
            4096      32     1321     1343                                                                                            
            4096      64     3091     3343                                                                                            
            4096     128     4096     4634                                                                                            
            4096     256     9417     9273                                                                                            
            4096     512    20512    21382                                                                                            
            4096    1024    16432    30771                                                                                            
            4096    2048    41203    49300                                                                                            
            4096    4096    62224    70698                                                                                            

    iozone test complete.

参数

a   全面测试
n   测试最小文件大小
g   测试最大文件大小
i   测试种类，0代表写，1代表读
f   后面指定文件名
o   指定sync操作


##dd命令

dd 命令主要是设置iflag=direct,sync oflag=direct,sync分别是direct IO, 同步读写IO的方式。例如

    [root@ceph-97 test]# dd  if=/dev/zero  of=./test_file4  bs=4M count=1024  oflag=sync
    记录了1024+0 的读入
    记录了1024+0 的写出
    4294967296字节(4.3 GB)已复制，75.707 秒，56.7 MB/秒

##hdparm

hdparm是一个工具用来显示与设定IDE或SCSI硬盘的参数。例如可以设置开关磁盘cache(有的时候可能一些原因部分硬盘不支持),可以设置硬盘某个block为坏快，可以修复某些种类的坏快，可以设置ncq等。

##smartctl

硬盘smart是硬盘里跑的一个监控工具，用来检测和报告磁盘运行时候的健康参数。smartctl工具可以从硬盘读出这些参数。具体可以参考wiki. https://en.wikipedia.org/wiki/S.M.A.R.T.




#线上机器测试结果

其中机器配置

    4 processors
    Intel(R) Xeon(R) CPU E5-2609 v2 @ 2.50GHz
    MemTotal:       32827532 kB
    
    disk:
    Vendor:               DELL
    Product:              PERC H310
    Revision:             2.12
    User Capacity:        4,000,225,165,312 bytes [4.00 TB]
    Logical block size:   512 bytes
    Logical Unit id:      0x6b083fe0c58496001bed426c09194c12
    Serial number:        00124c19096c42ed1b009684c5e03f08
    Device type:          disk
    Local Time is:        Mon Jul 13 15:07:23 2015 CST
    Device does not support SMART

dd:

    [root@ceph-53 test]# dd  if=/dev/zero  of=./test_file4  bs=4M count=1024  oflag=sync
    记录了1024+0 的读入
    记录了1024+0 的写出
    4294967296字节(4.3 GB)已复制，44.7233 秒，96.0 MB/秒

fio顺序写

    [root@ceph-53 test]# fio -directory=.  --sync=1  -rw=write -iodepth=1  -bs=4k -size=1G -numjobs=1 -runtime=30 -group_reporting -name=mytest -exit_all
    ...
    write: io=406640KB, bw=13554KB/s, iops=3388 , runt= 30001msec
    ...

fio随机写

    [root@ceph-53 test]# fio -directory=.  --sync=1  -rw=randwrite -iodepth=1  -bs=4k -size=1G -numjobs=1 -runtime=30 -group_reporting -name=mytest_rand -exit_all
    ...
    write: io=59060KB, bw=1968.7KB/s, iops=492 , runt= 30001msec
    ...

iozone

    [root@ceph-53 test]# /root/iozone -a -n 4m -g 4m -i 0 -f ./mytest_iozone -o
    Auto Mode
    Using minimum file size of 4096 kilobytes.
    Using maximum file size of 4096 kilobytes.
    SYNC Mode. 
    Command line used: /root/iozone -a -n 4m -g 4m -i 0 -f ./mytest_iozone -o
    Output is in kBytes/sec
    Time Resolution = 0.000001 seconds.
    Processor cache size set to 1024 kBytes.
    Processor cache line size set to 32 bytes.
    File stride size set to 17 * record size.
                                                                   
    kB  reclen    write  rewrite   
    4096       4    14398    24021                                                                                            
    4096       8    28300    48251                                                                                            
    4096      16    48532    77414                                                                                            
    4096      32    89103   119249                                                                                            
    4096      64   147016   172936                                                                                            
    4096     128   161845   167985                                                                                            
    4096     256   201268   169263                                                                                            
    4096     512    67737   210871                                                                                            
    4096    1024   234461   213590                                                                                            
    4096    2048   270077   342564                                                                                            
    4096    4096   297544   339383             
