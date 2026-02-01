import base64
import json
import os
import platform
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

try:
    import psutil
except Exception:
    psutil = None


@dataclass
class Account:
    id: str
    name: str
    token: str
    binary_data: Optional[bytes] = None
    created_at: Optional[float] = None
    expires_at: Optional[float] = None


def get_app_dir() -> Path:
    system = platform.system().lower()
    if system == "windows":
        base = os.environ.get("APPDATA", str(Path.home()))
        return Path(base) / "RobloxAccountManager"
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / "RobloxAccountManager"
    return Path.home() / ".config" / "RobloxAccountManager"


def get_accounts_path() -> Path:
    return get_app_dir() / "accounts.json"


def get_key_path() -> Path:
    return get_app_dir() / "key.key"


def ensure_app_dir() -> None:
    get_app_dir().mkdir(parents=True, exist_ok=True)


def load_or_create_key() -> bytes:
    ensure_app_dir()
    key_path = get_key_path()
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return key


def get_fernet() -> Fernet:
    return Fernet(load_or_create_key())


def encrypt_token(token: str) -> str:
    fernet = get_fernet()
    return fernet.encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted: str) -> str:
    fernet = get_fernet()
    return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")


def encrypt_bytes(data: bytes) -> str:
    fernet = get_fernet()
    encrypted = fernet.encrypt(data)
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_bytes(encrypted: str) -> bytes:
    try:
        fernet = get_fernet()
        decoded = base64.b64decode(encrypted.encode("utf-8"))
        return fernet.decrypt(decoded)
    except Exception:
        return b""

def _load_raw() -> dict:
    ensure_app_dir()
    accounts_path = get_accounts_path()
    if not accounts_path.exists():
        return {"version": 1, "accounts": [], "last_selected_id": None}
    try:
        return json.loads(accounts_path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "accounts": [], "last_selected_id": None}


def _save_raw(data: dict) -> None:
    ensure_app_dir()
    accounts_path = get_accounts_path()
    accounts_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_accounts() -> Tuple[List[Account], Optional[str]]:
    data = _load_raw()
    accounts = []
    for entry in data.get("accounts", []):
        try:
            token = decrypt_token(entry["token"])
        except (InvalidToken, KeyError, TypeError):
            continue
        
        binary_data = None
        if "binary_data" in entry and entry["binary_data"]:
            binary_data = decrypt_bytes(entry["binary_data"])
            
        accounts.append(Account(
            id=entry["id"], 
            name=entry["name"], 
            token=token, 
            binary_data=binary_data,
            created_at=entry.get("created_at"),
            expires_at=entry.get("expires_at")
        ))
    return accounts, data.get("last_selected_id")


def save_accounts(accounts: List[Account], last_selected_id: Optional[str] = None) -> None:
    account_list = []
    for acc in accounts:
        entry = {
            "id": acc.id,
            "name": acc.name,
            "token": encrypt_token(acc.token)
        }
        if acc.binary_data:
            entry["binary_data"] = encrypt_bytes(acc.binary_data)
        if acc.created_at:
            entry["created_at"] = acc.created_at
        if acc.expires_at:
            entry["expires_at"] = acc.expires_at
        account_list.append(entry)
        
    payload = {
        "version": 1,
        "accounts": account_list,
        "last_selected_id": last_selected_id,
    }
    _save_raw(payload)


def extract_cookie_metadata(binary_data: bytes) -> dict:
    try:
        cookies = _parse_binarycookies(binary_data)
        for cookie in cookies:
            if cookie.get("name") == ".ROBLOSECURITY" and cookie.get("domain", "").endswith("roblox.com"):
                # Core Foundation time to Unix timestamp
                # Epoch difference (2001-01-01 - 1970-01-01) is 978307200 seconds
                cf_creation = cookie.get("creation", 0)
                cf_expires = cookie.get("expires", 0)
                
                cf_creation = cookie.get("creation", 0)
                cf_expires = cookie.get("expires", 0)
                
                # Check for valid timestamps (avoid 0.0)
                created_at = (cf_creation + 978307200) if cf_creation > 0 else None
                expires_at = (cf_expires + 978307200) if cf_expires > 0 else None
                
                return {
                    "created_at": created_at,
                    "expires_at": expires_at
                }
    except Exception:
        pass
    return {}


