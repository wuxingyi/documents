#一些系统参数调整优化

##预读

    /sys/block/sda/queue/read_ahead_kb    128

这个参数对顺序读非常有用，意思是，一次提前读多少内容，无论实际需要多少，设置大些对读大文件有用。可以有效减少seek的次数。这个参数可以使用blockdev -setra来设置。setra设置的是扇区数目。比如设置read_ahead_kb为256,就要blockdev -setra 512, 或者直接echo "256" > /sys/block/sda/queue/read_ahead_kb

##节能

关闭节能可能对性能会有提升，不过应该影响不大，关闭节能在bios里，每个机器可能不一样
