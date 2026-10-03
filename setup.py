import os
import platform

from setuptools import Extension
from setuptools import setup
from setuptools_rust import RustExtension

if platform.python_implementation() not in {
    "PyPy",
    "Jython",
    "GraalVM",
}:
    local = os.environ.get("CIBUILDWHEEL", "0") != "1"
    setup(
        ext_modules=[
            Extension(
                "markupsafe._speedups", ["src/markupsafe/_speedups.c"], optional=local
            )
        ],
        rust_extensions=[
            RustExtension(
                "markupsafe._rust_speedups",
                "src/rust/Cargo.toml",
                optional=local,
                debug=False,
            )
        ],
    )
else:
    setup()
