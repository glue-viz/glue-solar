import re, zlib
b = open("../bursts/young2018.pdf","rb").read()
pages=[]
for m in re.finditer(rb"stream\r?\n", b):
    e = b.find(b"endstream", m.end())
    try: s = zlib.decompressobj().decompress(b[m.end():e])
    except Exception: continue
    if b"BT" not in s or b"TJ" not in s: continue
    out=[]
    for line in s.split(b"\n"):
        for arr in re.findall(rb"\[([^\]]*)\]\s*TJ", line):
            w=""
            for p,n in re.findall(rb"\(((?:\\.|[^\\)])*)\)|(-?\d+\.?\d*)", arr):
                if p: w+=p.decode("latin1")
                elif n and float(n) < -150: w+=" "
            out.append(w)
        out.append("\n") if b"Td" in line and b"-1" in line else None
    t=" ".join(out)
    for a,c in (("\\050","("),("\\051",")"),("\\223",'"'),("\\224",'"'),("\\(","("),("\\)",")")): t=t.replace(a,c)
    pages.append(t)
open("young2018.txt","w").write("\n=====PAGE=====\n".join(pages))
print(len(pages))