def add_account(name: str, token: str, binary_data: Optional[bytes] = None) -> Account:
    accounts, last_selected_id = load_accounts()
    
    metadata = {}
    if binary_data:
        metadata = extract_cookie_metadata(binary_data)
        
    new_account = Account(
        id=str(uuid.uuid4()), 
        name=name, 
        token=token.strip(),
        binary_data=binary_data,
        created_at=metadata.get("created_at"),
        expires_at=metadata.get("expires_at")
    )
    accounts.append(new_account)
    save_accounts(accounts, last_selected_id)
    return new_account


def export_accounts_to_json(path: Path) -> None:
    accounts, _ = load_accounts()
    export_data = []
    for acc in accounts:
        item = {
            "name": acc.name,
            "token": acc.token,
            "created_at": acc.created_at,
            "expires_at": acc.expires_at
        }
        if acc.binary_data:
            item["binary_data_b64"] = base64.b64encode(acc.binary_data).decode("utf-8")
        export_data.append(item)
    
    path.write_text(json.dumps(export_data, indent=2), encoding="utf-8")


def get_roblox_username(token: str) -> Optional[str]:
    import urllib.request
    try:
        url = "https://users.roblox.com/v1/users/authenticated"
        req = urllib.request.Request(url)
        req.add_header("Cookie", f".ROBLOSECURITY={token}")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.load(response)
            return data.get("name")
    except Exception:
        return None


def import_accounts_from_json(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return 0
            
        count = 0
        for item in data:
            if not item.get("token"):
                continue
                
            name = item.get("name", "Imported Account")
            token = item.get("token")
            binary_data = None
            if item.get("binary_data_b64"):
                try:
                    binary_data = base64.b64decode(item["binary_data_b64"])
                except Exception:
                    pass
            
            # Use add_account to handle ID generation, encryption logic, etc.
            # We pass binary_data directly, stats will be re-extracted
            add_account(name, token, binary_data)
            count += 1
        return count
    except Exception:
        return 0


def rename_account(account_id: str, new_name: str) -> None:
    accounts, last_selected_id = load_accounts()
    for acc in accounts:
        if acc.id == account_id:
            acc.name = new_name
            break
    save_accounts(accounts, last_selected_id)


def delete_account(account_id: str) -> None:
    accounts, last_selected_id = load_accounts()
    accounts = [acc for acc in accounts if acc.id != account_id]
    if last_selected_id == account_id:
        last_selected_id = None
    save_accounts(accounts, last_selected_id)


def set_last_selected_id(account_id: Optional[str]) -> None:
    accounts, _ = load_accounts()
    save_accounts(accounts, account_id)


def list_running_roblox_processes() -> List[str]:
    names = []
    target_names = {
        "robloxplayerbeta.exe",
        "robloxplayer.exe",
        "robloxstudio.exe",
        "robloxstudiobeta.exe",
        "robloxplayerbeta",
        "robloxplayer",
        "robloxstudio",
        "robloxstudiobeta",
    }
    if psutil is None:
        return names
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in target_names:
                names.append(proc.info.get("name") or "")
        except Exception:
            continue
    return names


def is_roblox_running() -> bool:
    if psutil is None:
        return False
    return len(list_running_roblox_processes()) > 0


def kill_roblox_processes() -> List[str]:
    killed = []
    if psutil is not None:
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name.startswith("roblox"):
                    proc.terminate()
                    killed.append(proc.info.get("name") or "")
            except Exception:
                continue
        if killed:
            def on_terminate(proc):
                pass
            
            procs_to_wait = []
            for p in psutil.process_iter(['name']):
                try:
                    if p.info['name'] and p.info['name'].lower().startswith("roblox"):
                        procs_to_wait.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
            _, alive = psutil.wait_procs(procs_to_wait, timeout=3, callback=on_terminate)
            for proc in alive:
                try:
                    proc.kill()
                except Exception:
                    continue
        return killed
    system = platform.system().lower()
    if system == "windows":
        subprocess.run(["taskkill", "/f", "/im", "RobloxPlayerBeta.exe"], capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "RobloxPlayer.exe"], capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "RobloxStudio.exe"], capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "RobloxStudioBeta.exe"], capture_output=True)
        return ["RobloxPlayerBeta.exe", "RobloxPlayer.exe", "RobloxStudio.exe", "RobloxStudioBeta.exe"]
    if system == "darwin":
        subprocess.run(["pkill", "-f", "RobloxPlayer"], capture_output=True)
        subprocess.run(["pkill", "-f", "RobloxStudio"], capture_output=True)
        return ["RobloxPlayer", "RobloxStudio"]
    return []


