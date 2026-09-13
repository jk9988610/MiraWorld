#!/usr/bin/env python3
"""Upload pre-built VitePress dist from this VM to admin@8.133.252.224 via SSH.

Run in Cloud Agent VM (two separate steps):
  npm run docs:build
  npm run deploy

Build happens here; the cloud server only receives a tar.gz and extracts it.
No apt/python/pip setup runs on the server during deploy.

Auth priority:
1. MIRAWORLD_SSH_PRIVATE_KEY env (PEM/OpenSSH private key text)
2. MIRAWORLD_SSH_KEY_PATH or ~/.ssh/jk9988610.pem
3. MIRAWORLD_SSH_PASSWORD / interactive getpass
"""
from __future__ import annotations

import getpass
import os
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

import paramiko

HOST = "8.133.252.224"
USER = "admin"
SSH_KEY_NAME = "jk9988610.pem"
SSH_KEY_ENV = "MIRAWORLD_SSH_PRIVATE_KEY"
REMOTE_ROOT = "/var/www/html/miraworld"

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "docs" / ".vitepress" / "dist"


def _resolve_key_path() -> Path | None:
    env_path = os.environ.get("MIRAWORLD_SSH_KEY_PATH", "").strip()
    candidates = []
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.append(Path.home() / ".ssh" / SSH_KEY_NAME)
    for p in candidates:
        if p.is_file():
            return p
    return None


def _materialize_env_key() -> tuple[Path | None, Path | None]:
    raw = os.environ.get(SSH_KEY_ENV, "").strip()
    if not raw:
        return None, None
    if "\\n" in raw and "\n" not in raw:
        raw = raw.replace("\\n", "\n")
    if not raw.endswith("\n"):
        raw += "\n"
    fd, name = tempfile.mkstemp(prefix="miraworld_ssh_", suffix=".pem")
    path = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(raw)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return path, path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    password = os.environ.get("MIRAWORLD_SSH_PASSWORD")

    env_key_path, cleanup = _materialize_env_key()
    key_path = env_key_path or _resolve_key_path()

    kwargs = {
        "hostname": HOST,
        "username": USER,
        "timeout": 20,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if key_path is not None:
        print(f"SSH key: {key_path}", flush=True)
        kwargs["key_filename"] = str(key_path)

    try:
        try:
            if key_path is not None:
                client.connect(**kwargs)
                return client
            raise paramiko.AuthenticationException("no key")
        except paramiko.AuthenticationException:
            try:
                if not password:
                    password = getpass.getpass(f"SSH password for {USER}@{HOST}: ")
                client.connect(
                    hostname=HOST,
                    username=USER,
                    password=password,
                    timeout=20,
                    allow_agent=False,
                    look_for_keys=False,
                )
                return client
            except Exception:
                client.close()
                raise
        except Exception:
            client.close()
            raise
    finally:
        if cleanup is not None:
            cleanup.unlink(missing_ok=True)


def run(client: paramiko.SSHClient, cmd: str, check: bool = True) -> str:
    print(f"$ {cmd}", flush=True)
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip(), flush=True)
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    if check and code != 0:
        raise RuntimeError(f"Command failed ({code}): {cmd}")
    return out


def build_tarball(dist: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="miraworld_dist_", suffix=".tar.gz")
    os.close(fd)
    path = Path(name)
    print(f"打包 dist -> {path} ...", flush=True)
    with tarfile.open(path, "w:gz") as tar:
        tar.add(dist, arcname=".")
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"打包完成: {size_mb:.2f} MB", flush=True)
    return path


def main() -> int:
    print("MiraWorld deploy: 检查本地 dist ...", flush=True)
    if not DIST.is_dir():
        print("Dist missing. Run: npm run docs:build", file=sys.stderr)
        return 1

    tarball = build_tarball(DIST)
    remote_tar = f"/tmp/miraworld-dist-{uuid.uuid4().hex[:8]}.tar.gz"
    print(f"MiraWorld deploy: 连接 {USER}@{HOST} ...", flush=True)
    client = connect()
    try:
        print(f"上传 tar.gz -> {remote_tar} ...", flush=True)
        sftp = client.open_sftp()
        try:
            sftp.put(str(tarball), remote_tar)
        finally:
            sftp.close()
        print("上传完成", flush=True)

        setup = f"""
set -e
sudo mkdir -p {REMOTE_ROOT}
sudo find {REMOTE_ROOT} -mindepth 1 -delete
sudo tar -xzf {remote_tar} -C {REMOTE_ROOT}
sudo rm -f {remote_tar}
sudo chown -R www-data:www-data {REMOTE_ROOT}
echo DEPLOY_OK
curl -sI http://127.0.0.1/miraworld/ | head -n 5
"""
        print("服务器解压发布（仅 tar，无 apt/python）...", flush=True)
        run(client, setup)
        print(f"Done. Open http://{HOST}/miraworld/", flush=True)
        return 0
    finally:
        client.close()
        tarball.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
