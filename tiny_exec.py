import subprocess as sp
import json as j
import os
os.chdir(r"D:\JemmaRepo\Jemma")
d={}
for n,c,t in [("s1",["python","--version"],10),("s2",["python","-c","import sys;print('E:',sys.executable);print('V:',sys.version_info)"],10),("s3",["python","-m","pip","list"],30),("s4",["python","-m","pip","install","-e","."],120),("sup",["python","-m","pip","list"],30)]:
 try:
  r=sp.run(c,capture_output=True,text=True,timeout=t)
  d[n]={'c':' '.join(c),'o':r.stdout,'e':r.stderr,'x':r.returncode}
 except Exception as ex:
  d[n]={'c':' '.join(c),'o':'','e':str(ex),'x':-1}
print(j.dumps(d))
