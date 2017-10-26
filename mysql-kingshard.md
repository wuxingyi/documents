# Mysql+Kingshard集群部署

## 背景相关：
Mysql本身提供Master-slave replication的功能，即binary log(binlog)

Binlog采用半同步方式(semi-sync)进行主从间的复制，具体可参见【1】,所以主从间的数据能够保证实时的同步，因为只有当数据同时被写入到Master和slave的log后，主设备才会提交commit，返回用户提交成功，从而保证数据一致性。

这时我们就拥有了一个可供写的主设备，以及一个或多个用来读的设备，进一步我们可以加入proxy，来帮助实现读写分离功能。这里将选取kingshard作为前端proxy。

Replication设置：
两台Mysql数据库服务器，分别作为master和slave节点。初始状态时需要保证master、slave的数据信息一致，这点是此架构保证数据一致性的基础：通过一致的初始状态，slave实时同步复制master的所有操作，保证数据的一致性。如果初始数据不一致，可以使用mysql提供的mysqldunmp将Master的数据导入到slave中，具体参见【2】。

## 配置参数：
	操作系统：CentOS 7
	Mysql 5.7/mariaDB 10.2
	Kingshard: https://github.com/flike/kingshard

## Mysql配置
### 1.创建用户
	Master需要在数据库中创建一个用来replication的user，每个slave使用标准的Mysql用户名和密码来连接Master。进行replication的用户应当被赋予REPLICATION SLAVE的权限。如下：
      	Mysql > create user ‘replicator’@‘%’ identified by ‘Replicator@1’;
      	Mysql > grant replication slave on *.* to ‘replicator’@‘%’ identified by ‘Replicator@1’;
	此处建立用户名为replicator，任意ip地址(%通配符表任意)，密码为Replicator@1的user，其他slave可以通过此user连接到Master进行replication任务。

### 2.配置master
	修改/etc/my.cnf，添加如下信息到[mysqld]下：
		server-id = 1
		log-bin = /var/log/mysql/mysql-bin.log
	server-id 表示为Master的id值，一般取1；
	log-bin 为binlog的change log
	重启Master，使刚才的修改生效，运行SHOW MASTER STATUS查看Master状态(important，后续操作需要此处信息)

### 3.配置slave
	slave与Master修改类似，在/etc/my.cnf中加入如下信息，然后重启slave的mysql：
	server-id = 2
	server-id是必须的，且唯一的。

### 4.启动slave
	登录到mysql后(slave本地用户，root即可)，使用change master命令来连接master(不要配置此命令涉及的相关参数到my.cnf中，以此来保持灵活性)
		mysql >  CHANGE MASTER TO MASTER_HOST = ‘/*master的ip地址或域名*/’,
	      	>  MASTER_USER = ‘replicator’,   /*在Master上创建的用来replication的user*/
	      	>  MASTER_PASSWORD = ‘Replicator@1’,    /*该user的password*/
	      	>  MASTER_LOG_FILE = ‘’,      /*show master status中的File内容*/
	      	>  MASTER_LOG_POSE = ‘’       /*show master status中的Position内容*/
	如果执行结果提示成功，则成功配置slave节点；如果提示不能配置一个运行中的slave，则需要执行 stop slave，这表明在此mysql上正在运行着一个slave，需要停止该slave，然后运行上面change命令，才能修改成功，且成功后运行start slave使slave再次运行起来.

### 5.查看配置是否成功
运行命令SHOW SLAVE STATUS，此命令用来显示当前设置下slave的状态信息：

      其中需要注意的有：
      Slave_IO_State 当为waiting for master to send event
      Slave_IO_Running Slave_SQL_Running 当二者为yes
      表示当前master-slave架构连接成功

## Kingshard部署
Kingshard是使用源码进行安装，但本身的架构简单，所以下载、安装、部署和配置比较简单
，参见【5】中有很详细的步骤，按照1~5的步骤操作下来，就生成了我们所需要的kingshard程序

## Mysql+Kingshard配置
Kingshard提供两个配置文件，分别对应于分表模式和不分表模式。
在此次部署中，我们考虑到如果使用kingshard的分表功能，将会提升系统的复杂度，不易维护。因此我们将使用不分表的模式，即需要修改和使用的配置文件为etc/unshard.yaml

### 1.配置mysql
	作为proxy，kingshard将接管所有来自client的连接，然后转发接收到的命令到对应的server上。因此kingshard需要连接到每个mysql数据库的权限，需要在每个mysql创建一个user，来保证kingshard能够连接上:
      mysql > create user ‘kingshard’@‘xxxx’ identified by ‘Kingshard@1’     /*xxxx代表kingshard 所在server ip或域名*/
     并授予相对应的权限(读or写)
### 2.配置etc/unshard.yaml
	  2.1 修改nodes下node1的user和password为上步骤中创建的用户名和密码
      2.2 修改master为mysql master的ip，需要加端口3306
      2.3 修改slave为mysql slave的ip，需要加端口3306和读权重’@n’, n为大于1的整数值
### 3.运行kingshard
	确认每个node上的mysql server都在运行后，启动kingshard(在kingshard的目录内)
	./bin/kingshard -config=etc/unshard.yaml

## 测试系统
	使用mysql -u kingshar -pkingshard -P9696 连接到kingshard，执行不同的sql语句，可以在kingshard的log中显示对应的去向。

## 相关
	深入理解mysql master-slave replication，请参照链接：
	【1】 http://www.orczhou.com/index.php/2011/07/why-and-how-mysql-5-5-semi-sync-replication/
	【2】 https://dev.mysql.com/doc/refman/5.7/en/mysqldump.html
	【3】 http://blog.csdn.net/hguisu/article/details/7325124
	【4】 https://dev.mysql.com/doc/refman/5.7/en/replication.html
	【5】 https://github.com/flike/kingshard/blob/master/doc/KingDoc/kingshard_install_document.mc