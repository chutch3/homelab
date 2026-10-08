from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_installer_cli_installs_real_assets(tmp_path):
    for name in ("index.html", "vnc.html"):
        shutil.copyfile(ROOT / "tests/fixtures/kasm-sidebar.html", tmp_path / name)
    result = subprocess.run([sys.executable, str(ROOT / "install.py"), str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Kasm sidebar audio installed" in result.stdout
    assert (tmp_path / "homelab-audio/jsmpeg.min.js").read_bytes() == (ROOT / "vendor/jsmpeg/jsmpeg.min.js").read_bytes()


def test_incompatible_webroot_cli_fails_without_modification(tmp_path):
    for name in ("index.html", "vnc.html"):
        (tmp_path / name).write_text("unsupported")
    result = subprocess.run([sys.executable, str(ROOT / "install.py"), str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "Unsupported Kasm sidebar" in result.stderr
    assert not (tmp_path / "homelab-audio").exists()
