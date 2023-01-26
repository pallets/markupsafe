import pyperf

runner = pyperf.Runner()

for name in ("native", "rust_speedups"):  # ("native", "speedups", "rust_speedups"):
    runner.timeit(
        f"short escape {name}",
        setup=f"from markupsafe._{name} import escape",
        stmt='escape("<strong>Hello, World!</strong>")',
    )
    # runner.timeit(
    #     f"long escape {name}",
    #     setup=(
    #         f"from markupsafe._{name} import escape;\n"
    #         "s = \"Hello, World!\" * 1000"
    #     ),
    #     stmt="escape(s)",
    # )
    # runner.timeit(
    #     f"short empty {name}",
    #     setup=f"from markupsafe._{name} import escape",
    #     stmt="escape(\"Hello, World!\")",
    # )
    # runner.timeit(
    #     f"long empty {name}",
    #     setup=(
    #         f"from markupsafe._{name} import escape;\n"
    #         "s = \"<strong>Hello, World!</strong>\" * 1000"
    #     ),
    #     stmt="escape(s)",
    # )
    # runner.timeit(
    #     f"long suffix {name}",
    #     setup=(
    #         f"from markupsafe._{name} import escape;\n"
    #         "s = \"<strong>Hello, World!</strong>\" + \"x\" * 100000"
    #     ),
    #     stmt="escape(s)",
    # )
