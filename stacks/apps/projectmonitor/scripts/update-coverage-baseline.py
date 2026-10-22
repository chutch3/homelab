#!/usr/bin/env python3
"""Record the fork's changed Ruby lines against the pinned upstream checkout."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

UPSTREAM_COMMIT = '2b85d1701007d832cbc4b49aa3c94cbacb076884'
upstream = Path(sys.argv[1]).resolve()
revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
if revision != UPSTREAM_COMMIT:
    raise SystemExit(f'Expected upstream {UPSTREAM_COMMIT}, got {revision}')
subprocess.run(['git', '-C', str(upstream), 'diff', '--exit-code', 'HEAD', '--', 'app', 'lib'], check=True)
app = Path(__file__).resolve().parent.parent / 'app'
original = {}
changes = {}
for folder in ['app', 'lib']:
    for path in (upstream / folder).rglob('*.rb'):
        original[path.relative_to(upstream).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
paths = [*app.glob('app/**/*.rb'), *app.glob('lib/**/*.rb'), app / 'config/settings_loader.rb', app / 'docker/wait-for-database.rb']
for path in sorted(paths):
    rel = path.relative_to(app).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if original.get(rel) == digest:
        continue
    old = upstream / rel
    old_lines = old.read_text().splitlines() if old.exists() else []
    new_lines = path.read_text().splitlines()
    lines = [i + 1 for tag, _, _, start, end in difflib.SequenceMatcher(None, old_lines, new_lines).get_opcodes()
             if tag in ('insert', 'replace') for i in range(start, end)]
    changes[rel] = {'sha256': digest, 'lines': lines}
output = {'upstream': UPSTREAM_COMMIT, 'original': original, 'changes': changes}
(app / 'script/compatibility-coverage.json').write_text(json.dumps(output, indent=2) + '\n')
print(f'Recorded changed lines in {len(changes)} files; run the full tests to validate coverage.')
