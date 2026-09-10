#!/usr/bin/env python3
"""Deploy MiraWorld VitePress dist to admin@8.133.252.224 via SSH.

Auth: prefers existing SSH keys; falls back to password from
MIRAWORLD_SSH_PASSWORD env, or interactive getpass.
"""
from __future__ import annotations

import getpass
import os
import posixpath
import stat
import sys
from pathlib import Path

import paramiko

HOST = "8.133.252.224"
USER = "admin"
WEB_ROOT = "/var/www/html"
REMOTE_ROOT = "/var/www/html/miraworld"
REMOTE_TMP = "/tmp/miraworld-dist"

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "docs" / ".vitepress" / "dist"
NGINX_CONF = ROOT / "deploy" / "nginx-miraworld.conf"


def connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = Path.home() / ".ssh" / "id_ed25519"
    password = os.environ.get("MIRAWORLD_SSH_PASSWORD")

    kwargs = {
        "hostname": HOST,
        "username": USER,
        "timeout": 20,
        "allow_agent": True,
        "look_for_keys": True,
    }
    if key_path.exists():
        kwargs["key_filename"] = str(key_path)

    try:
        client.connect(**kwargs)
        return client
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


def sftp_mkdirs(sftp: paramiko.SFTPClient, remote: str) -> None:
    parts = remote.strip("/").split("/")
    cur = ""
    for p in parts:
        cur = f"{cur}/{p}"
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            sftp.mkdir(cur)


def upload_dir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    sftp_mkdirs(sftp, remote)
    for path in local.rglob("*"):
        rel = path.relative_to(local).as_posix()
        target = posixpath.join(remote, rel)
        if path.is_dir():
            try:
                sftp.stat(target)
            except FileNotFoundError:
                sftp.mkdir(target)
        else:
            sftp_mkdirs(sftp, posixpath.dirname(target))
            sftp.put(str(path), target)


def main() -> int:
    if not DIST.is_dir():
        print("Dist missing. Run: npm run docs:build", file=sys.stderr)
        return 1

    print(f"Connecting to {USER}@{HOST} ...")
    client = connect()
    try:
        run(client, f"rm -rf {REMOTE_TMP} && mkdir -p {REMOTE_TMP}")
        sftp = client.open_sftp()
        try:
            print(f"Uploading {DIST} -> {REMOTE_TMP}")
            upload_dir(sftp, DIST, REMOTE_TMP)
            sftp.put(str(NGINX_CONF), "/tmp/nginx-miraworld.conf")
        finally:
            sftp.close()

        setup = f"""
set -e
sudo mkdir -p /etc/nginx/snippets {REMOTE_ROOT}
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
sudo cp /tmp/nginx-miraworld.conf /etc/nginx/snippets/miraworld.conf
DEFAULT_SITE=/etc/nginx/sites-enabled/default
if [ ! -e "$DEFAULT_SITE" ]; then
  DEFAULT_SITE=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -n 1 || true)
fi
if [ -n "$DEFAULT_SITE" ] && ! grep -q 'snippets/miraworld.conf' "$DEFAULT_SITE"; then
  sudo cp "$DEFAULT_SITE" "$DEFAULT_SITE.bak.miraworld"
  sudo sed -i 's|^}}|    include /etc/nginx/snippets/miraworld.conf;\\n}}|' "$DEFAULT_SITE" || true
  if ! grep -q 'snippets/miraworld.conf' "$DEFAULT_SITE"; then
    sudo awk 'BEGIN{{c=0}} /^}}/{{c++}} {{print}} END{{}}' "$DEFAULT_SITE" >/dev/null
    tmp=$(mktemp)
    sudo awk '
      {{ lines[NR]=$0 }}
      END {{
        for (i=1;i<=NR;i++) {{
          if (i==NR && lines[i] ~ /^}}/) {{
            print "    include /etc/nginx/snippets/miraworld.conf;"
          }}
          print lines[i]
        }}
      }}
    ' "$DEFAULT_SITE" > "$tmp"
    sudo cp "$tmp" "$DEFAULT_SITE"
    rm -f "$tmp"
  fi
fi
sudo find {REMOTE_ROOT} -mindepth 1 -delete
sudo cp -a {REMOTE_TMP}/. {REMOTE_ROOT}/
sudo chown -R www-data:www-data {REMOTE_ROOT}
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
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
