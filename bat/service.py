#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Privacy Browser - Service Manager
Cross-platform development mode starter/stopper for Wails application.

Usage:
    python service.py start    - Start  server
    python service.py stop     - Stop  server
    python service.py restart  - Restart  server
    python service.py status   - Check server status
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path


# ============================================================================
# Configuration
# ============================================================================
FRONTEND_PORT = 5218
PID_FILE_NAME = ".Privacy-Browser.pid"
LOG_FILES = [
    "tmp-npm-dev.err.log", "tmp-npm-dev.log",
    "tmp-wails-err.log", "tmp-wails-out.log",
    "tmp-wails2-err.log", "tmp-wails2-out.log",
    "tmp-wails3-err.log", "tmp-wails3-out.log",
    "tmp-wails.err", "wails-dev-capture.log",
    "wails-dev-run.log", "wails-dev-stderr.log",
    "wails-dev-stdout.log"
]


# ============================================================================
# Utility Functions
# ============================================================================

def get_script_dir():
    """Get the directory where this script is located."""
    return Path(__file__).parent


def get_project_root():
    """Get the project root directory (parent of script directory)."""
    return get_script_dir().parent


def get_pid_file():
    """Get the PID file path."""
    return get_script_dir() / PID_FILE_NAME


def is_windows():
    """Check if running on Windows."""
    return sys.platform == "win32"


def run_command(cmd, capture=True, **kwargs):
    """Run a shell command."""
    try:
        if capture:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="gbk" if is_windows() else "utf-8",
                errors="ignore",
                **kwargs
            )
            return result
        else:
            return subprocess.run(cmd, **kwargs)
    except Exception as e:
        return None


def kill_process(pid):
    """Kill a process by PID."""
    try:
        if is_windows():
            run_command(["taskkill", "/F", "/PID", str(pid)])
        else:
            os.kill(pid, signal.SIGKILL)
        return True
    except Exception:
        return False


def kill_process_tree(pid):
    """Kill a process and its children."""
    try:
        if is_windows():
            run_command(["taskkill", "/F", "/T", "/PID", str(pid)])
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except ProcessLookupError:
                os.kill(pid, signal.SIGKILL)
        return True
    except Exception:
        return kill_process(pid)


# ============================================================================
# Process Discovery
# ============================================================================

def find_processes_by_name(name):
    """Find processes by name."""
    pids = []
    try:
        if is_windows():
            result = run_command(
                ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH", "/FO", "CSV"]
            )
            if result and result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line and name.lower() in line.lower():
                        parts = [p.strip().strip('"') for p in line.split(",")]
                        if len(parts) >= 2 and parts[1].isdigit():
                            pids.append(int(parts[1]))
        else:
            result = run_command(["pgrep", "-f", name])
            if result and result.returncode == 0:
                for p in result.stdout.strip().split("\n"):
                    if p.strip().isdigit():
                        pids.append(int(p.strip()))
    except Exception:
        pass
    return pids


def find_wails_processes():
    """Find all Wails-related processes."""
    pids = []
    patterns = ["wails", "ant-chrome-dev", "ant-chrome"]
    for pattern in patterns:
        pids.extend(find_processes_by_name(f"{pattern}.exe" if is_windows() else pattern))
    return list(set(pids))


def find_vite_processes():
    """Find Vite/Node processes related to this project by checking port usage."""
    pids = []
    try:
        # Check if any process is listening on the frontend port
        port_pid = check_port(FRONTEND_PORT)
        if port_pid:
            pids.append(port_pid)
    except Exception:
        pass
    return pids


def check_port(port):
    """Check if a port is in use. Returns PID if in use, 0 otherwise."""
    try:
        if is_windows():
            result = run_command([
                "powershell", "-NoProfile", "-Command",
                f"(Get-NetTCPConnection -State Listen -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"
            ])
            if result and result.stdout.strip().isdigit():
                return int(result.stdout.strip())
        else:
            result = run_command(["lsof", "-i", f":{port}", "-t"])
            if result and result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return 0


# ============================================================================
# File Operations
# ============================================================================

def save_pid(pid):
    """Save PID to file."""
    pid_file = get_pid_file()
    try:
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Started by {os.environ.get('USERNAME', 'unknown')}\n")
            f.write(f"{pid}\n")
    except Exception as e:
        print(f"Warning: Could not save PID file: {e}")


