"""Очистить профили пользователей на VPS и перезапустить rental-bot."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
SSH_ENV = ROOT / "beget-vps" / "ssh.local.env"
SERVICE_NAME = "rental-bot"


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def main() -> int:
    if not SSH_ENV.exists():
        print(f"Нет {SSH_ENV}", file=sys.stderr)
        return 1

    ssh_cfg = load_env(SSH_ENV)
    app_dir = ssh_cfg.get("VPS_APP_DIR", "/opt/rental-bot")
    users_path = f"{app_dir}/data/users.json"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh_cfg["VPS_HOST"],
        port=int(ssh_cfg.get("VPS_PORT", "22")),
        username=ssh_cfg.get("VPS_USER", "root"),
        password=ssh_cfg["VPS_PASSWORD"],
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )

    payload = json.dumps({"users": {}}, ensure_ascii=False, indent=2)
    sftp = client.open_sftp()
    with sftp.file(users_path, "w") as remote:
        remote.write(payload)
    sftp.close()
    print(f"OK: cleared {users_path}")

    for cmd in (f"systemctl restart {SERVICE_NAME}", f"systemctl is-active {SERVICE_NAME}"):
        _, stdout, stderr = client.exec_command(cmd, get_pty=True)
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace").strip()
        print(out)
        if stdout.channel.recv_exit_status() != 0:
            client.close()
            return 1

    client.close()
    print("OK: bot restarted — напишите /start в Telegram")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
