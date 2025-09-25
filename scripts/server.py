import threading
from flask import Flask
from scripts.gallery_manager import create_app
from scripts.logger import get_last_logs

def start_server(output_dir: str, host: str = "0.0.0.0", port: int = 8000):
    """
    Запуск единого Flask-сервера:
    - UI галереи из gallery_manager
    - /logs для последних 50 строк лога
    """
    app: Flask = create_app(output_dir)

    @app.route("/logs")
    def logs():
        last = get_last_logs(50)
        return """<!doctype html>
<html><head>
<meta charset="utf-8" />
<title>Logs</title>
<meta http-equiv="refresh" content="5" />
<style>
 body{font-family:monospace;background:#111;color:#0f0;padding:16px}
 pre{white-space:pre-wrap}
</style>
</head><body>
<h3>Last 50 logs (auto-refresh 5s)</h3>
<pre>{}</pre>
</body></html>""".format("".join(last))

    th = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    th.start()
