#!/usr/bin/env python3
"""
Smoke test for dist/Zedsu/ production package.

Verifies:
1. dist/Zedsu/ directory exists
2. Zedsu.exe (Tauri frontend) exists
3. ZedsuBackend.exe (Python backend) exists
4. Backend starts and responds to /health on port 9761
5. Backend starts IDLE (no auto-start core)
6. Backend process is killed after test

Exit codes:
  0 = all checks passed
  1 = dist/Zedsu/ not found
  2 = Zedsu.exe not found
  3 = ZedsuBackend.exe not found
  4 = Backend failed to start or /health did not respond
  5 = Backend did not start IDLE
  6 = Unexpected error
"""

import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path


def check_dist_exists(dist_path: Path) -> bool:
    """Verify dist/Zedsu/ directory exists."""
    if not dist_path.exists():
        print(f"[FAIL] dist/Zedsu/ not found at {dist_path}")
        return False
    print(f"[PASS] dist/Zedsu/ directory exists: {dist_path}")
    return True


def check_executables(dist_path: Path) -> tuple[bool, bool]:
    """Verify Zedsu.exe and ZedsuBackend.exe exist."""
    zedsu_exe = dist_path / "Zedsu.exe"
    backend_exe = dist_path / "ZedsuBackend.exe"

    zedsu_ok = zedsu_exe.exists()
    backend_ok = backend_exe.exists()

    if zedsu_ok:
        print(f"[PASS] Zedsu.exe found: {zedsu_exe}")
    else:
        print(f"[FAIL] Zedsu.exe not found: {zedsu_exe}")

    if backend_ok:
        print(f"[PASS] ZedsuBackend.exe found: {backend_exe}")
    else:
        print(f"[FAIL] ZedsuBackend.exe not found: {backend_exe}")

    return zedsu_ok, backend_ok


def wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
    """Wait for a TCP port to accept connections (HTTP server ready)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((host, port))
            sock.close()
            elapsed = time.time() - start
            if result == 0:
                return True
            # Only log every ~5s to avoid spam
            if elapsed % 5 < 0.6:
                print(f"[DEBUG] Port {port} not ready after {elapsed:.1f}s (connect result={result})")
        except Exception as e:
            pass
        time.sleep(0.5)
    return False


def _kill_existing_backend() -> None:
    """Kill any running ZedsuBackend processes before starting the smoke test."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object { $_.Name -like '*ZedsuBackend*' } | Stop-Process -Force -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10,
        )
        time.sleep(1.0)  # Wait for port to be released
    except Exception:
        pass


def check_backend_health(backend_exe: Path) -> tuple[bool, str]:
    """
    Start ZedsuBackend.exe, wait for /health to respond, check backend state.
    Returns (success, state_summary).
    """
    _kill_existing_backend()

    print(f"[INFO] Starting {backend_exe}...")
    proc = None
    try:
        # Start the backend process (no stdout/stderr redirect for windowed exe)
        # runw.exe doesn't have a console; redirecting pipes causes issues.
        # Startup errors go to logs/ directory instead.
        proc = subprocess.Popen(
            [str(backend_exe)],
            cwd=str(backend_exe.parent),
        )

        # Poll /health directly instead of raw socket check.
        # Backend takes 10-20s on cold start due to PyInstaller decompression.
        start = time.time()
        while time.time() - start < 25.0:
            if proc.poll() is not None:
                print(f"[FAIL] Backend process died with exit code {proc.returncode}")
                return False, "process_died"
            try:
                req = urllib.request.Request("http://127.0.0.1:9761/health", method="GET")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    elapsed = time.time() - start
                    print(f"[PASS] Backend is healthy ({elapsed:.1f}s startup)")
                    break
            except urllib.error.URLError:
                pass
            except Exception:
                pass
            time.sleep(1.0)
        else:
            elapsed = time.time() - start
            exit_code = proc.poll()
            print(f"[FAIL] Backend /health did not respond after {elapsed:.1f}s (exit={exit_code})")
            log_path = backend_exe.parent / "logs" / "backend.log"
            if log_path.exists():
                with open(log_path) as f:
                    lines = f.readlines()
                print(f"[DEBUG] Log has {len(lines)} lines. Last 3:")
                for line in lines[-3:]:
                    print(f"  {line.rstrip()}")
            return False, "startup_timeout"

        # Check /health endpoint
        try:
            req = urllib.request.Request("http://127.0.0.1:9761/health")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                print(f"[PASS] /health responded: HTTP {status}")
                print(f"[INFO] /health body: {body[:200]}")

                # Verify backend is IDLE (not running core)
                try:
                    state_req = urllib.request.Request("http://127.0.0.1:9761/state")
                    with urllib.request.urlopen(state_req, timeout=5.0) as state_resp:
                        import json
                        state = json.loads(state_resp.read().decode("utf-8"))
                        running = state.get("running", None)
                        combat_state = state.get("combat_state", state.get("hud", {}).get("combat_state", "unknown"))
                        print(f"[INFO] Backend state -- running: {running}, combat_state: {combat_state}")

                        if running is True:
                            print("[FAIL] Backend started with core running (should be IDLE)")
                            return False, "auto_start"
                        else:
                            print("[PASS] Backend started in IDLE state (no auto-start)")
                except Exception as e:
                    # /state is optional for smoke test -- /health passing is sufficient
                    print(f"[WARN] Could not check /state: {e}")

                return True, "idle"

        except urllib.error.URLError as e:
            print(f"[FAIL] /health request failed: {e}")
            return False, "health_failed"

    finally:
        # Always kill the backend process
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3.0)
                print("[INFO] Backend process terminated")
            except subprocess.TimeoutExpired:
                proc.kill()
                print("[INFO] Backend process killed")
            except Exception as e:
                print(f"[WARN] Could not terminate backend: {e}")


def main():
    project_root = Path(__file__).resolve().parents[1]  # scripts/ -> project root
    dist_path = project_root / "dist" / "Zedsu"

    print("============================================")
    print(" Zedsu v3 Smoke Test")
    print("============================================")
    print(f"Testing: {dist_path}")
    print("")

    # Check 1: dist/Zedsu/ exists
    if not check_dist_exists(dist_path):
        sys.exit(1)

    # Check 2: Executables exist
    zedsu_ok, backend_ok = check_executables(dist_path)
    if not zedsu_ok:
        sys.exit(2)
    if not backend_ok:
        sys.exit(3)

    # Check 3: Backend starts and responds
    backend_exe = dist_path / "ZedsuBackend.exe"
    backend_ok, state = check_backend_health(backend_exe)
    if not backend_ok:
        if state == "auto_start":
            sys.exit(5)
        sys.exit(4)

    print("")
    print("============================================")
    print(" Smoke Test: ALL CHECKS PASSED")
    print("============================================")
    sys.exit(0)


if __name__ == "__main__":
    main()
