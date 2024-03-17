import pyperf

runner = pyperf.Runner()

name = "native"
runner.timeit(
    f"escape_inner {name}",
    setup=f"from markupsafe._{name} import escape_inner",
    stmt='escape_inner("<strong>Hello, World!</strong>" * 1024)',
)
name = "rust_speedups"
runner.timeit(
    f"escape_inner_naive {name}",
    setup=f"from markupsafe._{name} import escape_inner_naive",
    stmt='escape_inner_naive("<strong>Hello, World!</strong>" * 1024)',
)
runner.timeit(
    f"escape_inner {name}",
    setup=f"from markupsafe._{name} import escape_inner",
    stmt='escape_inner("<strong>Hello, World!</strong>" * 1024)',
)
