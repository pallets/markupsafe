use std::ops::{BitAnd, BitOr};
use std::str::from_utf8_unchecked;

use pyo3::prelude::*;
use pyo3::{
    types::{PyString, PyStringData},
    PyResult, Python,
};

/// A Rust implemented find and replace for the characters `<`, `>`, `&`, `"`, and `'`
/// into the sanitized strings `&lt;`, `&gt;`, `&amp;`, `#34;`, and `#39;` respectively

// Since speed was is a concern, I try to strike a balance between fast and readable, borrowing
// some lessons from simd-json. Namely I use vectorized and branchless-ish processing, but instead
// of using explicit vectorization, I let the compiler auto-vectorize the code for us, keeping the
// code readable, portable, and safe.
//
// To guarantee this optimization we need to help the compiler to recognize the patterns. We need to
// operate on 128-bit chunks whenever possible, and to do so generically because python could give
// us characters encoded as u8, u16, or u32.
// > By default, the i686 and x86_64 Rust targets enable sse and sse2 (128-bit vector extensions)
// https://github.com/rust-lang/portable-simd/blob/master/beginners-guide.md
//
// To enable this, I used some intermediate Rust features, so I'll include comments labelled
// RUST_INTRO where they're relevant, but they include:
//
// - const generics - similar to generics, but for compile-time constants. This means that
//                    different calls to the same function can work with different numbers in their
//                    types.
// - traits         - like an interface in java. Defines the behavior we might want out of a
//                    generic type that can be implemented by many different concrete types.
// - macro_rules    - used to create syntax sugar for some repetative code.
// - iterators      - a lazy data stream used mostly to make for-in loops look nice. They have a
//                    similar interface to java's stream api, but compile to optimized loops.

// A trait that describes anything we might want to do with bits so we can generically work with
// u8, u16, or u32
// RUST_INTRO: The traits after the colon are trait-bounds. Any types implementing Bits must already
// implement these other traits. These are all handled by the standard library.
trait Bits: Copy + Eq + BitAnd<Output = Self> + BitOr<Output = Self> + Into<u64> + From<u8> {
    fn ones() -> Self;
    fn zeroes() -> Self;
    fn as_u8(self) -> u8;
}

// RUST_INTRO: We can implement our trait on types that already exist in the standard library
impl Bits for u8 {
    fn ones() -> Self {
        Self::MAX
    }

    fn zeroes() -> Self {
        0
    }

    fn as_u8(self) -> u8 {
        self
    }
}

impl Bits for u16 {
    fn ones() -> Self {
        Self::MAX
    }

    fn zeroes() -> Self {
        0
    }

    fn as_u8(self) -> u8 {
        self as u8
    }
}

impl Bits for u32 {
    fn ones() -> Self {
        Self::MAX
    }

    fn zeroes() -> Self {
        0
    }

    fn as_u8(self) -> u8 {
        self as u8
    }
}

// auto-vectorized OR
// RUST_INTRO: the `<const N: usize` is a const generic. It tells the compiler that we know the
// exact size of ax, which is the same as bx, and the result will be the same size, but don't
// commit to an actual size in the function definition. This way we can create a 128-bit vector
// out of [u8; 16], [u16; 8], or [u32; 4] and the compiler will still know to auto-vectorize it.
// RUST_INTRO: `.iter()` and `.zip()` and later `.map()` and `.reduce()` are iterators. `.zip()`
// merges 2 streams into one with a tuple (a, b) for each item. We can do this twice to get a
// tuple containing a tuple ((a, b), r).
#[inline(always)]
fn v_or<const N: usize, T: Bits>(ax: [T; N], bx: [T; N]) -> [T; N] {
    let mut result = [T::zeroes(); N];
    for ((&a, &b), r) in ax.iter().zip(bx.iter()).zip(result.iter_mut()) {
        *r = a | b;
    }
    result
}

const MASK_BITS: [u8; 16] = [
    1,
    1 << 1,
    1 << 2,
    1 << 3,
    1 << 4,
    1 << 5,
    1 << 6,
    1 << 7,
    1,
    1 << 1,
    1 << 2,
    1 << 3,
    1 << 4,
    1 << 5,
    1 << 6,
    1 << 7,
];

