"""Upload local .env (+ optional files) to VPS and restart rental-bot."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
SSH_ENV = ROOT / "beget-vps" / "ssh.local.env"
LOCAL_ENV = ROOT / ".env"


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
    if not SSH_ENV.exists() or not LOCAL_ENV.exists():
        print("Missing ssh.local.env or .env", file=sys.stderr)
        return 1

    ssh_cfg = load_env(SSH_ENV)
    app_env = load_env(LOCAL_ENV)
    app_dir = ssh_cfg.get("VPS_APP_DIR", "/opt/rental-bot")
    service = ssh_cfg.get("VPS_SERVICE", "rental-bot")

    lines = [f"{key}={value}" for key, value in app_env.items()]
    if "FAISS_DIR" not in app_env:
        lines.append(f"FAISS_DIR={app_dir}/data/faiss_index")
    env_text = "\n".join(lines) + "\n"

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
    with sftp.file(f"{app_dir}/.env", "w") as remote_file:
        remote_file.write(env_text)
    config_path = ROOT / "config.py"
    if config_path.exists():
        with sftp.file(f"{app_dir}/config.py", "w") as remote_file:
            remote_file.write(config_path.read_text(encoding="utf-8"))
    sftp.close()

    _, stdout, stderr = client.exec_command(f"systemctl restart {service} && systemctl is-active {service}")
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    client.close()

    if err:
        print(err, file=sys.stderr)
        return 1
    print(f"OK: {service} is {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
