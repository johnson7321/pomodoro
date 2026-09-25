"""把封鎖網站塞進 hosts 檔，需要管理員權限。

設計成可被 mock 的純函式 + 一個 stateful 的 facade，方便 UI 呼叫。
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from typing import List

from ..config import BLOCK_END, BLOCK_START, BLOCKED_SITES_FILE, HOSTS_FILE


# ---------------------------------------------------------------------------
# 權限與重啟
# ---------------------------------------------------------------------------
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin() -> bool:
    """以管理員身分重新啟動本程式；成功觸發時回傳 True。"""
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 清單持久化
# ---------------------------------------------------------------------------
def load_sites(path: str = BLOCKED_SITES_FILE) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [str(s) for s in data] if isinstance(data, list) else []
    except Exception:
        return []


def save_sites(sites: List[str], path: str = BLOCKED_SITES_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False, indent=2)


def normalize_site(site: str) -> str:
    s = site.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.rstrip("/")


# ---------------------------------------------------------------------------
# hosts 操作
# ---------------------------------------------------------------------------
def _read_hosts() -> str:
    for enc in ("utf-8", "cp1252"):
        try:
            with open(HOSTS_FILE, "r", encoding=enc, errors="ignore") as f:
                return f.read()
        except Exception:
            continue
    return ""


def _write_hosts(content: str) -> None:
    with open(HOSTS_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _strip_block(content: str) -> str:
    if BLOCK_START in content and BLOCK_END in content:
        before = content[:content.index(BLOCK_START)]
        after = content[content.index(BLOCK_END) + len(BLOCK_END):]
        content = before.rstrip("\n") + "\n" + after.lstrip("\n")
    return content


def apply_block(sites: List[str], enable: bool) -> bool:
    """寫入或移除封鎖區塊。回傳是否成功。
    無管理員權限會直接回 False，由呼叫端決定要不要提示重啟。
    """
    if not is_admin():
        return False
    try:
        content = _strip_block(_read_hosts())
        if enable and sites:
            lines = [BLOCK_START]
            for site in sites:
                site = site.strip()
                if not site:
                    continue
                lines.append(f"127.0.0.1 {site}")
                lines.append(f"127.0.0.1 www.{site}")
            lines.append(BLOCK_END)
            if not content.endswith("\n"):
                content += "\n"
            content += "\n".join(lines) + "\n"
        _write_hosts(content)
        _flush_dns()
        return True
    except Exception as e:
        print(f"[hosts] error: {e}")
        return False


def _flush_dns() -> None:
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass
