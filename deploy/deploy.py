#!/usr/bin/env python3
"""Deploy MiraWorld VitePress dist to admin@8.133.252.224 via SSH.

Auth priority:
1. MIRAWORLD_SSH_PRIVATE_KEY env (PEM/OpenSSH private key text)
2. MIRAWORLD_SSH_KEY_PATH or ~/.ssh/jk9988610.pem
3. MIRAWORLD_SSH_PASSWORD / interactive getpass
"""
from __future__ import annotations

import errno
import getpass
import os
import posixpath
import sys
import tempfile
import uuid
from pathlib import Path

import paramiko

HOST = "8.133.252.224"
USER = "admin"
SSH_KEY_NAME = "jk9988610.pem"
SSH_KEY_ENV = "MIRAWORLD_SSH_PRIVATE_KEY"
REMOTE_ROOT = "/var/www/html/miraworld"
REMOTE_TMP_PREFIX = "/tmp/miraworld-dist"

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "docs" / ".vitepress" / "dist"
NGINX_CONF = ROOT / "deploy" / "nginx-miraworld.conf"
SETUP_NGINX = ROOT / "deploy" / "setup-nginx.sh"


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
    """Write MIRAWORLD_SSH_PRIVATE_KEY to a temp file. Returns (path, cleanup_path)."""
    raw = os.environ.get(SSH_KEY_ENV, "").strip()
    if not raw:
        return None, None
    # Normalize escaped newlines from some secret UIs
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
        print(f"SSH key: {key_path}")
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
    print(f"$ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    if check and code != 0:
        raise RuntimeError(f"Command failed ({code}): {cmd}")
    return out


def _sftp_missing(exc: BaseException) -> bool:
    return isinstance(exc, OSError) and exc.errno in (errno.ENOENT, errno.ENOTDIR)


def sftp_mkdirs(sftp: paramiko.SFTPClient, remote: str) -> None:
    parts = remote.strip("/").split("/")
    cur = ""
    for p in parts:
        cur = f"{cur}/{p}"
        try:
            sftp.stat(cur)
        except OSError as exc:
            if not _sftp_missing(exc):
                raise
            sftp.mkdir(cur)


def upload_dir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    sftp_mkdirs(sftp, remote)
    for path in local.rglob("*"):
        rel = path.relative_to(local).as_posix()
        target = posixpath.join(remote, rel)
        if path.is_dir():
            try:
                sftp.stat(target)
            except OSError as exc:
                if not _sftp_missing(exc):
                    raise
                sftp.mkdir(target)
        else:
            sftp_mkdirs(sftp, posixpath.dirname(target))
            sftp.put(str(path), target)


def main() -> int:
    if not DIST.is_dir():
        print("Dist missing. Run: npm run docs:build", file=sys.stderr)
        return 1

    remote_tmp = f"{REMOTE_TMP_PREFIX}-{uuid.uuid4().hex[:8]}"
    print(f"Connecting to {USER}@{HOST} ...")
    client = connect()
    try:
        run(client, f"mkdir -p {remote_tmp}")
        sftp = client.open_sftp()
        try:
            print(f"Uploading {DIST} -> {remote_tmp}")
            upload_dir(sftp, DIST, remote_tmp)
            sftp.put(str(NGINX_CONF), "/tmp/nginx-miraworld.conf")
            sftp.put(str(SETUP_NGINX), "/tmp/setup-nginx.sh")
        finally:
            sftp.close()

        # Copy site files BEFORE setup-nginx.sh reloads nginx (avoids /miraworld/ 404 race).
        setup = f"""
set -e
sudo mkdir -p {REMOTE_ROOT}
sudo find {REMOTE_ROOT} -mindepth 1 -delete
sudo cp -a {remote_tmp}/. {REMOTE_ROOT}/
sudo rm -rf {remote_tmp}
sudo chown -R www-data:www-data {REMOTE_ROOT}
chmod +x /tmp/setup-nginx.sh
sudo bash /tmp/setup-nginx.sh /tmp/nginx-miraworld.conf
echo DEPLOY_OK
curl -sI http://127.0.0.1/miraworld/ | head -n 8
"""
        run(client, setup)
        print(f"Done. Open http://{HOST}/miraworld/")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