def _windows_set_registry_cookie(token: str) -> List[str]:
    updated = []
    try:
        import winreg
    except Exception:
        return updated
    paths = [
        r"Software\Roblox\RobloxStudioBrowser\roblox.com",
        r"Software\Roblox\RobloxPlayer\roblox.com",
        r"Software\Roblox\RobloxPlayerBeta\roblox.com",
        r"Software\Roblox\RobloxStudio\roblox.com",
    ]
    for path in paths:
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, ".ROBLOSECURITY", 0, winreg.REG_SZ, token)
            winreg.CloseKey(key)
            updated.append(path)
        except Exception:
            continue
    return updated


def _windows_get_registry_cookie() -> Optional[str]:
    try:
        import winreg
    except Exception:
        return None
    paths = [
        r"Software\Roblox\RobloxStudioBrowser\roblox.com",
        r"Software\Roblox\RobloxPlayer\roblox.com",
        r"Software\Roblox\RobloxPlayerBeta\roblox.com",
        r"Software\Roblox\RobloxStudio\roblox.com",
    ]
    for path in paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, ".ROBLOSECURITY")
            winreg.CloseKey(key)
            if value:
                return str(value)
        except Exception:
            continue
    return None


def _macos_absolute_time(dt: datetime) -> float:
    epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
    return (dt - epoch).total_seconds()


def _read_cstring(data: bytes, offset: int) -> str:
    end = data.find(b"\x00", offset)
    if end == -1:
        end = len(data)
    return data[offset:end].decode("utf-8", errors="ignore")


def _parse_binarycookies(data: bytes) -> List[dict]:
    import struct

    if len(data) < 8 or data[:4] != b"cook":
        return []
    num_pages = struct.unpack_from(">I", data, 4)[0]
    page_sizes = struct.unpack_from(">" + "I" * num_pages, data, 8)
    cookies = []
    cursor = 8 + 4 * num_pages
    for size in page_sizes:
        page = data[cursor : cursor + size]
        cursor += size
        if len(page) < 12:
            continue
        num_cookies = struct.unpack_from("<I", page, 4)[0]
        offsets = struct.unpack_from("<" + "I" * num_cookies, page, 8)
        for off in offsets:
            if off + 4 > len(page):
                continue
            cookie_size = struct.unpack_from("<I", page, off)[0]
            chunk = page[off : off + cookie_size]
            if len(chunk) < 56:
                continue
            # Cookie structure (macOS 2026 format):
            # 0-4: cookie size
            # 4-8: unknown
            # 8-12: flags
            # 12-16: unknown
            # 16-20: domain offset
            # 20-24: name offset
            # 24-28: path offset
            # 28-32: value offset
            # 32-40: expiration date (double - Core Foundation absolute time)
            # 40-48: creation date (double - Core Foundation absolute time)
            # 48-56: end of header, strings follow
            domain_off = struct.unpack_from("<I", chunk, 16)[0]
            name_off = struct.unpack_from("<I", chunk, 20)[0]
            path_off = struct.unpack_from("<I", chunk, 24)[0]
            value_off = struct.unpack_from("<I", chunk, 28)[0]
            creation = struct.unpack_from("<d", chunk, 32)[0]
            expires = struct.unpack_from("<d", chunk, 40)[0]
            flags = struct.unpack_from("<I", chunk, 8)[0]
            cookies.append(
                {
                    "domain": _read_cstring(chunk, domain_off),
                    "name": _read_cstring(chunk, name_off),
                    "path": _read_cstring(chunk, path_off),
                    "value": _read_cstring(chunk, value_off),
                    "expires": expires,
                    "creation": creation,
                    "flags": flags,
                }
            )
    return cookies