// I attempted to autovectorize to pmovmskb, but since I can't get it to
// recognize it, I'll just take advantage of v_eq setting all bits to 1.
//
// converts chunks of ones created by v_eq into a bitmask with 1s where the
// matching characters were. e.g.
// input     = "xx<x"
// v_eq "<"  = 0x00 00 FF 00
// v_bitmask = 0b0010
// technically the last line has the bits reversed. I wrote it this way to
// show the relationship between the matched character and the bits.
#[inline(always)]
fn v_bitmask<const N: usize, T: Bits>(ax: [T; N]) -> u64 {
    let mut masked = [0u8; N];
    for ((a, m), r) in ax.iter().zip(MASK_BITS.iter()).zip(masked.iter_mut()) {
        *r = a.as_u8() & m
    }
    let mut result = 0u64;
    for (i, &m) in masked.iter().enumerate() {
        result |= (m as u64) << ((i / 8) * 8);
    }
    result
}

// auto-vectorized equal. designed to compile into the instruction pcmpeqb
#[inline(always)]
fn v_eq<const N: usize, T: Bits>(ax: &[T], bx: [T; N]) -> [T; N] {
    let mut result = [T::zeroes(); N];
    for ((&a, &b), r) in ax.iter().zip(bx.iter()).zip(result.iter_mut()) {
        *r = if a == b { T::ones() } else { T::zeroes() };
    }
    result
}

#[inline(always)]
fn mask<const N: usize, const M: usize, T: Bits>(input: &[T], splats: [[T; N]; M]) -> u64 {
    let mut result = 0u64;
    // split into 128-bit chunks to vectorize inside the loop
    for (i, lane) in input.chunks_exact(N).enumerate() {
        result |= v_bitmask(
            splats
                .iter()
                .fold([T::zeroes(); N], |acc, &splat| v_or(acc, v_eq(lane, splat))),
        ) << (i * N);
    }
    result
}

// a splat is an array containing the same element repeated.
// e.g. [u8; 16] splat of "<" is "<<<<<<<<<<<<<<<<"
// a single call to mask might need many of those, so we construct them with a macro
// RUST_INTRO: `$items:expr` matches any input that looks like an expression. `$(...),+` means that
// the pattern inside is repeated one or more times, separated by commas
macro_rules! make_splats {
    ($($items:expr),+) => {
        [$([$items.into(); N],)+]
    };
}

macro_rules! is_equal_any {
    ($lhs:expr, $($rhs:literal)|+) => {
        $(($lhs == $rhs.into()))|+
    };
}

// Tying everything together, we calculate the delta between the input size and the output.
// the algorithm: take chunks of 64 items at a time so mask() can create a u64 representing
// which items, if any, have characters that need replacing. We can then count how many of each
// character class is in the input and keep any indices if needed. Finally if the input doesn't
// neatly fit into 64 item chunks, we need a slow version to do the same to the remainder.
fn delta<const N: usize, T: Bits>(input: &[T], replacement_indices: &mut Vec<u32>) -> usize {
    // calls to mask() create a u64 mask representing 64 items
    let chunks = input.chunks_exact(64);
    let remainder = chunks.remainder();

    let mut delta = 0;
    for (i, chunk) in chunks.enumerate() {
        let delta_3_mask = mask::<N, 2, T>(chunk, make_splats!(b'<', b'>'));
        let delta_4_mask = mask::<N, 3, T>(chunk, make_splats!(b'"', b'\'', b'&'));
        // count_ones() is a single instruction on x86
        let delta_3 = delta_3_mask.count_ones();
        let delta_4 = delta_4_mask.count_ones();
        delta += (delta_3 * 3) + (delta_4 * 4);

        let mut all_mask = delta_3_mask | delta_4_mask;
        let mut count = delta_3 + delta_4;
        let idx = (i * 64) as u32;
        while count > 0 {
            replacement_indices.push(idx + all_mask.trailing_zeros());
            all_mask &= all_mask.wrapping_sub(1);
            count -= 1;
        }
    }

    let idx = ((input.len() / 64) * 64) as u32;
    for (i, &item) in remainder.iter().enumerate() {
        if is_equal_any!(item, b'<' | b'>') {
            delta += 3;
            replacement_indices.push(idx + i as u32);
        } else if is_equal_any!(item, b'"' | b'\'' | b'&') {
            delta += 4;
            replacement_indices.push(idx + i as u32);
        }
    }
    delta as usize
}

