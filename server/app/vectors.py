"""sqlite-vec exact vector search; permission filtering happens before ranking.
Default hashed character features are lexical, NOT semantic embeddings.
Configure EMBEDDING_* for OpenAI-compatible semantic embeddings.
"""
import hashlib,json,math,os,struct
from urllib.request import Request,urlopen

def embed(text):
    name=os.getenv('EMBEDDING_MODEL','')
    base=os.getenv('EMBEDDING_BASE_URL','').rstrip('/')
    key=os.getenv('EMBEDDING_API_KEY','')
    if name and base and key:
        if not base.startswith('https://'): raise ValueError('Embedding 地址需要 HTTPS')
        req=Request(base+'/embeddings',data=json.dumps({'model':name,'input':text}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
        with urlopen(req,timeout=30) as r: v=json.load(r)['data'][0]['embedding']
        if not v or not all(isinstance(x,(float,int)) and math.isfinite(x) for x in v): raise ValueError('无效向量')
        return v,'remote:'+base+':'+name
    text=''.join(text.lower().split());v=[0.0]*256
    for n in (1,2,3):
        for i in range(max(0,len(text)-n+1)):
            h=int.from_bytes(hashlib.sha256(text[i:i+n].encode()).digest()[:4],'big');v[h%256]+=1
    norm=math.sqrt(sum(x*x for x in v)) or 1
    return [x/norm for x in v],'local-charhash-v1'

def pack(v): return struct.pack('<'+'f'*len(v),*v)

def enable(db):
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
