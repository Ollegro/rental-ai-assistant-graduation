"""Скачать data/photos с VPS в локальный проект."""
from __future__ import annotations

import sys
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


def main() -> int:
    ssh_cfg = load_env(SSH_ENV)
    app_dir = ssh_cfg.get("VPS_APP_DIR", "/opt/rental-bot")
    remote_photos = f"{app_dir}/data/photos"
    local_photos = ROOT / "data" / "photos"

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
    count = 0

    def walk(remote_dir: str, local_dir: Path) -> None:
        nonlocal count
        local_dir.mkdir(parents=True, exist_ok=True)
        for name in sftp.listdir(remote_dir):
            remote_path = f"{remote_dir}/{name}"
            local_path = local_dir / name
            try:
                sftp.stat(remote_path)
                if str(sftp.stat(remote_path)).startswith("d"):  # fallback
                    pass
            except OSError:
                continue
            mode = sftp.lstat(remote_path).st_mode
            import stat

            if stat.S_ISDIR(mode):
                walk(remote_path, local_path)
            else:
                sftp.get(remote_path, str(local_path))
                count += 1

    import stat

    for name in sftp.listdir(remote_photos):
        remote_path = f"{remote_photos}/{name}"
        local_path = local_photos / name
        if stat.S_ISDIR(sftp.lstat(remote_path).st_mode):
            walk(remote_path, local_path)

    remote_props = f"{app_dir}/data/properties.json"
    sftp.get(remote_props, str(ROOT / "data" / "properties.json"))
    sftp.close()
    client.close()
    print(f"OK: synced {count} photos + properties.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
