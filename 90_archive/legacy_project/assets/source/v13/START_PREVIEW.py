"""Serve locally only. No installation, Internet connection or uploads required."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import webbrowser,threading
root=Path(__file__).resolve().parent
for port in range(8765,8790):
    try:
        server=ThreadingHTTPServer(('127.0.0.1',port),partial(SimpleHTTPRequestHandler,directory=str(root)))
        break
    except OSError:continue
else:raise SystemExit('利用できるローカルポートがありません。')
url=f'http://127.0.0.1:{port}/web/'
print('CAR PRODUCE ONE v13 —',url,'\n終了: Ctrl+C')
threading.Timer(.5,lambda:webbrowser.open(url)).start()
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()
