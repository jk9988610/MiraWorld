#!/usr/bin/env python3
"""Sync server/ API code to production and restart miraworld-auth (no apt/build on server)."""
from __future__ import annotations

import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy as d
SERVER_DIR = ROOT / "server"
AUTH_ROOT = "/opt/miraworld-auth"


def main() -> int:
    if not SERVER_DIR.is_dir():
        print("server/ missing", file=sys.stderr)
        return 1

    fd, tarball_name = tempfile.mkstemp(prefix="miraworld_srv_", suffix=".tar.gz")
    # mkstemp returns an open file descriptor; close it before tarfile/SFTP use,
    # otherwise Windows keeps the temporary archive locked during cleanup.
    import os
    os.close(fd)
    tarball = Path(tarball_name)
    print(f"打包 server -> {tarball} ...", flush=True)
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(SERVER_DIR, arcname=".")
    remote_tar = f"/tmp/miraworld-server-{uuid.uuid4().hex[:8]}.tar.gz"
    print(f"连接 {d.USER}@{d.HOST} ...", flush=True)
    client = d.connect()
    try:
        sftp = client.open_sftp()
        try:
            print(f"上传 -> {remote_tar}", flush=True)
            sftp.put(str(tarball), remote_tar)
        finally:
            sftp.close()
        cmd = f"""
set -e
sudo mkdir -p {AUTH_ROOT}
sudo tar -xzf {remote_tar} -C {AUTH_ROOT}
sudo rm -f {remote_tar}
sudo chown -R www-data:www-data {AUTH_ROOT}
if [ -d {AUTH_ROOT}/venv ]; then
  sudo {AUTH_ROOT}/venv/bin/pip install -q -r {AUTH_ROOT}/requirements.txt
fi
sudo systemctl restart miraworld-auth.service
curl -s http://127.0.0.1/miraworld/api/health
"""
        print("重启 API ...", flush=True)
        d.run(client, cmd)
        print("API sync done.", flush=True)
        return 0
    finally:
        client.close()
        tarball.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
