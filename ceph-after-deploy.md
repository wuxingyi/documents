# ceph rbd上线须知
本文档记录cep部署之后的后续操作，以便规范ceph上线流程。
## 1.ceph部署
参考http://git.letv.cn/wuxingyi/cephseed-rbd/blob/master/README.md, 进行部署。
## 2.调整crushmap
为了维护ceph的高可用性，需要根据机器所处机房、机柜等物理信息调整crushmap。
具体步骤为：
1.创建各个rack：
```ceph osd crush add-bucket A4-08 rack```
```ceph osd crush add-bucket A4-07 rack```
```ceph osd crush add-bucket A14-15 rack```
```ceph osd crush add-bucket A14-16 rack```
2.将host挪到对应的rack下：
```for i in `seq 10 19`; do ceph osd crush move c-108-$i-plato01-tdxy rack=A4-08; done```
```for i in `seq 20 29`; do ceph osd crush move c-108-$i-plato01-tdxy rack=A4-07; done```
```for i in `seq 30 39`; do ceph osd crush move c-108-$i-plato01-tdxy rack=A14-16; done```
```for i in `seq 40 49`; do ceph osd crush move c-108-$i-plato01-tdxy rack=A14-15; done```
3.将rack挪到root下：
```ceph osd crush move  A4-08 root=default```
```ceph osd crush move  A4-07 root=default```
```ceph osd crush move  A14-15 root=default```
```ceph osd crush move  A14-16 root=default```
4.删除老的crushrule，重建默认的crushrule
```ceph osd crush rule rm replicated_ruleset```
```ceph osd crush rule create-simple replicated_ruleset  default rack firstn```
