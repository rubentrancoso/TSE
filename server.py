#!/usr/bin/env python3
import argparse, csv, io, json, os, sqlite3, threading, time, urllib.request, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DATA_DIR=os.path.join(BASE_DIR,"data")
DB_PATH=os.path.join(DATA_DIR,"tse_history.sqlite3")
TSE_URL="https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json"
BACKFILL_URL="https://raw.githubusercontent.com/pedreirorr/painel-eleicao-2026/dados/historico-6257.json"
os.makedirs(DATA_DIR, exist_ok=True)

def n(v):
    try: return int(str(v or "0").replace(".",""))
    except: return 0

def p(v):
    try: return float(str(v or "0").replace(",","."))
    except: return 0.0

def fetch_json(url):
    req=urllib.request.Request(url + ("&" if "?" in url else "?") + "_="+str(int(time.time()*1000)),
        headers={"User-Agent":"TSE-live-dashboard/1.0","Cache-Control":"no-cache"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_tse(d):
    cands={}
    for cargo in d.get("carg",[]):
        if str(cargo.get("cd"))!="1": continue
        for agr in cargo.get("agr",[]):
            for par in agr.get("par",[]):
                partido=par.get("sg","")
                for c in par.get("cand",[]):
                    num=str(c.get("n",""))
                    cands[num]={
                        "numero":num,
                        "nome":c.get("nmu") or c.get("nm") or num,
                        "partido":partido,
                        "sqcand":str(c.get("sqcand","")),
                        "foto":("https://resultados.tse.jus.br/oficial/ele2026/6257/fotos/br/"+str(c.get("sqcand",""))+".jpeg") if c.get("sqcand") else "",
                        "votos":n(c.get("vap")),
                        "pct":p(c.get("pvapn") or c.get("pvap"))
                    }
    s,e,v=d.get("s",{}),d.get("e",{}),d.get("v",{})
    return {
        "dt":d.get("dt") or d.get("dg") or "",
        "ht":d.get("ht") or d.get("hg") or "",
        "pst":p(s.get("pstn") or s.get("pst")),
        "st":n(s.get("st")),"ts":n(s.get("ts")),
        "vv":n(v.get("vv")),"tv":n(v.get("tv")),
        "vb":n(v.get("vb")),"vn":n(v.get("tvn") or v.get("vn")),
        "c":n(e.get("c")),"te":n(e.get("te")),"a":n(e.get("a")),
        "cand":cands,
        "raw":d
    }

class Store:
    def __init__(self):
        self.lock=threading.Lock()
        self.last_error=None
        self.last_poll=None
        self.init()
    def conn(self):
        c=sqlite3.connect(DB_PATH)
        c.row_factory=sqlite3.Row
        return c
    def init(self):
        with self.conn() as c:
            c.execute("""create table if not exists snapshots(
                id integer primary key autoincrement,
                source text not null,
                dt text, ht text, pst real, st integer, ts integer,
                vv integer, tv integer, vb integer, vn integer,
                comparecimento integer, eleitorado integer, abstencao integer,
                candidates_json text not null,
                captured_at text not null,
                raw_json text,
                unique(source,dt,ht,st,vv)
            )""")
    def add(self,x,source):
        with self.lock,self.conn() as c:
            cur=c.execute("""insert or ignore into snapshots
              (source,dt,ht,pst,st,ts,vv,tv,vb,vn,comparecimento,eleitorado,abstencao,candidates_json,captured_at,raw_json)
              values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
              (source,x.get("dt",""),x.get("ht",""),x.get("pst",0),x.get("st",0),x.get("ts",0),
               x.get("vv",0),x.get("tv",0),x.get("vb",0),x.get("vn",0),x.get("c",0),x.get("te",0),x.get("a",0),
               json.dumps(x.get("cand",{}),ensure_ascii=False,separators=(",",":")),
               json.dumps(x.get("raw"),ensure_ascii=False,separators=(",",":")) if x.get("raw") is not None else None))
            return cur.rowcount>0
    def history(self):
        with self.conn() as c:
            rows=c.execute("""select * from snapshots order by
              case when dt like '__/__/____' then substr(dt,7,4)||substr(dt,4,2)||substr(dt,1,2) else dt end, ht, id""").fetchall()
        out=[]
        seen=set()
        for r in rows:
            key=(r["dt"],r["ht"],r["st"],r["vv"])
            if key in seen: continue
            seen.add(key)
            out.append({
                "source":r["source"],"dt":r["dt"],"ht":r["ht"],"pst":r["pst"],"st":r["st"],"ts":r["ts"],
                "vv":r["vv"],"tv":r["tv"],"vb":r["vb"],"vn":r["vn"],"c":r["comparecimento"],
                "te":r["eleitorado"],"a":r["abstencao"],"cand":json.loads(r["candidates_json"])
            })
        return out
    def latest_raw(self):
        with self.conn() as c:
            r=c.execute("select raw_json from snapshots where raw_json is not null order by id desc limit 1").fetchone()
        return json.loads(r[0]) if r and r[0] else None

store=Store()

def collect_once():
    store.last_poll=time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        x=parse_tse(fetch_json(TSE_URL))
        store.add(x,"tse-live")
        store.last_error=None
        return x
    except Exception as e:
        store.last_error=str(e)
        raise

def import_backfill():
    try:
        data=fetch_json(BACKFILL_URL)
        count=0
        for h in data:
            cand={}
            for num,val in (h.get("cand") or {}).items():
                if isinstance(val,list):
                    cand[str(num)]={"numero":str(num),"nome":str(num),"partido":"","votos":n(val[0]),"pct":p(val[1] if len(val)>1 else 0)}
            x={"dt":h.get("dt",""),"ht":h.get("ht",""),"pst":p(h.get("pst")),"st":n(h.get("st")),
               "ts":0,"vv":n(h.get("vv")),"tv":n(h.get("c")),"vb":0,"vn":0,"c":n(h.get("c")),
               "te":0,"a":0,"cand":cand,"raw":None}
            if store.add(x,"public-capture"): count+=1
        return count
    except Exception as e:
        store.last_error="Backfill: "+str(e)
        return 0

def collector(interval):
    while True:
        try: collect_once()
        except: pass
        time.sleep(interval)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=BASE_DIR,**kw)
    def log_message(self,*a): pass
    def end_headers(self):
        self.send_header("Cache-Control","no-store")
        super().end_headers()
    def send_json(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/history":
            return self.send_json({"history":store.history()})
        if path=="/api/status":
            h=store.history()
            return self.send_json({"ok":not bool(store.last_error),"error":store.last_error,"last_poll":store.last_poll,"points":len(h),"latest":h[-1] if h else None})
        if path=="/api/raw/latest":
            return self.send_json(store.latest_raw() or {})
        if path=="/api/export.csv":
            h=store.history(); nums=sorted({n for x in h for n in x["cand"]})
            sio=io.StringIO(); w=csv.writer(sio); w.writerow(["source","dt","ht","pst","st","ts","vv","tv","comparecimento"]+[f"{n}_votos" for n in nums]+[f"{n}_pct" for n in nums])
            for x in h:
                w.writerow([x["source"],x["dt"],x["ht"],x["pst"],x["st"],x["ts"],x["vv"],x["tv"],x["c"]]+
                           [x["cand"].get(n,{}).get("votos",0) for n in nums]+[x["cand"].get(n,{}).get("pct",0) for n in nums])
            b=sio.getvalue().encode("utf-8-sig")
            self.send_response(200); self.send_header("Content-Type","text/csv; charset=utf-8"); self.send_header("Content-Disposition",'attachment; filename="tse_history.csv"')
            self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        if path=="/api/refresh":
            try: return self.send_json({"ok":True,"snapshot":collect_once()})
            except Exception as e: return self.send_json({"ok":False,"error":str(e)},500)
        if path=="/api/backfill/community":
            return self.send_json({"ok":True,"imported":import_backfill()})
        return self.send_json({"error":"not found"},404)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",type=int,default=8765); ap.add_argument("--interval",type=int,default=10)
    ap.add_argument("--no-backfill",action="store_true"); ap.add_argument("--no-browser",action="store_true")
    a=ap.parse_args()
    if not a.no_backfill: import_backfill()
    try: collect_once()
    except: pass
    threading.Thread(target=collector,args=(max(5,a.interval),),daemon=True).start()
    url=f"http://127.0.0.1:{a.port}/"
    print("TSE Live:",url,flush=True)
    if not a.no_browser: threading.Timer(0.8,lambda:webbrowser.open(url)).start()
    ThreadingHTTPServer(("127.0.0.1",a.port),Handler).serve_forever()

if __name__=="__main__": main()
