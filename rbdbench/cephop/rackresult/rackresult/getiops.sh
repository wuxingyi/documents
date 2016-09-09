cat $1 | grep iops= | awk -F'iops=' '{print $2}' | awk -F", " '{print $1}'
