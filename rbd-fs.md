# provide file system interface with rbd block device
## rbd-fuse

```
rbd create -p rbd test --image-format 2 --size 1024G
mkdir -p /rbd_images
rbd-fuse -p rbd /rbd_images
mkfs.xfs /rbd_images/test
mkdir -p /mnt/fuse
mount /rbd_images/test /mnt/fuse
```

## rbd kernel module
```
rbd create -p rbd test2 --image-format 2 --size 1024G
rbd map rbd/test2 #this command line returns a block device like /dev/rbd0
mkfs.xfs /dev/rbd0
mkdir /mnt/kernel
mount /dev/rbd0 /mnt/kernel
```
