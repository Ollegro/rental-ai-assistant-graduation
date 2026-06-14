"""Безопасный деплой Telegram-бота на VPS Beget (без удаления чужих проектов)."""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent
SSH_ENV = ROOT / "beget-vps" / "ssh.local.env"
LOCAL_ENV = ROOT / ".env"
SERVICE_NAME = "rental-bot"
MIN_FREE_MB = 400

UPLOAD_PATHS = [
    "bot.py",
    "rag.py",
    "config.py",
    "knowledge_base.py",
    "applications.py",
    "personality.py",
    "users.py",
    "keyboards.py",
    "gifts.py",
    "build_index.py",
    "requirements.txt",
    "data/properties.json",
    "prompts/system.txt",
]


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


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 900) -> str:
    print(f"\n$ {cmd[:160]}{'...' if len(cmd) > 160 else ''}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    text = (out or err).encode("ascii", errors="replace").decode("ascii")
    if text.strip():
        print(text.rstrip()[-8000:])
    if code != 0:
        raise RuntimeError(f"Command failed ({code})")
    return out or err


def disk_free_mb(client: paramiko.SSHClient) -> int:
    out = run(client, "df -m / | awk 'NR==2 {print $4}'")
    return int(out.strip().split()[-1])


def check_disk(client: paramiko.SSHClient, step: str) -> None:
    free_mb = disk_free_mb(client)
    print(f"[disk] {step}: свободно {free_mb} MB на /")
    if free_mb < MIN_FREE_MB:
        raise RuntimeError(
            f"Мало места на диске ({free_mb} MB). "
            f"Нужно минимум {MIN_FREE_MB} MB. Деплой остановлен — старые проекты не трогали."
        )


def upload_project(sftp: paramiko.SFTPClient, app_dir: str) -> None:
    for rel in UPLOAD_PATHS:
        local = ROOT / rel
        if not local.exists():
            raise FileNotFoundError(f"Missing file: {local}")
        remote = f"{app_dir}/{rel.replace(chr(92), '/')}"
        remote_dir = os.path.dirname(remote)
        mkdir_p_sftp(sftp, remote_dir)
        print(f"upload: {rel}")
        sftp.put(str(local), remote)


def mkdir_p_sftp(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    path = ""
    for part in parts:
        path += f"/{part}"
        try:
            sftp.stat(path)
        except OSError:
            sftp.mkdir(path)


def build_server_env(app_env: dict[str, str], app_dir: str) -> str:
    lines = []
    seen = set()
    for key, value in app_env.items():
        lines.append(f"{key}={value}")
        seen.add(key)
    if "FAISS_DIR" not in seen:
        lines.append(f"FAISS_DIR={app_dir}/data/faiss_index")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not SSH_ENV.exists():
        print(f"Создайте {SSH_ENV} из beget-vps/ssh.local.env.example", file=sys.stderr)
        return 1
    if not LOCAL_ENV.exists():
        print("Создайте .env из .env.example", file=sys.stderr)
        return 1

    ssh_cfg = load_env(SSH_ENV)
    app_env = load_env(LOCAL_ENV)
    app_dir = ssh_cfg.get("VPS_APP_DIR", "/opt/rental-bot")

    print("=== Безопасный деплой rental-bot ===")
    print("Не удаляем: /opt/n8n, /var/www, Docker volumes, другие проекты.")
    print(f"Рабочая папка: {app_dir}")

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

    run(client, "df -h / && echo '---' && du -sh /opt/n8n /opt/rental-bot /var/www/bloggpt 2>/dev/null || true")
    check_disk(client, "перед деплоем")

    sftp = client.open_sftp()
    run(client, f"mkdir -p {app_dir}/data {app_dir}/prompts")
    upload_project(sftp, app_dir)

    with sftp.file(f"{app_dir}/.env", "w") as remote_file:
        remote_file.write(build_server_env(app_env, app_dir))
    sftp.close()

    setup_script = textwrap.dedent(
        f"""
        set -e
        echo "=== Только rental-bot: переустановка venv и faiss_index ==="
        # Удаляем ТОЛЬКО артефакты нашего бота (не n8n, не /var/www)
        rm -rf {app_dir}/venv {app_dir}/data/faiss_index

        if ! command -v python3 >/dev/null 2>&1; then
          export DEBIAN_FRONTEND=noninteractive
          apt-get update -y
          apt-get install -y python3 python3-venv python3-pip
        fi

        cd {app_dir}
        python3 -m venv venv
        ./venv/bin/pip install --upgrade pip
        ./venv/bin/pip install --no-cache-dir -r requirements.txt
        ./venv/bin/python build_index.py --force

        cat > /etc/systemd/system/{SERVICE_NAME}.service << 'EOFUNIT'
        [Unit]
        Description=Rental AI Telegram Bot
        After=network-online.target
        Wants=network-online.target

        [Service]
        Type=simple
        WorkingDirectory={app_dir}
        Environment=PYTHONUNBUFFERED=1
        ExecStart={app_dir}/venv/bin/python bot.py
        Restart=always
        RestartSec=10

        [Install]
        WantedBy=multi-user.target
        EOFUNIT

        systemctl daemon-reload
        systemctl enable {SERVICE_NAME}
        systemctl restart {SERVICE_NAME}
        sleep 4
        systemctl is-active {SERVICE_NAME}
        systemctl status {SERVICE_NAME} --no-pager -l | tail -n 20
        """
    ).strip()

    check_disk(client, "перед pip install")
    run(client, setup_script, timeout=1200)
    check_disk(client, "после деплоя")
    run(client, "df -h / && docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null || true")

    client.close()

    host = ssh_cfg["VPS_HOST"]
    print("\nDEPLOY_OK")
    print(f"Сервер: {host}")
    print(f"Папка: {app_dir}")
    print(f"Сервис: {SERVICE_NAME}")
    print(f"Логи: ssh root@{host} 'journalctl -u {SERVICE_NAME} -f'")
    print("Остановите локальный bot.py, если он запущен — один BOT_TOKEN = один polling.")
    print("Напишите боту /start в Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
