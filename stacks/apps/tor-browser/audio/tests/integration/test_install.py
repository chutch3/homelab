from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import pytest

import install as installer

FIXTURE = Path(__file__).parents[1] / "fixtures/kasm-sidebar.html"


@pytest.fixture
def installation(tmp_path):
    source = tmp_path / "source"
    webroot = tmp_path / "www"
    webroot.mkdir()
    for name, relative in installer.ASSETS.items():
        asset = source / relative
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("test asset " + name)
    for name in ("index.html", "vnc.html"):
        (webroot / name).write_bytes(FIXTURE.read_bytes())
    return source, webroot


def test_repeated_install_is_idempotent(installation):
    source, web = installation
    installer.install(source, web)
    before = {p.name: p.read_bytes() for p in web.glob("*.html")}
    installer.install(source, web)
    assert before == {p.name: p.read_bytes() for p in web.glob("*.html")}
    for contents in before.values():
        assert contents.count(installer.MARKER.encode()) == 1
    for name, relative in installer.ASSETS.items():
        assert (web / "homelab-audio" / name).read_bytes() == (source / relative).read_bytes()
        assert (web / "homelab-audio" / name).stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize("asset", ["sidebar.js", "jsmpeg.min.js"])
def test_changed_asset_gets_new_cache_key(installation, asset):
    source, web = installation
    installer.install(source, web)
    old = (web / "index.html").read_text()
    (source / installer.ASSETS[asset]).write_bytes(b"updated code")
    installer.install(source, web)
    expected = sha256(b"updated code").hexdigest()[:16]
    for name in ("index.html", "vnc.html"):
        text = (web / name).read_text()
        assert text != old
        assert f"{asset}?v={expected}" in text
        assert text.count(installer.MARKER) == 1


def test_migrates_original_scripts(installation):
    source, web = installation
    original = FIXTURE.read_text()
    old = installer.MARKER + '<script defer src="/homelab-audio/jsmpeg.min.js?v=1"></script><script defer src="/homelab-audio/sidebar.js?v=1"></script>'
    (web / "index.html").write_text(original.replace("</body>", old + "</body>"))
    installer.install(source, web)
    text = (web / "index.html").read_text()
    assert '?v=1"' not in text
    assert text.count('src="/homelab-audio/') == 2
    # Existing Kasm scripts and UI are retained.
    assert "Disconnect desktop" in text
    assert "document.documentElement.classList.remove" in text


@pytest.mark.parametrize("missing", ["noVNC_disconnect_button", "noVNC_button_div", "</body>"])
def test_incompatible_html_does_not_modify_either_page(installation, missing):
    source, web = installation
    (web / "vnc.html").write_text(FIXTURE.read_text().replace(missing, "unsupported"))
    before = {p: p.read_bytes() for p in web.glob("*.html")}
    with pytest.raises(RuntimeError, match="Unsupported Kasm sidebar"):
        installer.install(source, web)
    assert before == {p: p.read_bytes() for p in before}
    assert not (web / "homelab-audio").exists()


def test_unknown_existing_patch_is_not_duplicated(installation):
    source, web = installation
    (web / "vnc.html").write_text(FIXTURE.read_text().replace("</body>", installer.MARKER + "</body>"))
    with pytest.raises(RuntimeError, match="Unrecognized audio script block"):
        installer.install(source, web)
    assert (web / "index.html").read_bytes() == FIXTURE.read_bytes()


@pytest.mark.parametrize("asset", list(installer.ASSETS))
def test_missing_asset_does_not_inject_scripts(installation, asset):
    source, web = installation
    (source / installer.ASSETS[asset]).unlink()
    with pytest.raises(FileNotFoundError):
        installer.install(source, web)
    for name in ("index.html", "vnc.html"):
        assert (web / name).read_bytes() == FIXTURE.read_bytes()


def test_copy_failure_does_not_inject_scripts(installation):
    source, web = installation
    with patch.object(installer.shutil, "copyfile", side_effect=PermissionError):
        with pytest.raises(PermissionError):
            installer.install(source, web)
    for name in ("index.html", "vnc.html"):
        assert (web / name).read_bytes() == FIXTURE.read_bytes()