def load_pid():
    """Load PID from file."""
    pid_file = get_pid_file()
    if pid_file.exists():
        try:
            with open(pid_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    pid_str = lines[-1].strip()
                    if pid_str.isdigit():
                        return int(pid_str)
        except Exception:
            pass
    return None


def remove_pid_file():
    """Remove PID file."""
    pid_file = get_pid_file()
    if pid_file.exists():
        try:
            pid_file.unlink()
        except Exception:
            pass


def cleanup_logs():
    """Clean up old log files."""
    script_dir = get_script_dir()
    for log_name in LOG_FILES:
        log_file = script_dir / log_name
        if log_file.exists():
            try:
                log_file.unlink()
            except Exception:
                pass


# ============================================================================
# Service Actions
# ============================================================================

def stop_service():
    """Stop the Privacy Browser server."""
    print("=" * 60)
    print("  Privacy Chrome - Stop  Server")
    print("=" * 60)
    print()

    killed = False
    killed_pids = set()

    # 1. Check and kill process occupying the frontend port (highest priority)
    port_pid = check_port(FRONTEND_PORT)
    if port_pid:
        print(f"Killing process occupying port {FRONTEND_PORT}: PID {port_pid}")
        if kill_process_tree(port_pid):
            killed = True
            killed_pids.add(port_pid)
            print(f"  Killed PID {port_pid}")
    else:
        print(f"Port {FRONTEND_PORT}: Port not bound")

    # 2. Try to stop from PID file
    saved_pid = load_pid()
    if saved_pid and saved_pid not in killed_pids:
        print(f"Stopping process from PID file: {saved_pid}")
        if kill_process_tree(saved_pid):
            killed = True
            killed_pids.add(saved_pid)
            print(f"  Killed PID {saved_pid}")
        remove_pid_file()

    # 3. Find and stop any remaining wails processes
    wails_pids = find_wails_processes()
    for pid in wails_pids:
        if pid not in killed_pids:
            print(f"Stopping wails process: {pid}")
            if kill_process_tree(pid):
                killed = True
                killed_pids.add(pid)
                print(f"  Killed PID {pid}")

    # 4. Clean up Vite/Node processes that might be related to  server
    vite_pids = find_vite_processes()
    for pid in vite_pids:
        if pid not in killed_pids:
            print(f"Killing Vite/Node PID: {pid}")
            if kill_process(pid):
                killed = True
                killed_pids.add(pid)

    print()
    if killed:
        print("[OK] Privacy Browser server stopped successfully.")
    else:
        print("[INFO] No running Privacy Browser server found.")

    print()
    return 0


def start_service():
    """Start the Privacy Browser server."""
    project_root = get_project_root()
    os.chdir(project_root)

    print("=" * 60)
    print("  Privacy Chrome - Dev Launcher")
    print("=" * 60)
    print()
    print(f"Current workdir: {project_root}")
    print()

    # Clean up old logs
    cleanup_logs()

    # Check for existing Wails processes
    existing_pids = find_wails_processes()
    if existing_pids:
        print()
        print("=" * 60)
        print("[WARNING] Wails Privacy Browser is already running!")
        print("=" * 60)
        print()
        print(f"Existing process PIDs: {existing_pids}")
        print()

        while True:
            choice = input("Do you want to kill it and restart? [Y/N]: ").strip().lower()
            if choice in ["y", "yes"]:
                print()
                print("Killing existing processes...")
                for pid in existing_pids:
                    kill_process_tree(pid)
                    print(f"  Killed PID {pid}")
                time.sleep(2)
                break
            elif choice in ["n", "no"]:
                print()
                print("Startup cancelled.")
                return 0
            else:
                print("Please enter Y or N")

    # Clean up stale processes
    print("Cleaning stale processes...")
    for pid in find_wails_processes():
        kill_process_tree(pid)
    time.sleep(1)
    print()

    # Check frontend port
    print("Checking port status...")
    port_pid = check_port(FRONTEND_PORT)
    if port_pid:
        print(f"[ERROR] Port {FRONTEND_PORT} is occupied. PID: {port_pid}")
        print()
        print("Please close the process using the occupied port and retry.")
        return 1
    else:
        print(f"[OK] Port {FRONTEND_PORT} is available.")
    print()

    # Check dependencies
    print("Checking dependencies...")
    go_sum = project_root / "go.sum"
    if not go_sum.exists():
        print("Installing Go dependencies...")
        run_command(["go", "mod", "download"], capture=False)
        run_command(["go", "mod", "tidy"], capture=False)

    node_modules = project_root / "frontend" / "node_modules"
    if not node_modules.exists():
        print("Installing frontend dependencies...")
        run_command(["npm", "install"], cwd=project_root / "frontend", capture=False)
    print()

    # Regenerate Wails bindings
    print("Regenerating Wails bindings...")
    dist_dir = project_root / "frontend" / "dist"
    temp_dist_created = False
    temp_placeholder_created = False

    if not dist_dir.exists():
        dist_dir.mkdir(parents=True)
        temp_dist_created = True

    placeholder = dist_dir / "__wails_placeholder__.txt"
    if not placeholder.exists():
        placeholder.write_text("placeholder")
        temp_placeholder_created = True

    result = run_command(["wails", "generate", "module"], capture=False)

    # Clean up temp files
    if temp_placeholder_created and placeholder.exists():
        placeholder.unlink()
    if temp_dist_created and dist_dir.exists() and not any(dist_dir.iterdir()):
        dist_dir.rmdir()

    if result and result.returncode != 0:
        print("[ERROR] Failed to generate Wails bindings.")
        return 1

    # Copy bindings
    wailsjs = project_root / "frontend" / "wailsjs"
    src_wailsjs = project_root / "frontend" / "src" / "wailsjs"
    if wailsjs.exists():
        import shutil
        if src_wailsjs.exists():
            shutil.rmtree(src_wailsjs)
        shutil.copytree(wailsjs, src_wailsjs)

    if not src_wailsjs.exists():
        print("[ERROR] Wails bindings output folder not found.")
        return 1
    print()

    # Start server
    print("Starting Privacy Browser server...")
    print(f"Frontend URL: http://127.0.0.1:{FRONTEND_PORT}")
    print("Wails Privacy Browser endpoint: auto-select")
    print()

    # Save PID
    save_pid(os.getpid())

    try:
        result = run_command(["wails", "dev"], capture=False)
        exit_code = result.returncode if result else 1
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        remove_pid_file()

    if exit_code != 0:
        print()
        print(f"[ERROR] wails Privacy Browser exited with code {exit_code}.")

    return exit_code


def status_service():
    """Check service status."""
    print("=" * 60)
    print("  Privacy Chrome - Privacy Browser Server Status")
    print("=" * 60)
    print()

    # Check PID file
    saved_pid = load_pid()
    pid_file = get_pid_file()

    if saved_pid:
        print(f"PID file: {pid_file}")
        print(f"Saved PID: {saved_pid}")
    else:
        print(f"PID file: Not found")

    # Check port status (most reliable indicator)
    port_pid = check_port(FRONTEND_PORT)
    if port_pid:
        print(f"Port {FRONTEND_PORT}: In use by PID {port_pid}")
        print(f"Status: [RUNNING]")
    else:
        print(f"Port {FRONTEND_PORT}: Port not bound")
        print(f"Status: [NOT RUNNING]")

    # Show detected processes for debugging
    wails_pids = find_wails_processes()
    if wails_pids:
        print(f"Wails processes (detected): {wails_pids}")

    # Check for stale PID file
    if saved_pid and not port_pid:
        print()
        print("  Note: Stale PID file detected. Run 'stop' to clean up.")

    print()
    return 0


def restart_service():
    """Restart the  server."""
    print("Restarting  server...")
    print()
    stop_service()
    print()
    time.sleep(2)
    return start_service()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Privacy Browser Service Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python service.py start    - Start  server
    python service.py stop     - Stop  server
    python service.py restart  - Restart  server
    python service.py status   - Check server status
        """
    )
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status"],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "start":
        return start_service()
    elif args.action == "stop":
        return stop_service()
    elif args.action == "restart":
        return restart_service()
    elif args.action == "status":
        return status_service()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
