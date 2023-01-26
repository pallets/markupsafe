use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyLong, PyString};
use pyo3::{intern, PyTypeInfo};

fn escape_str(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('>', "&gt;")
        .replace('<', "&lt;")
        .replace('\'', "&#39;")
        .replace('"', "&#34;")
}

#[pyfunction]
fn escape<'p>(py: Python<'p>, s: &'p PyAny) -> PyResult<&'p PyAny> {
    let cls = PyModule::import(py, "markupsafe")?.getattr("Markup")?;

    if PyLong::is_exact_type_of(s) || PyFloat::is_exact_type_of(s) || PyBool::is_exact_type_of(s) {
        cls.call1((s,))
    } else if s.hasattr(intern!(py, "__html__"))? {
        cls.call1((s.call_method0("__html__")?,))
    } else if PyString::is_exact_type_of(s) {
        cls.call1((escape_str(s.extract()?),))
    } else {
        cls.call1((escape_str(s.str()?.extract()?),))
    }
}

#[pyfunction]
fn escape_silent<'p>(py: Python<'p>, s: &'p PyAny) -> PyResult<&'p PyAny> {
    if s.is_none() {
        let cls = PyModule::import(py, "markupsafe")?.getattr("Markup")?;
        cls.call0()
    } else {
        escape(py, s)
    }
}

#[pyfunction]
fn soft_str(s: &PyAny) -> &PyAny {
    if PyString::is_type_of(s) {
        s
    } else {
        s.str().unwrap()
    }
}

#[pymodule]
#[pyo3(name = "_rust_speedups")]
fn speedups(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(escape, m)?)?;
    m.add_function(wrap_pyfunction!(escape_silent, m)?)?;
    m.add_function(wrap_pyfunction!(soft_str, m)?)?;
    Ok(())
}
