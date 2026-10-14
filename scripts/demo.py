"""One-command demo: start a manager and three disks, then open an interactive user shell.

Usage: python scripts/demo.py
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = [sys.executable, os.path.join(ROOT, "run.py")]
MANAGER_PORT = 1500
DISK_PORTS = {"disk1": (1601, 1602), "disk2": (1603, 1604), "disk3": (1605, 1606)}


def main():
    procs = []
    try:
        procs.append(subprocess.Popen(RUN + ["manager", str(MANAGER_PORT)], cwd=ROOT))
        time.sleep(1)
        for name, (m_port, c_port) in DISK_PORTS.items():
            procs.append(subprocess.Popen(
                RUN + ["disk", name, "127.0.0.1", str(MANAGER_PORT), str(m_port), str(c_port)], cwd=ROOT))
        time.sleep(1)
        print("\nManager and 3 disks are running. Try:")
        print("  configure-dss dss1 3 128")
        print("  copy in-flanders.txt 0 alice")
        print("  ls")
        print("  disk-failure dss1\n")
        subprocess.call(RUN + ["user", "alice", "127.0.0.1", str(MANAGER_PORT), "1701", "1702"], cwd=ROOT)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in procs:
            proc.terminate()


if __name__ == "__main__":
    main()
