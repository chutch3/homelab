"""Exercise persistence using isolated homes and a shared config directory."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ENTRYPOINT = Path(os.environ.get(
    "DEVBOX_ENTRYPOINT", Path(__file__).resolve().parents[1] / "devbox-entrypoint.sh"
))


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.root / "config"
        self.config.mkdir()
        self.legacy = self.home / ".claude.json"
        self.persisted = self.config / ".claude.json"

    def start(self, home=None, command=("true",), check=True):
        return subprocess.run(
            ["bash", str(ENTRYPOINT), *command],
            env={**os.environ, "HOME": str(home or self.home),
                 "CLAUDE_CONFIG_DIR": str(self.config)},
            capture_output=True, text=True, check=check,
        )

    def test_fresh_start_and_replacement_preserve_state(self):
        self.start()
        self.assertTrue(self.legacy.is_symlink())
        self.assertFalse(self.persisted.exists())
        self.legacy.write_text('{"account":"saved"}')
        replacement = self.root / "replacement"
        replacement.mkdir()
        self.start(home=replacement)
        self.assertEqual((replacement / ".claude.json").read_text(), self.persisted.read_text())

    def test_migrates_legacy_file_and_is_idempotent(self):
        self.legacy.write_text('{"account":"legacy"}')
        self.start()
        self.start()
        self.assertTrue(self.legacy.is_symlink())
        self.assertEqual(self.persisted.read_text(), '{"account":"legacy"}')
        self.assertEqual(self.persisted.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.config.glob(".claude.json.pre-migration.*")), [])

    def test_conflict_keeps_shared_state_and_backs_up_legacy(self):
        self.persisted.write_text('{"account":"shared"}')
        self.legacy.write_text('{"account":"other"}')
        self.start()
        self.start()
        self.assertEqual(self.persisted.read_text(), '{"account":"shared"}')
        backups = list(self.config.glob(".claude.json.pre-migration.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), '{"account":"other"}')
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.legacy.is_symlink())

    def test_same_config_needs_no_backup(self):
        self.persisted.write_text('{}')
        self.legacy.write_text('{}')
        self.start()
        self.assertEqual(list(self.config.glob(".claude.json.pre-migration.*")), [])

    def test_unexpected_legacy_symlink_is_preserved(self):
        other = self.root / "other.json"
        other.write_text('{}')
        self.legacy.symlink_to(other)
        result = self.start(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.legacy.resolve(), other)
        self.assertEqual(other.read_text(), '{}')

    def test_invalid_config_types_do_not_launch_application(self):
        self.persisted.mkdir()
        marker = self.root / "launched"
        result = self.start(command=("touch", str(marker)), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())

    def test_concurrent_containers_keep_both_configs(self):
        other_home = self.root / "other-home"
        other_home.mkdir()
        self.legacy.write_text('{"account":"first"}')
        (other_home / ".claude.json").write_text('{"account":"second"}')
        processes = [subprocess.Popen(
            ["bash", str(ENTRYPOINT), "true"],
            env={**os.environ, "HOME": str(home), "CLAUDE_CONFIG_DIR": str(self.config)},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ) for home in (self.home, other_home)]
        for process in processes:
            _, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
        backups = list(self.config.glob(".claude.json.pre-migration.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual({self.persisted.read_text(), backups[0].read_text()},
                         {'{"account":"first"}', '{"account":"second"}'})

    def test_preserves_command_arguments_and_exit_status(self):
        result = self.start(command=("bash", "-c", 'printf "%s" "$1"; exit 7', "--", "two words"), check=False)
        self.assertEqual(result.stdout, "two words")
        self.assertEqual(result.returncode, 7)


if __name__ == "__main__":
    unittest.main()
