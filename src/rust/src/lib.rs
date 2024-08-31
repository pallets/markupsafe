use pyo3::prelude::*;
use pyo3::{types::PyString, PyResult, Python};

static NEEDS_SANITIZE: [bool; 256] = {
    let mut needs_sanitize = [false; 256];
    needs_sanitize[b'"' as usize] = true;
    needs_sanitize[b'&' as usize] = true;
    needs_sanitize[b'\'' as usize] = true;
    needs_sanitize[b'<' as usize] = true;
    needs_sanitize[b'>' as usize] = true;
    needs_sanitize
};

pub fn needs_sanitize(bytes: &[u8]) -> Option<usize> {
    let chunks = bytes.chunks_exact(4);
    let rest = chunks.remainder();

    for (i, chunk) in chunks.enumerate() {
        let a = NEEDS_SANITIZE[chunk[0] as usize];
        let b = NEEDS_SANITIZE[chunk[1] as usize];
        let c = NEEDS_SANITIZE[chunk[2] as usize];
        let d = NEEDS_SANITIZE[chunk[3] as usize];
        if a | b | c | d {
            return Some(i * 4);
        }
    }

    for (i, &b) in rest.iter().enumerate() {
        if NEEDS_SANITIZE[b as usize] {
            return Some(((bytes.len() / 4) * 4) + i);
        }
    }

    None
}

static SANITIZE_INDEX: [i8; 256] = {
    let mut sanitize_index = [-1; 256];
    sanitize_index[b'"' as usize] = 0;
    sanitize_index[b'&' as usize] = 1;
    sanitize_index[b'\'' as usize] = 2;
    sanitize_index[b'<' as usize] = 3;
    sanitize_index[b'>' as usize] = 4;
    sanitize_index
};

static SANITIZED_VALUE: [&str; 5] = ["&#34;", "&amp;", "&#39;", "&lt;", "&gt;"];

pub fn lut_replace(input: &str) -> Option<String> {
    let bytes = input.as_bytes();
    if let Some(mut idx) = needs_sanitize(bytes) {
        let mut out = String::with_capacity(input.len());
        let mut prev_idx = 0;
        for &b in bytes[idx..].iter() {
            let replace_idx = SANITIZE_INDEX[b as usize];
            if replace_idx >= 0 {
                if prev_idx < idx {
                    out.push_str(&input[prev_idx..idx]);
                }
                out.push_str(SANITIZED_VALUE[replace_idx as usize]);
                prev_idx = idx + 1;
            }
            idx += 1;
        }
        if prev_idx < idx {
            out.push_str(&input[prev_idx..idx]);
        }
        Some(out)
    } else {
        None
    }
}

#[pyfunction]
pub fn _escape_inner<'py>(
    py: Python<'py>,
    s: Bound<'py, PyString>,
) -> PyResult<Bound<'py, PyString>> {
    if let Some(out) = lut_replace(s.to_str()?) {
        Ok(PyString::new_bound(py, out.as_str()))
    } else {
        Ok(s)
    }
}

#[pymodule]
#[pyo3(name = "_rust_speedups")]
fn speedups<'py>(_py: Python<'py>, m: &Bound<'py, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(_escape_inner, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use crate::lut_replace;

    #[test]
    fn empty() {
        let inp = "";
        assert!(lut_replace(inp).is_none());
    }

    #[test]
    fn no_change_test() {
        let inp = "abcdefgh";
        assert!(lut_replace(inp).is_none());
    }

    #[test]
    fn middle() {
        assert_eq!(
            "abcd&amp;&gt;&lt;&#39;&#34;efgh",
            lut_replace("abcd&><'\"efgh").unwrap()
        );
    }

    #[test]
    fn begin() {
        assert_eq!(
            "&amp;&gt;&lt;&#39;&#34;efgh",
            lut_replace("&><'\"efgh").unwrap()
        );
    }

    #[test]
    fn end() {
        assert_eq!(
            "abcd&amp;&gt;&lt;&#39;&#34;",
            lut_replace("abcd&><'\"").unwrap()
        );
    }

    #[test]
    fn no_change_large() {
        let inp = "abcdefgh".repeat(1024);
        assert!(lut_replace(inp.as_str()).is_none());
    }

    #[test]
    fn middle_large() {
        assert_eq!(
            "abcd&amp;&gt;&lt;&#39;&#34;efgh".repeat(1024).as_str(),
            lut_replace("abcd&><'\"efgh".repeat(1024).as_str()).unwrap()
        );
    }

    #[test]
    fn begin_large() {
        assert_eq!(
            "&amp;&gt;&lt;&#39;&#34;efgh".repeat(1024).as_str(),
            lut_replace("&><'\"efgh".repeat(1024).as_str()).unwrap()
        );
    }

    #[test]
    fn end_large() {
        assert_eq!(
            "abcd&amp;&gt;&lt;&#39;&#34;".repeat(1024).as_str(),
            lut_replace("abcd&><'\"".repeat(1024).as_str()).unwrap()
        );
    }
}
