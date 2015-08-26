## bucket 和 object

1. bucket名称全局唯一
2. Bucket不能是中文,可以包括数字,-, 字母
3. object的名称任意
4. 最多1000个bucket, amazon最多100个bucket

## 目录结构

	S3可以模拟目录结构
	http://docs.aws.amazon.com/AmazonS3/latest/API/RESTBucketGET.html
	
## 接入速度

	上传目前只有北京节点, 以后会增加

## 大文件续传

大于4M, Multipart方式

	1. Initiate Multipart Upload => uploadid
	2. Upload Part

		PUT /ObjectName?partNumber=PartNumber&uploadId=UploadId HTTP/1.1
		Host: BucketName.s3.amazonaws.com
		Date: date
		Content-Length: Size
		Authorization: authorization string

	3. Complete Multipart Upload


续传
	1. List Parts => md5sum
	2. Skip parts which md5sum match
	3. Upload remaining parts
	4. Complete Multipart Upload

取消上传

	1. Abort Multipart Upload

## 文件管理

1. ACL

	object:
		public-read
	CDN可以读取

	bucket:
		public-read 之后不能上传

2. RENAME

	s3不能rename, 可以用copy操作

## CDN 分发

1. 上传的文件是public-read, object就可以通过

http://s3.lecloud.com/{bucketname}/{objectname}直接访问

2. 拼接url

http://s3-cdn.lecloud.com/{bucketname}/{objectname}直接访问

## CDN分析

1. Private Object

curl -v http://s3-cdn.lecloud.com/test/README.md

	> GET /test/README.md HTTP/1.1
	> User-Agent: curl/7.35.0
	> Host: s3-cdn.lecloud.com
	> Accept: */*
	> 


	< HTTP/1.1 302 Moved
	< Location: http://119.188.122.50/coopcdn/s3-cdn.lecloud.com/test/README.md?geo=CN-1-9-2&tm=1423757400&key=4dd9400762c4b43fe8877a58c42e402d&platid=0&splatid=0&its=0&keyitem=platid,splatid,its&ntm=1423757400&nkey=4dd9400762c4b43fe8877a58c42e402d&proxy=2008855756,2007471065,1981430552&errc=0&gn=751&buss=59886&qos=4&cips=10.58.180.187&lersrc=czMubGVjbG91ZC5jb20=&tag=letvs3test&cuhost=s3-cdn.lecloud.com&sign=coopdown&fext=.md
	< Desc: CN.1.9.2@SD-JN-CNC2.751@0.59886
	< Content-Type: text/plain; charset=utf-8
	* Server letv/gslb/2014-11-13 is not blacklisted
	< Server: letv/gslb/2014-11-13
	< Pragma: no-cache
	< Cache-Control: no-cache, no-store
	< Connection: keep-alive
	< Date: Thu, 12 Feb 2015 06:09:27 GMT
	< Content-Length: 0


	curl -v 'http://119.188.122.50/coopcdn/s3-cdn.lecloud.com/test/README.md?geo=CN-1-9-2&tm=1423757400&key=4dd9400762c4b43fe8877a58c42e402d&platid=0&splatid=0&its=0&keyitem=platid,splatid,its&ntm=1423757400&nkey=4dd9400762c4b43fe8877a58c42e402d&proxy=2008855756,2007471065,1981430552&errc=0&gn=751&buss=59886&qos=4&cips=10.58.180.187&lersrc=czMubGVjbG91ZC5jb20=&tag=letvs3test&cuhost=s3-cdn.lecloud.com&sign=coopdown&fext=.md'


	< HTTP/1.1 403 Forbidden
	* Server letv/2015-02-11/5.82/letv is not blacklisted
	< Server: letv/2015-02-11/5.82/letv
	< Date: Thu, 12 Feb 2015 06:09:52 GMT
	< Content-Type: application/xml
	< Connection: keep-alive
	< Accept-Ranges: bytes
	< Content-Length: 78
	< Age: 0


2. 问题

第一次访问有可能比较慢

3. 同名文件

	1. 改名上传
	2. 先检查文件是否存在
	

## 不支持

1. object policy
2. object version
3. 转码
