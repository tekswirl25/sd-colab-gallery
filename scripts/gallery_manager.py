import os, time, json, shutil, threading
import nest_asyncio
from flask import Flask, send_file, redirect, url_for, render_template_string, abort

# Универсальные утилиты (можно вынести в scripts/utils.py)
def list_images(folder):
    return sorted(
        [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))],
        key=lambda x: os.path.getmtime(os.path.join(folder, x)),
        reverse=True
    )

def folder_stats(folder):
    files = list_images(folder)
    total_bytes = sum(os.path.getsize(os.path.join(folder, f)) for f in files)
    return files, total_bytes

# HTML шаблон
INDEX_HTML = r'''
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Gallery Manager</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;background:#faf6ee;margin:0;padding:20px;color:#2b2b2b}
    header{display:flex;gap:16px;align-items:center;justify-content:space-between;margin-bottom:12px}
    .stats{font-weight:600}
    .btn{background:#3b6e57;color:#fff;padding:10px 14px;border-radius:10px;border:none;cursor:pointer;text-decoration:none}
    .btn.danger{background:#9c2b2b}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
    .card{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden}
    .card img{width:100%;height:280px;object-fit:cover;display:block}
    .card .meta{padding:10px;font-size:13px;line-height:1.35}
    .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
    .tiny{font-size:12px;color:#555}
    .filename{font-weight:600}
  </style>
</head>
<body>
  <header>
    <div class="stats">Files: {{count}} | Total: {{size_mb}} MB</div>
    <div>
      <a class="btn" href="{{url_for('download_all')}}">Download all (zip)</a>
      <a class="btn danger" href="{{url_for('delete_all')}}" onclick="return confirm('Delete ALL images?')">Delete all</a>
    </div>
  </header>
  <div class="grid">
  {% for item in items %}
    <div class="card">
      <a href="/outputs/{{item.filename}}" target="_blank">
        <img src="/outputs/{{item.filename}}" alt="{{item.filename}}"/>
      </a>
      <div class="meta">
        <div class="filename">{{item.filename}}</div>
        <div class="tiny">size: {{item.size_kb}} KB</div>
        {% if item.meta %}
          <div class="tiny">variant: {{item.meta.model_variant}}</div>
          <div class="tiny">mode: {{item.meta.mode}}</div>
          <div class="tiny">tone: {{item.meta.color_tone}}</div>
          <div class="tiny">seed: {{item.meta.seed}}</div>
        {% endif %}
        <div class="row">
          <a class="btn" href="/outputs/{{item.filename}}" download>Download</a>
          <a class="btn danger" href="{{url_for('delete_one', filename=item.filename)}}" onclick="return confirm('Delete this image?')">Delete</a>
          {% if item.meta %}
          <button class="btn" onclick="copyText('{{item.meta.seed}}')">Copy Seed</button>
          <button class="btn" onclick="copyText(`{{item.meta.prompt | replace('`','\\`') | replace('\\n',' ') }}`)">Copy Prompt</button>
          {% endif %}
        </div>
      </div>
    </div>
  {% endfor %}
  </div>
  <script>
    async function copyText(t){
      try{ await navigator.clipboard.writeText(String(t||'')); alert('Copied!'); }
      catch(e){ alert('Copy failed'); }
    }
  </script>
</body>
</html>
'''

def create_app(output_dir):
    nest_asyncio.apply()
    app = Flask(__name__, static_folder=output_dir, static_url_path='/outputs')

    @app.route('/')
    def index():
        files, total_bytes = folder_stats(output_dir)
        items = []
        for fn in files:
            fp = os.path.join(output_dir, fn)
            size_kb = int(os.path.getsize(fp)/1024)
            stem = os.path.splitext(fn)[0]
            meta_path = os.path.join(output_dir, stem + '.json')
            meta = None
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                except Exception:
                    meta = None
            items.append({"filename": fn, "size_kb": size_kb, "meta": meta})
        size_mb = round(total_bytes/1024/1024, 2)
        return render_template_string(INDEX_HTML, count=len(files), size_mb=size_mb, items=items)

    @app.route('/download_all')
    def download_all():
        zip_path = os.path.join(output_dir, 'outputs_all.zip')
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.make_archive(zip_path.replace('.zip',''), 'zip', output_dir)
        return send_file(zip_path, as_attachment=True)

    @app.route('/delete_all')
    def delete_all():
        for f in os.listdir(output_dir):
            try:
                os.remove(os.path.join(output_dir, f))
            except Exception:
                pass
        return redirect(url_for('index'))

    @app.route('/delete/<path:filename>')
    def delete_one(filename):
        safe = os.path.basename(filename)
        fp = os.path.join(output_dir, safe)
        if not os.path.exists(fp):
            abort(404)
        os.remove(fp)
        stem = os.path.splitext(safe)[0]
        meta_path = os.path.join(output_dir, stem + '.json')
        if os.path.exists(meta_path):
            try:
                os.remove(meta_path)
            except Exception:
                pass
        return redirect(url_for('index'))

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
