# -*- coding: utf-8 -*-
"""ComfyUI CORS 代理：8199 -> 8188。
Prompt Forge（webui/tool.html）里的「一键生图」直连 http://127.0.0.1:8199，
由这里把 /prompt /history /view /queue /object_info 等原样转发，并补 CORS 头。
"""
import http.server, socketserver, urllib.request, urllib.error, sys

TARGET = "http://127.0.0.1:8188"
PORT = 8199
CT = "Content-Type"


class P(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")

    def _proxy(self, method):
        url = TARGET + self.path
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(url, data=body, method=method)
        for k, v in self.headers.items():
            if k.lower() in ("host", "content-length", "accept-encoding", "connection",
                             "origin", "referer"):
                continue
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() in ("content-length", "transfer-encoding", "connection",
                                     "content-encoding", "access-control-allow-origin"):
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header(CT, e.headers.get(CT, "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = ("proxy error: %s" % e).encode()
            self.send_response(502)
            self.send_header(CT, "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self._cors()
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print("comfy proxy 127.0.0.1:%d -> %s" % (PORT, TARGET))
    S(("127.0.0.1", PORT), P).serve_forever()