// very similar to delta(), but short-circuits because if there is anything to replace, we need to
// convert to utf-8 anyway to calculate delta and indices
fn no_change<const N: usize, T: Bits>(input: &[T]) -> bool {
    // calls to mask() create a u64 mask representing 64 items
    let chunks = input.chunks_exact(64);
    let remainder = chunks.remainder();

    for chunk in chunks {
        let any_mask = mask::<N, 5, T>(chunk, make_splats!(b'<', b'>', b'"', b'\'', b'&'));
        if any_mask != 0 {
            return false;
        }
    }

    for &item in remainder {
        if is_equal_any!(item, b'<' | b'>' | b'"' | b'\'' | b'&') {
            return false;
        }
    }
    true
}

// builds the sanitized output string. Copies the input bytes from sections that haven't changed
// and replaces the characters that need sanitizing.
fn build_replaced(
    RebuildArgs {
        delta,
        replacement_indices,
        input_str,
    }: RebuildArgs<'_>,
) -> String {
    // we could create the string without the size, but with_capacity means we
    // never need to re-allocate the backing memory
    let mut builder = String::with_capacity(input_str.len() + delta);
    let mut prev_idx = 0usize;
    for idx in replacement_indices {
        let idx = idx as usize;
        if prev_idx < idx {
            builder.push_str(&input_str[prev_idx..idx]);
        }
        builder.push_str(match &input_str[idx..idx + 1] {
            "<" => "&lt;",
            ">" => "&gt;",
            "\"" => "&#34;",
            "\'" => "&#39;",
            "&" => "&amp;",
            _ => unreachable!(""),
        });
        prev_idx = idx + 1;
    }
    if prev_idx != input_str.len() - 1 {
        builder.push_str(&input_str[prev_idx..input_str.len()]);
    }
    builder
}

struct RebuildArgs<'a> {
    delta: usize,
    replacement_indices: Vec<u32>,
    input_str: &'a str,
}

impl<'a> RebuildArgs<'a> {
    fn new(delta: usize, replacement_indices: Vec<u32>, input_str: &'a str) -> Self {
        RebuildArgs {
            delta,
            replacement_indices,
            input_str,
        }
    }
}

fn check_utf8(input: &[u8]) -> Option<RebuildArgs> {
    let mut replacement_indices = Vec::with_capacity(8);
    let delta = delta::<16, u8>(input, &mut replacement_indices);
    if delta == 0 {
        None
    } else {
        // SAFETY: The rest of the code assumes that python gives us valid utf-8, so to avoid
        // validation or copying, we will here too
        // https://docs.python.org/3.12//c-api/unicode.html
        let input_str = unsafe { from_utf8_unchecked(input) };
        Some(RebuildArgs::new(delta, replacement_indices, input_str))
    }
}

fn escape_utf8<'a>(py: Python<'a>, orig: &'a PyString, input: &[u8]) -> &'a PyString {
    check_utf8(input)
        .map(|rb| PyString::new(py, build_replaced(rb).as_str()))
        .unwrap_or(orig)
}

fn escape_other_format<'a, const N: usize, T: Bits>(
    py: Python<'a>,
    orig: &'a PyString,
    input: &[T],
) -> PyResult<&'a PyString> {
    // there's no safe way to construct a utf-16 or unicode string to pass back to python without
    // using the unsafe ffi bindings, so best case scenario we short circuit and pass the original
    // string back, otherwise just slow-path convert to utf-8 and process it that way since we'd
    // have to recompute the delta and indices anyway
    if no_change::<N, T>(input) {
        Ok(orig)
    } else {
        orig.to_str()
            .map(|utf8| escape_utf8(py, orig, utf8.as_bytes()))
    }
}

