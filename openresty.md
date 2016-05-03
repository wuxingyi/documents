[root@bj-dx-ceph-122-219 ~]# cat work/conf/nginx.conf
worker_processes  1;
error_log logs/error.log debug;
user root;
events {
    worker_connections 1024;
}
http {
    client_max_body_size 64G;
    upstream s1 {
        server  127.0.0.1:80;
    }

    server {
        listen 9000;
        client_body_buffer_size 2m;
        location / {
	    if ($host ~ (contracion|mmspdu|phototasfds)) {
                access_by_lua_file /root/work/conf/limit_put_cors.lua;
            }
            proxy_pass http://s1;
	}

        location ~* ^/passtorgw {
            internal;
            log_subrequest on;
            rewrite ^/passtorgw(.*)$ $1 break;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_pass http://s1;
            access_log logs/upstream.log;
        }

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    }
}


[root@bj-dx-ceph-122-219 ~]# cat work/conf/limit_put_cors.lua
ngx.req.read_body()
local data = ngx.req.get_body_data();
local arry
local action = ngx.var.request_method
local redis = require "resty.redis"
local red = redis.new()
local needRecordBucket = 0
local needRecordCors = 0
local isBucketOp = false
red.connect(red, '127.0.0.1', '6379')
if action == "PUT" then
    arry = {method = ngx.HTTP_PUT, body = data};
end

local host = ngx.req.get_headers()["Host"]
ngx.log(ngx.NOTICE, "HOST=", host)
--local i, j = string.find(ngx.var,"s3.lecloud.com")
local subdomain = string.match(host, "(.+)%.s3%.lecloud%.com")
ngx.log(ngx.NOTICE, "subdomain=", subdomain)
string.split = function(s, p)
    local rt= {}
    string.gsub(s, '[^'..p..']+', function(w) table.insert(rt, w) end )
    return rt
end
local method = ngx.var.request_method
local URI = ngx.var.request_uri
local uri_subresource
local args = ngx.req.get_uri_args()
for key, val in pairs(args) do
    ngx.log(ngx.NOTICE, "key val=", key, val)
    if val == true then
        uri_subresource = key
    end
end
ngx.log(ngx.NOTICE, "uri subresource=", uri_subresource)

if method == 'PUT' and ngx.var.request_uri == '/' then
    ngx.log(ngx.NOTICE, "enter 1", subdomain, "-", ngx.var.uri)
    local hasBucketCreated = red:sismember('bucket_name', subdomain)
    if hasBucketCreated == 1 then
        ngx.log(ngx.NOTICE, "bucket already exist in redis", subdomain)
        ngx.exit(200)
    end
    needRecordBucket = 1
end

if method == 'PUT' and uri_subresource == "cors" then
    ngx.log(ngx.NOTICE, "enter 2", subdomain, "-", ngx.var.uri)
    local hasBucketCorsCreated = red:sismember('bucket_name_cors', subdomain)
    if hasBucketCorsCreated == 1 then
        ngx.log(ngx.NOTICE, "bucket put cors already exist in redis", subdomain)
        ngx.exit(200)
    end
    needRecordCors = 1
end

if needRecordBucket == 1 or needRecordCors == 1 then
    local res1 = ngx.location.capture_multi({{"/passtorgw" .. ngx.var.request_uri, arry},})
    if res1.status == ngx.HTTP_OK then
        if needRecordBucket == 1 then
            red:sadd('bucket_name',subdomain)
            ngx.log(ngx.NOTICE, "redis add record bucket name", subdomain)
        end

        if needRecordCors == 1 then
            red:sadd('bucket_name_cors',subdomain)
            ngx.log(ngx.NOTICE, "redis add record bucket cors", subdomain)
        end
    end
    ngx.say(res1.status)
    ngx.say(res1.body)
end