def _macos_get_cookie_from_binarycookies(path: Path) -> Optional[str]:
    try:
        data = path.read_bytes()
        cookies = _parse_binarycookies(data)
    except Exception:
        return None
    for cookie in cookies:
        if cookie.get("name") == ".ROBLOSECURITY" and cookie.get("domain", "").endswith("roblox.com"):
            value = cookie.get("value")
            if value:
                return value
    return None


def _macos_cookie_candidate_paths() -> List[Path]:
    return [
        Path.home() / "Library" / "HTTPStorages" / "com.roblox.RobloxPlayer.binarycookies",
        Path.home() / "Library" / "Cookies" / "Cookies.binarycookies",
        Path.home()
        / "Library"
        / "Containers"
        / "com.apple.Safari"
        / "Data"
        / "Library"
        / "Cookies"
        / "Cookies.binarycookies",
    ]


def _build_cookie(domain: str, name: str, path: str, value: str, expires: float, creation: float, flags: int) -> bytes:
    import struct

    domain_b = domain.encode("utf-8") + b"\x00"
    name_b = name.encode("utf-8") + b"\x00"
    path_b = path.encode("utf-8") + b"\x00"
    value_b = value.encode("utf-8") + b"\x00"
    # Cookie structure (macOS 2026 format):
    # 0-4: cookie size
    # 4-8: unknown (0)
    # 8-12: flags
    # 12-16: unknown (0)
    # 16-20: domain offset
    # 20-24: name offset
    # 24-28: path offset
    # 28-32: value offset
    # 32-40: expiration date (double)
    # 40-48: creation date (double)
    # 48-56: padding (8 bytes of zeros)
    # 56+: string data (domain, name, path, value)
    header_size = 56
    domain_off = header_size
    name_off = domain_off + len(domain_b)
    path_off = name_off + len(name_b)
    value_off = path_off + len(path_b)
    body = domain_b + name_b + path_b + value_b
    size = header_size + len(body)
    header = struct.pack(
        "<IIIIIIIIdd",
        size,           # 0-4: cookie size
        0,              # 4-8: unknown
        flags,          # 8-12: flags
        0,              # 12-16: unknown
        domain_off,     # 16-20: domain offset
        name_off,       # 20-24: name offset
        path_off,       # 24-28: path offset
        value_off,      # 28-32: value offset
        creation,       # 32-40: creation date
        expires,        # 40-48: expiration date
    )
    padding = b"\x00" * 8  # 48-56: padding
    return header + padding + body


def _write_binarycookies(path: Path, cookies: List[dict]) -> None:
    import struct

    cookie_blobs = [c for c in cookies if c.get("domain") and c.get("name")]
    if not cookie_blobs:
        return
    cookie_data = []
    for c in cookie_blobs:
        cookie_data.append(
            _build_cookie(
                c["domain"],
                c["name"],
                c.get("path", "/"),
                c["value"],
                c["expires"],
                c["creation"],
                c.get("flags", 0),
            )
        )
    num_cookies = len(cookie_data)
    page_header = struct.pack("<II", 256, num_cookies)
    offsets = []
    cursor = 8 + 4 * num_cookies
    for blob in cookie_data:
        offsets.append(cursor)
        cursor += len(blob)
    offsets_blob = struct.pack("<" + "I" * num_cookies, *offsets)
    page_footer = b"\x00" * 8
    page = page_header + offsets_blob + b"".join(cookie_data) + page_footer
    header = b"cook" + struct.pack(">I", 1) + struct.pack(">I", len(page))
    path.write_bytes(header + page)


