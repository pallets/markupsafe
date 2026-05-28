#!/usr/bin/env python3
# /// scripts
# dependencies = [
#     ".",
#     "pyperf",
# ]
# ///
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as d:
    outfiles = []
    for mod in "native", "speedups":
        print(mod, end="", flush=True)
        outname = f"{d}/{mod}.json"
        outfiles.append(outname)
        for name, s in (
            ("short escape", '"<strong>Hello, World!</strong>"'),
            ("long escape", '"<strong>Hello, World!</strong>" * 1000'),
            ("short plain", '"Hello, World!"'),
            ("long plain", '"Hello, World!" * 1000'),
            (
                "long prefix",
                '"Hello, World!" * 1000 + "<strong>Hello, World!</strong>"',
            ),
            ("long suffix", '"<strong>Hello, World!</strong>" + "x" * 100_000'),
        ):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pyperf",
                    "timeit",
                    "--quiet",
                    "--name",
                    name,
                    "--append",
                    outname,
                    "-s",
                    (
                        "import markupsafe\n"
                        f"from markupsafe._{mod} import _escape_inner\n"
                        "markupsafe._escape_inner = _escape_inner\n"
                        "from markupsafe import escape\n"
                        f"s = {s}"
                    ),
                    "escape(s)",
                ],
                stdout=subprocess.DEVNULL,
            )
            print(".", end="", flush=True)
        print()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pyperf",
            "compare_to",
            "--table",
            *outfiles,
        ]
    )
