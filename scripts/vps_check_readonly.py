"""Только чтение: диагностика VPS Beget."""
from __future__ import annotations

from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
SSH_ENV = ROOT / "beget-vps" / "ssh.local.env"


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


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 120) -> None:
    print("\n" + "=" * 70)
    print("$", cmd)
    print("=" * 70)
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    text = (stdout.read() + stderr.read()).decode("utf-8", errors="replace").strip()
    if text:
        print(text[-12000:])


def main() -> None:
    cfg = load_env(SSH_ENV)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        cfg["VPS_HOST"],
        port=int(cfg.get("VPS_PORT", "22")),
        username=cfg.get("VPS_USER", "root"),
        password=cfg["VPS_PASSWORD"],
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )

    commands = [
        "hostname && uptime && date",
        "df -h",
        "df -i",
        "ls -la /opt 2>/dev/null || true",
        "du -sh /opt/* 2>/dev/null | sort -hr | head -20",
        "ls -la /opt/n8n 2>/dev/null || echo 'NO /opt/n8n'",
        "ls -la /opt/rental-bot 2>/dev/null || echo 'NO /opt/rental-bot'",
        "du -sh /opt/rental-bot/* 2>/dev/null | sort -hr || true",
        'docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}" 2>/dev/null || echo docker-not-available',
        "docker system df 2>/dev/null || true",
        "docker volume ls 2>/dev/null || true",
        "systemctl is-active rental-bot 2>/dev/null || echo rental-bot-inactive",
        "systemctl status rental-bot --no-pager 2>/dev/null | head -15 || true",
        "ls -la /var/www 2>/dev/null || true",
        "du -sh /var/www/* 2>/dev/null | sort -hr | head -10 || true",
        "du -sh /var/lib/docker 2>/dev/null || echo no-docker-dir",
        "free -h",
    ]

    for cmd in commands:
        run(client, cmd)

    client.close()
    print("\n" + "=" * 70)
    print("READ-ONLY CHECK COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
