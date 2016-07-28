# ceph osd reweight manual
  在ceph部署之后，创建pool时，在各个osd之间，会存在pg个数非常不均匀的情况，本手册的目的在于通过ceph osd reweight来减轻这种不均匀现象。

## 1.命令行
  1.ceph osd reweight-by-pg 101 test
  调整osd的weight，使得拥有最多pg的osd拥有的pg个数与平均pg个数的比例为101/100。这个101是因为这个参数为必须大于100的整数，101能保证次优的pg分布。另外，这个命令行需要制定poolname，即test。
  2.ceph osd test-reweight-by-pg 101 test
  这一命令行的作用是只进行reweight的计算，但是不修改weight，通过这条命令行可以看到reweight操作的预期影响。
  3.ceph osd utilization
  它可以展示当前拥有最多/最少pg的osd，以及偏离情况。
  4.ceph osd df
  它可以展示各个osd的实际磁盘使用量，因为尽管pg较为均为，但磁盘使用量均匀才是我们的最终目标，因此它展示的数据均匀与否才是reweight操作是否有效的唯一标准。

## 2.使用
  1.在某些场景下，osd可能会只有一个pool，比如HDD的.rgw.buckets以及VaaS的video，而在另外一些场景下，可能会有多个pool，比如rbd使用场景下，需要有vms、images及volumes等多个pool。对于多个pool的情况，使用reweight时，采取的方式是按照预期数据量大小顺序来进行调整，因为对后面的pool的weight调整，会影响之前已经调整好的pool的weight。比如根据经验来看，images和vms会拥有较少的数据量，而volumes这个pool通常会具有较多的数据量，因此reweight的顺序就应该是volumes->vms->images。事实上，一种更为妥当的方式时，只调整具有决定性作用的pool即可，因为像images这样的pool，数据量实际上跟volumes这种pool差一两个数量级。
  2.进行reweight时，一次操作很大概率是不能够将数据完美分布的，所有reweight操作需要进行多次, 并通过前述ceph osd utilization命令行观察pg是否已经分布较为均匀。在pool创建完之后，最合理的方式是通过rados bench向这个pool中写入一定量的数据(比如总容量的5%)，在reweight操作之后，即可以通过ceph osd df命令行观察数据的分布情况。
  
## 3.数据均匀的标准
前面提到，只有通过ceph osd df看到的数据均匀，才是真正的数据均匀。一般而言，达到最大与平均之比为1.05左右即可认为调整成功。
  


