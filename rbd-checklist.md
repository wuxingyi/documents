#rbd上线checklist

1.monitor是否已经分布于多个rack
在选择conf/monhost中确定

2.crushmap是否已经根据rack、host进行了修改
参考ceph-after-deploy.md

3.是否已经将root=default改成了相应的az名
ceph osd crush rename-bucket default az1

4.是否已经在ceph.conf中显式关闭了rbd cache
nova.conf已经默认关闭了rbd cache.

5.是否修改了默认的crush rule的挑选规则为rack
ceph osd crush rule create-simple replicated_ruleset  default rack firstn

6.是否修改了默认crush rule名
删除老的rule，创建新的.

7.是否在创建pool时显式指定了crush rule
ceph osd pool create compute-108-10 1024 1024 replicated_ruleset1

8.是否检查了各个osd的crush weight能跟实际容量匹配
ceph osd df或者ceph osd tree可以看到crush weight

9.在创建volumes这个pool之后，是否通过reweight-by-pg进行了reweight操作

10.各个节点的diamond是否能正常运行

11.各个节点时钟是否能够完全一致

12.是否已经添加了watchceph监控项，用以进行短信、电话告警

13.是否对ceph-osd@.service设置了taskset CPU限制