def _macos_inject_cookie(token: str) -> dict:
    cookie_path = Path.home() / "Library" / "HTTPStorages" / "com.roblox.RobloxPlayer.binarycookies"
    if not cookie_path.exists():
        return {"status": "not_found", "path": str(cookie_path)}
    backup_path = cookie_path.with_suffix(".binarycookies.bak")
    try:
        if not backup_path.exists():
            backup_path.write_bytes(cookie_path.read_bytes())
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    expires = _macos_absolute_time(now + timedelta(days=365))
    creation = _macos_absolute_time(now)
    try:
        data = cookie_path.read_bytes()
        cookies = _parse_binarycookies(data)
    except Exception:
        cookies = []
    filtered = [
        c
        for c in cookies
        if not (
            c.get("name") == ".ROBLOSECURITY"
            and c.get("domain", "").endswith("roblox.com")
        )
    ]
    filtered.append(
        {
            "domain": ".roblox.com",
            "name": ".ROBLOSECURITY",
            "path": "/",
            "value": token,
            "expires": expires,
            "creation": creation,
            "flags": 5,
        }
    )
    try:
        _write_binarycookies(cookie_path, filtered)
        return {"status": "ok", "path": str(cookie_path)}
    except Exception as exc:
        return {"status": "error", "path": str(cookie_path), "error": str(exc)}


def try_android_inject_cookie(token: str) -> dict:
    return {
        "status": "unsupported",
        "requires_root": True,
        "details": "Injecting cookies into /data/data/com.roblox.client requires root on Android.",
    }


def _macos_restore_full_cookie(data: bytes) -> dict:
    cookie_path = Path.home() / "Library" / "HTTPStorages" / "com.roblox.RobloxPlayer.binarycookies"
    if not cookie_path.parent.exists():
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        
    backup_path = cookie_path.with_suffix(".binarycookies.bak")
    try:
        # Create backup if it doesn't exist or update it if we are injecting a fresh state
        if not backup_path.exists() and cookie_path.exists():
            backup_path.write_bytes(cookie_path.read_bytes())
    except Exception:
        pass
        
    try:
        cookie_path.write_bytes(data)
        return {"status": "ok", "path": str(cookie_path), "method": "full_file_swap"}
    except Exception as exc:
        return {"status": "error", "path": str(cookie_path), "error": str(exc)}


def inject_cookie(token: str, binary_data: Optional[bytes] = None) -> dict:
    system = platform.system().lower()
    if system == "windows":
        updated = _windows_set_registry_cookie(token)
        return {"status": "ok" if updated else "error", "updated": updated}
    if system == "darwin":
        if binary_data:
            return _macos_restore_full_cookie(binary_data)
        return _macos_inject_cookie(token)
    return {"status": "unsupported", "details": "Cookie injection not implemented for this OS."}


