"""What can go wrong in a workflow is said apart from how it is answered over HTTP: a service
raising one needs neither the web framework nor how a store's settings are worded."""

import subprocess
import sys


def test_the_errors_a_workflow_raises_come_without_the_web_or_settings_presentation() -> None:
    loaded = subprocess.run(
        [sys.executable, "-c",
         "import sys, disktracker.errors; print(*sorted(sys.modules), sep='\\n')"],
        capture_output=True, text=True, check=True,
    ).stdout.split()  # fmt: skip

    assert not [name for name in loaded if name == "fastapi" or name.startswith("fastapi.")]
    assert "disktracker.collection.settings" not in loaded