#[pyfunction]
pub fn escape_inner<'a>(py: Python<'a>, s: &'a PyString) -> PyResult<&'a PyString> {
    // SAFETY: from the py03 docs:
    // This function implementation relies on manually decoding a C bitfield.
    // In practice, this works well on common little-endian architectures such
    // as x86_64, where the bitfield has a common representation (even if it is
    // not part of the C spec). The PyO3 CI tests this API on x86_64 platforms.
    //
    // The C implementation already does this. Python strings can be represented
    // as u8, u16, or u32, and this avoids converting to utf-8 if it's not
    // necessary, meaning if a u16 or u32 string doesn't need any characters
    // replaced, we can short-circuit without doing any converting
    let data_res = unsafe { s.data() };
    match data_res {
        Ok(data) => match data {
            PyStringData::Ucs1(raw) => Ok(escape_utf8(py, s, raw)),
            PyStringData::Ucs2(raw) => escape_other_format::<8, u16>(py, s, raw),
            PyStringData::Ucs4(raw) => escape_other_format::<4, u32>(py, s, raw),
        },
        Err(e) => Err(e),
    }
}

fn delta_naive(input: &str, replacement_indices: &mut Vec<u32>) -> usize {
    let mut delta = 0;
    for (i, item) in input.chars().enumerate() {
        if is_equal_any!(item, b'<' | b'>') {
            delta += 3;
            replacement_indices.push(i as u32);
        } else if is_equal_any!(item, b'"' | b'\'' | b'&') {
            delta += 4;
            replacement_indices.push(i as u32);
        }
    }
    delta
}

fn check_utf8_naive(input: &str) -> Option<RebuildArgs> {
    let mut replacement_indices = Vec::with_capacity(8);
    let delta = delta_naive(input, &mut replacement_indices);
    if delta == 0 {
        None
    } else {
        Some(RebuildArgs::new(delta, replacement_indices, input))
    }
}

#[pyfunction]
pub fn escape_inner_naive<'a>(py: Python<'a>, s: &'a PyString) -> PyResult<&'a PyString> {
    let input = s.to_str()?;
    Ok(check_utf8_naive(input)
        .map(|rb| PyString::new(py, build_replaced(rb).as_str()))
        .unwrap_or(s))
}