def get_full_cookie_file_content() -> dict:
    system = platform.system().lower()
    if system == "darwin":
        path = Path.home() / "Library" / "HTTPStorages" / "com.roblox.RobloxPlayer.binarycookies"
        if not path.exists():
            return {"status": "not_found", "path": str(path)}
        try:
            data = path.read_bytes()
            # Also try to parse out the token for the legacy token field
            token = _macos_get_cookie_from_binarycookies(path) or ""
            return {"status": "ok", "data": data, "token": token, "path": str(path)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
            
    # Fallback/todo for Windows full file support if needed
    return get_existing_cookie()


def get_existing_cookie() -> dict:
    system = platform.system().lower()
    if system == "windows":
        token = _windows_get_registry_cookie()
        if token:
            return {"status": "ok", "token": token}
        return {"status": "not_found"}
    if system == "darwin":
        checked = []
        for cookie_path in _macos_cookie_candidate_paths():
            checked.append(str(cookie_path))
            if not cookie_path.exists():
                continue
            token = _macos_get_cookie_from_binarycookies(cookie_path)
            if token:
                return {"status": "ok", "token": token, "path": str(cookie_path)}
        return {"status": "not_found", "paths": checked}
    return {"status": "unsupported", "details": "Cookie lookup not implemented for this OS."}


def launch_roblox() -> dict:
    system = platform.system().lower()
    if system == "windows":
        try:
            os.startfile("roblox-player:")
            return {"status": "ok", "method": "protocol"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
    if system == "darwin":
        for app in ["Roblox", "RobloxPlayer", "RobloxStudio"]:
            result = subprocess.run(["open", "-a", app], capture_output=True)
            if result.returncode == 0:
                return {"status": "ok", "method": "open", "app": app}
        result = subprocess.run(["open", "roblox-player:"], capture_output=True)
        return {"status": "ok" if result.returncode == 0 else "error"}
    return {"status": "unsupported", "details": "Launch not implemented for this OS."}


def switch_account(account_id: str) -> dict:
    accounts, _ = load_accounts()
    target = next((acc for acc in accounts if acc.id == account_id), None)
    if not target:
        return {"status": "error", "error": "Account not found"}
    killed = kill_roblox_processes()
    inject_result = inject_cookie(target.token, target.binary_data)
    launch_result = launch_roblox()
    set_last_selected_id(account_id)
    return {
        "status": "ok",
        "killed": killed,
        "inject": inject_result,
        "launch": launch_result,
    }


def load_account_cookie(account_id: str) -> dict:
    """Inject the account cookie without launching Roblox."""
    accounts, _ = load_accounts()
    target = next((acc for acc in accounts if acc.id == account_id), None)
    if not target:
        return {"status": "error", "error": "Account not found"}
    inject_result = inject_cookie(target.token, target.binary_data)
    set_last_selected_id(account_id)
    return {
        "status": inject_result.get("status", "error"),
        "inject": inject_result,
        "account_name": target.name,
    }


def _macos_clear_cookie() -> dict:
    """Remove .ROBLOSECURITY from the Roblox binarycookies file."""
    cookie_path = Path.home() / "Library" / "HTTPStorages" / "com.roblox.RobloxPlayer.binarycookies"
    if not cookie_path.exists():
        return {"status": "not_found", "path": str(cookie_path)}
    try:
        data = cookie_path.read_bytes()
        cookies = _parse_binarycookies(data)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    # Filter out .ROBLOSECURITY cookies
    filtered = [
        c
        for c in cookies
        if not (
            c.get("name") == ".ROBLOSECURITY"
            and c.get("domain", "").endswith("roblox.com")
        )
    ]
    if len(filtered) == len(cookies):
        return {"status": "not_found", "message": "No .ROBLOSECURITY cookie found to clear"}
    try:
        _write_binarycookies(cookie_path, filtered)
        return {"status": "ok", "path": str(cookie_path), "removed": len(cookies) - len(filtered)}
    except Exception as exc:
        return {"status": "error", "path": str(cookie_path), "error": str(exc)}


def _windows_clear_cookie() -> dict:
    """Remove .ROBLOSECURITY from Windows registry."""
    try:
        import winreg
    except Exception:
        return {"status": "error", "error": "winreg not available"}
    paths = [
        r"Software\Roblox\RobloxStudioBrowser\roblox.com",
        r"Software\Roblox\RobloxPlayer\roblox.com",
        r"Software\Roblox\RobloxPlayerBeta\roblox.com",
        r"Software\Roblox\RobloxStudio\roblox.com",
    ]
    cleared = []
    for path in paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, ".ROBLOSECURITY")
            winreg.CloseKey(key)
            cleared.append(path)
        except Exception:
            continue
    if cleared:
        return {"status": "ok", "cleared": cleared}
    return {"status": "not_found", "message": "No .ROBLOSECURITY cookie found to clear"}


def clear_cookie() -> dict:
    """Clear the current .ROBLOSECURITY cookie from the system."""
    system = platform.system().lower()
    if system == "windows":
        return _windows_clear_cookie()
    if system == "darwin":
        return _macos_clear_cookie()
    return {"status": "unsupported", "details": "Cookie clearing not implemented for this OS."}
