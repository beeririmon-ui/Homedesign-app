# qa-agent S21: read a Chromium profile's History database (urls, visits) for the cart id in a fragment. Run with python3 -I.
import sqlite3, sys, shutil, os, json
src = os.path.join(sys.argv[1], 'Default', 'History')
tmp = sys.argv[2]
shutil.copy(src, tmp)
c = sqlite3.connect(tmp)
rows = c.execute("select url, visit_count, typed_count from urls order by id").fetchall()
print(json.dumps({'profile': os.path.basename(sys.argv[1]), 'urls': [r[0].replace('http://127.0.0.1:8830', '') for r in rows], 'with_c': [r[0].replace('http://127.0.0.1:8830', '') for r in rows if '#c=' in r[0]]}, ensure_ascii=False))