#[pymodule]
#[pyo3(name = "_rust_speedups")]
fn speedups(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(escape_inner, m)?)?;
    m.add_function(wrap_pyfunction!(escape_inner_naive, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use crate::{build_replaced, check_utf8, no_change};

    #[test]
    fn empty() {
        let res = check_utf8("".as_bytes());
        assert!(res.is_none());
    }

    #[test]
    fn no_change_test() {
        let res = check_utf8("abcdefgh".as_bytes());
        assert!(res.is_none());
    }

    #[test]
    fn middle() {
        let res = build_replaced(check_utf8("abcd&><'\"efgh".as_bytes()).unwrap());
        assert_eq!("abcd&amp;&gt;&lt;&#39;&#34;efgh", res);
    }

    #[test]
    fn begin() {
        let res = build_replaced(check_utf8("&><'\"efgh".as_bytes()).unwrap());
        assert_eq!("&amp;&gt;&lt;&#39;&#34;efgh", res);
    }

    #[test]
    fn end() {
        let res = build_replaced(check_utf8("abcd&><'\"".as_bytes()).unwrap());
        assert_eq!("abcd&amp;&gt;&lt;&#39;&#34;", res);
    }

    #[test]
    fn no_change_large() {
        assert!(check_utf8("abcdefgh".repeat(1024).as_bytes()).is_none());
    }

    #[test]
    fn middle_large() {
        let res = build_replaced(check_utf8("abcd&><'\"efgh".repeat(1024).as_bytes()).unwrap());
        assert_eq!("abcd&amp;&gt;&lt;&#39;&#34;efgh".repeat(1024).as_str(), res);
    }

    #[test]
    fn begin_large() {
        let res = build_replaced(check_utf8("&><'\"efgh".repeat(1024).as_bytes()).unwrap());
        assert_eq!("&amp;&gt;&lt;&#39;&#34;efgh".repeat(1024).as_str(), res);
    }

    #[test]
    fn end_large() {
        let res = build_replaced(check_utf8("abcd&><'\"".repeat(1024).as_bytes()).unwrap());
        assert_eq!("abcd&amp;&gt;&lt;&#39;&#34;".repeat(1024).as_str(), res);
    }

    #[test]
    fn no_change_16() {
        let input = "こんにちはこんばんは".encode_utf16().collect::<Vec<_>>();
        assert!(no_change::<8, u16>(input.as_slice()));
    }

    #[test]
    fn middle_16() {
        let input = "こんにちは&><'\"こんばんは"
            .encode_utf16()
            .collect::<Vec<_>>();
        assert!(!no_change::<8, u16>(input.as_slice()));
        let utf8 = String::from_utf16(input.as_slice()).unwrap();
        let res = build_replaced(check_utf8(utf8.as_bytes()).unwrap());
        assert_eq!("こんにちは&amp;&gt;&lt;&#39;&#34;こんばんは", res);
    }

    #[test]
    fn begin_16() {
        let input = "&><'\"こんばんは".encode_utf16().collect::<Vec<_>>();
        assert!(!no_change::<8, u16>(input.as_slice()));
        let utf8 = String::from_utf16(input.as_slice()).unwrap();
        let res = build_replaced(check_utf8(utf8.as_bytes()).unwrap());
        assert_eq!("&amp;&gt;&lt;&#39;&#34;こんばんは", res);
    }

    #[test]
    fn end_16() {
        let input = "こんにちは&><'\"".encode_utf16().collect::<Vec<_>>();
        assert!(!no_change::<8, u16>(input.as_slice()));
        let utf8 = String::from_utf16(input.as_slice()).unwrap();
        let res = build_replaced(check_utf8(utf8.as_bytes()).unwrap());
        assert_eq!("こんにちは&amp;&gt;&lt;&#39;&#34;", res);
    }

    #[test]
    fn no_change_16_large() {
        let input = "こんにちはこんばんは"
            .repeat(1024)
            .encode_utf16()
            .collect::<Vec<_>>();
        assert!(no_change::<8, u16>(input.as_slice()));
    }

    #[test]
    fn middle_16_large() {
        let input = "こんにちは&><'\"こんばんは"
            .repeat(1024)
            .encode_utf16()
            .collect::<Vec<_>>();
        assert!(!no_change::<8, u16>(input.as_slice()));
        let utf8 = String::from_utf16(input.as_slice()).unwrap();
        let res = build_replaced(check_utf8(utf8.as_bytes()).unwrap());
        assert_eq!(
            "こんにちは&amp;&gt;&lt;&#39;&#34;こんばんは"
                .repeat(1024)
                .as_str(),
            res
        );
    }

    #[test]
    fn begin_16_large() {
        let input = "&><'\"こんばんは"
            .repeat(1024)
            .encode_utf16()
            .collect::<Vec<_>>();
        assert!(!no_change::<8, u16>(input.as_slice()));
        let utf8 = String::from_utf16(input.as_slice()).unwrap();
        let res = build_replaced(check_utf8(utf8.as_bytes()).unwrap());
        assert_eq!(
            "&amp;&gt;&lt;&#39;&#34;こんばんは".repeat(1024).as_str(),
            res
        );
    }

    #[test]
    fn end_16_large() {
        let input = "こんにちは&><'\""
            .repeat(1024)
            .encode_utf16()
            .collect::<Vec<_>>();
        assert!(!no_change::<8, u16>(input.as_slice()));
        let utf8 = String::from_utf16(input.as_slice()).unwrap();
        let res = build_replaced(check_utf8(utf8.as_bytes()).unwrap());
        assert_eq!(
            "こんにちは&amp;&gt;&lt;&#39;&#34;".repeat(1024).as_str(),
            res
        );
    }
}
