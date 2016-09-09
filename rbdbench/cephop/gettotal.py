import sys

sum=0
f=open(sys.argv[1])
for i in f.readlines():
  sum+=int(i)
print sum
