"""Скачать фото на VPS (там доступ к Unsplash стабильнее) и перезапустить бота."""
from __future__ import annotations

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

    sftp = client.open_sftp()
    remote_scripts = f"{app_dir}/scripts"
    try:
        sftp.stat(remote_scripts)
    except OSError:
        sftp.mkdir(remote_scripts)

    local_script = ROOT / "scripts" / "download_stock_property_photos.py"
    remote_script = f"{remote_scripts}/download_stock_property_photos.py"
    sftp.put(str(local_script), remote_script)
    sftp.close()
    print(f"upload: {local_script.name} -> {remote_script}")

    cmd = (
        f"cd {app_dir} && "
        f"./venv/bin/pip install -q Pillow && "
        f"./venv/bin/python scripts/download_stock_property_photos.py && "
        f"systemctl restart {SERVICE_NAME} && "
        f"sleep 2 && systemctl is-active {SERVICE_NAME}"
    )
    _, stdout, stderr = client.exec_command(cmd, timeout=900, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(out or err)
    client.close()

    if code != 0:
        return 1
    print("OK: фото на VPS обновлены, бот перезапущен")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
