# scripts/gallery_manager.py

import os, time, json, shutil, threading
import nest_asyncio
from flask import Flask, send_file, redirect, url_for, render_template_string, abort
from scripts.logger import LOG_FILE
from scripts.utils import list_images

def create_app(output_dir):
    nest_asyncio.apply()
    app = Flask(__name__, static_folder=output_dir, static_url_path='/outputs')

    INDEX_HTML = "<h2>Gallery will be here</h2>"

    @app.route('/')
    def index():
        files = list_images(output_dir)
        items = [{"filename": f, "size_kb": int(os.path.getsize(os.path.join(output_dir, f))/1024)} for f in files]
        return {"count": len(items), "items": items}

    @app.route('/logs')
    def show_logs():
        if not os.path.exists(LOG_FILE): return "<pre>No logs yet</pre>"
        with open(LOG_FILE,'r') as f: lines=f.readlines()
        last = "".join(lines[-200:])
        return f"<pre>{last}</pre>"

    return app

def start_gallery(output_dir, port=8000, in_colab=True):
    app = create_app(output_dir)
    th = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True)
    th.start()
    try:
        if in_colab:
            from google.colab import output as colab_output
            print("Starting gallery…")
            time.sleep(1)
            url = colab_output.eval_js(f'google.colab.kernel.proxyPort({port}, {{"cache\": false}})')
            print("👉 Open Gallery:", url)
        else:
            print(f"Gallery running on http://127.0.0.1:{port}")
    except Exception:
        print(f"Gallery running on http://127.0.0.1:{port}")
