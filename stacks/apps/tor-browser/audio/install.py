"""Install the optional sidebar extension without replacing Kasm's frontend."""
from hashlib import sha256
from pathlib import Path
import re
import shutil
import sys


ASSETS = {
    'sidebar.js': 'src/sidebar.js',
    'jsmpeg.min.js': 'vendor/jsmpeg/jsmpeg.min.js',
    'LICENSE.jsmpeg': 'vendor/jsmpeg/LICENSE',
}

MARKER = '<!-- homelab-desktop-audio-v1 -->'
# Also replaces the original ?v=1 scripts when upgrading an existing installation.
BLOCK = re.compile(re.escape(MARKER) +
                   r'\s*<script defer src="/homelab-audio/jsmpeg.min.js\?v=[^"]+"></script>'
                   r'\s*<script defer src="/homelab-audio/sidebar.js\?v=[^"]+"></script>\s*')


def install(source, webroot):
    pages = [webroot / name for name in ('index.html', 'vnc.html')]
    originals = {page: page.read_text() for page in pages}
    for page, text in originals.items():
        if any(token not in text for token in ('noVNC_disconnect_button', 'noVNC_button_div', '</body>')):
            raise RuntimeError(f'Unsupported Kasm sidebar: {page}')
        if MARKER in text and not BLOCK.search(text):
            raise RuntimeError(f'Unrecognized audio script block: {page}')
    assets = {name: (source / relative).read_bytes() for name, relative in ASSETS.items()}
    addition = MARKER + '\n' + ''.join(
        f'<script defer src="/homelab-audio/{name}?v={sha256(assets[name]).hexdigest()[:16]}"></script>\n'
        for name in ('jsmpeg.min.js', 'sidebar.js'))
    # Prepare every asset before injecting HTML. A failed copy leaves fresh pages alone.
    target = webroot / 'homelab-audio'
    target.mkdir(exist_ok=True)
    for name in assets:
        shutil.copyfile(source / ASSETS[name], target / name)
        (target / name).chmod(0o644)
    for page, text in originals.items():
        updated = BLOCK.sub('', text).replace('</body>', addition + '</body>', 1)
        if updated != text:
            page.write_text(updated)
    print('[PRESTART] Kasm sidebar audio installed.')


if __name__ == '__main__':
    install(Path(__file__).parent, Path(sys.argv[1] if len(sys.argv) > 1 else '/usr/share/kasmvnc/www'))
