import subprocess
import sys

for name, s in (
    ("short escape", '"<strong>Hello, World!</strong>"'),
    ("long escape", '"Hello, World!" * 1000'),
    ("short plain", '"Hello, World!"'),
    ("long plain", '"Hello, World!" * 1000'),
    ("long suffix", '"<strong>Hello, World!</strong>" + "x" * 100_000'),
):
    for mod in "native", "speedups":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pyperf",
                "timeit",
                "--append",
                "bench-results.json",
                "--name",
                f"{name} {mod}",
                "-s",
                f"from markupsafe._{mod} import escape\ns = {s}",
                "escape(s)",
            ]
        )
