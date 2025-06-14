import subprocess
import sys

for name, s in (
    ("short escape", '"<strong>Hello, World!</strong>"'),
    ("long escape", '"Hello, World!" * 1000'),
    ("short plain", '"Hello, World!"'),
    ("long plain", '"Hello, World!" * 1000'),
    ("long suffix", '"<strong>Hello, World!</strong>" + "x" * 100_000'),
):
    for mod in "native", "rust_speedups":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pyperf",
                "timeit",
                "--name",
                f"{name} {mod}",
                "-s",
                (
                    "import markupsafe\n"
                    f"from markupsafe._{mod} import _escape_inner\n"
                    "markupsafe._escape_inner = _escape_inner\n"
                    "from markupsafe import escape\n"
                    f"s = {s}"
                ),
                "escape(s)",
            ]
        )
