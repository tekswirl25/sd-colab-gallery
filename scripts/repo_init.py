import os
import subprocess
import shlex
from scripts.logger import log_info, log_error

def run(cmd, cwd=None):
    """Запускает shell-команду и логирует вывод."""
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        log_error(f"[CMD FAIL] {cmd}\n{res.stderr.strip()}")
        raise RuntimeError(res.stderr)
    out = (res.stdout or "").strip()
    if out:
        log_info(out)
    return out

def init_repo(repo_name: str, origin_url: str, upstream_url: str = "", base_dir: str = "/content"):
    """Клонирует или обновляет репо, переключает рабочую директорию."""
    repo_dir = os.path.join(base_dir, repo_name)

    if not os.path.exists(repo_dir):
        log_info(f"📥 Cloning {origin_url} …")
        run(f"git clone {shlex.quote(origin_url)} {shlex.quote(repo_dir)}")
    else:
        log_info("🔄 Repo exists, pulling latest changes…")

    os.chdir(repo_dir)

    if upstream_url:
        remotes = run("git remote")
        if "upstream" not in remotes.split():
            run(f"git remote add upstream {shlex.quote(upstream_url)}")
            log_info(f"➕ Added upstream {upstream_url}")
        run("git fetch upstream")
        run("git pull --rebase upstream main")
    else:
        run("git fetch origin")
        run("git pull --rebase origin main")

    log_info(f"✅ Repo ready at {repo_dir}")
    log_info(f"📂 Working directory set to {repo_dir}")
    return repo_dir
