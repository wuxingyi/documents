#  S3 ADMIN API说明

1. 所有的admin API使用的endpoint都必须以/admin/开头，否则s3会认为这是普通的上传下载API。
2. 对于所有GET请求，请添加`?format=json`，这样server端会返回比较好处理的json串。
3. 认证算法：S3 ADMIN API需要对每一个HTTP请求的签名进行验证，验证算法请参考：[http://docs.aws.amazon.com/zh_cn/AmazonS3/latest/dev/RESTAuthentication.html](AMAZON S3认证算法)，在我们提供的demo中会有对此算法的实现。
4. 名词解释：

    	4.1. user(用户)：通过uid来标志，可通过ADMIN API进行创建和修改，创建成功之后会给用户提供一组access key和secret key，使用这组key即可进行上传下载等数据操作。
    	4.2. access key和secret key：用户上传下载时必须使用这组key来进行验证。
    	4.3. quota：允许用户使用的存储量，包括最大object个数和最大存储字节数两个维度。

5. 需要实现的S3 ADMIN API及其说明请参考：

    5.1)	创建用户：

		5.1.1.	详情请参考http://ceph.com/docs/master/radosgw/adminops/#create-user 
   		5.1.2.	注意多次调用create-user，会产生多组access key和secret key
    	5.1.3.	注意user-caps参数在任何情况下都不需要设置。
    	5.1.4.	请不要指定access key和secret key，由服务端返回即可。
    	5.1.5.	suspended参数默认是false的，如果需要暂停用户的上传和下载等功能，请使用下面的修改用户API。

    5.2)	修改用户：

		5.2.1.	请参考http://ceph.com/docs/master/radosgw/adminops/#modify-user

	5.3)	获取用户信息：

		5.3.1.	请参考http://ceph.com/docs/master/radosgw/adminops/#get-user-info
		5.3.2.	不指定uid并不能获取到所有用户的信息，请使用7中获取所有用户的API，获取到所有用户的uid，再遍历获取每个用户的信息。

	5.4)	获取用户存储使用量：

		5.4.1.	请参考http://ceph.com/docs/master/radosgw/adminops/#get-usage

	5.5)	设置和修改用户quota:

		5.5.1.	请参考http://ceph.com/docs/master/radosgw/adminops/#set-user-quota
		5.5.2.  设置quota时，必须带上enabled=true来使能quota

	6.6)	获取用户的quota：

		6.6.1.	请参考http://ceph.com/docs/master/radosgw/adminops/#get-bucket-quota


6.	所有HTTP请求都需要使用HTTP 1.1来发起。
7.	获取所有user id：对应的ENDPOINT为：/admin/metadata/user。