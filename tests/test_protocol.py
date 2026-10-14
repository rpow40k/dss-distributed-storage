"""Loopback integration tests: a real manager process thread driven over UDP."""
import json
import os
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.manager as manager_module
from src.manager import ManagerProcess

MANAGER_PORT = 1990
HOST = "127.0.0.1"


def send(command, params=None):
    """Send one JSON command to the manager and return the decoded reply."""
    message = {
        "command": command,
        "params": params or {},
        "timestamp": "test",
        "message_id": f"test_{time.time_ns()}",
    }
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3.0)
        sock.sendto(json.dumps(message).encode("utf-8"), (HOST, MANAGER_PORT))
        data, _ = sock.recvfrom(65535)
    return json.loads(data.decode("utf-8"))


def register_disk(name, m_port, c_port):
    return send("register-disk", {
        "disk_name": name, "ip_address": HOST, "m_port": m_port, "c_port": c_port,
    })


class ManagerProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manager_module.SOCKET_TIMEOUT = 0.2  # so stop() returns quickly
        cls.manager = ManagerProcess(MANAGER_PORT)
        cls.thread = threading.Thread(target=cls.manager.start, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.manager.running = False
        cls.thread.join(timeout=2)

    def test_1_unknown_command_fails(self):
        self.assertEqual(send("bogus")["status"], "FAILURE")

    def test_2_rejects_bad_names_and_ports(self):
        self.assertEqual(register_disk("bad name!", 1601, 1602)["status"], "FAILURE")
        out_of_range = register_disk("diskx", 80, 1602)
        self.assertEqual(out_of_range["status"], "FAILURE")
        self.assertIn("between 1500 and 1999", out_of_range["message"])
        same = register_disk("diskx", 1601, 1601)
        self.assertEqual(same["status"], "FAILURE")

    def test_3_register_disks_and_configure_dss(self):
        for i in range(3):
            reply = register_disk(f"disk{i}", 1610 + 2 * i, 1611 + 2 * i)
            self.assertEqual(reply["status"], "SUCCESS", reply)

        duplicate_port = register_disk("disk9", 1610, 1650)
        self.assertEqual(duplicate_port["status"], "FAILURE")
        self.assertIn("already used", duplicate_port["message"])

        self.assertEqual(send("configure-dss", {"dss_name": "dss1", "n": 2, "striping_unit": 128})["status"], "FAILURE")
        self.assertEqual(send("configure-dss", {"dss_name": "dss1", "n": 3, "striping_unit": 100})["status"], "FAILURE")
        self.assertEqual(send("configure-dss", {"dss_name": "dss1", "n": 4, "striping_unit": 128})["status"], "FAILURE")

        ok = send("configure-dss", {"dss_name": "dss1", "n": 3, "striping_unit": 128})
        self.assertEqual(ok["status"], "SUCCESS", ok)
        again = send("configure-dss", {"dss_name": "dss1", "n": 3, "striping_unit": 128})
        self.assertEqual(again["status"], "FAILURE")

    def test_4_ls_lists_dss(self):
        reply = send("ls")
        self.assertEqual(reply["status"], "SUCCESS", reply)


if __name__ == "__main__":
    unittest.main(verbosity=2)
