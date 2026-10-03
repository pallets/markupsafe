#include <Python.h>
#include <stdint.h>

/*
 * Lookup tables for HTML escaping.
 *
 * The five special characters and their replacements:
 *   '"'  (34) -> "&#34;"  (len 5, delta +4)
 *   '&'  (38) -> "&amp;"  (len 5, delta +4)
 *   '\'' (39) -> "&#39;"  (len 5, delta +4)
 *   '<'  (60) -> "&lt;"   (len 4, delta +3)
 *   '>'  (62) -> "&gt;"   (len 4, delta +3)
 *
 * REPLACE_INDEX: 0 = no escaping needed, 1-5 = index into REPLACEMENT_STR.
 * All escape chars fit in a byte, so for UCS2/UCS4 we guard with c < 256.
 */
static const uint8_t REPLACE_INDEX[256] = {
	['"']  = 1,
	['&']  = 2,
	['\''] = 3,
	['<']  = 4,
	['>']  = 5,
};

static const char * const REPLACEMENT_STR[] = {
	NULL, "&#34;", "&amp;", "&#39;", "&lt;", "&gt;"
};

static const uint8_t REPLACEMENT_LEN[] = {0, 5, 5, 5, 4, 4};

/* Extra output characters needed per input character (0 if no escaping). */
static const uint8_t DELTA_TABLE[256] = {
	['"']  = 4,
	['&']  = 4,
	['\''] = 4,
	['<']  = 3,
	['>']  = 3,
};

/* Boolean: nonzero if this byte value requires HTML escaping. */
static const uint8_t NEEDS_ESCAPE[256] = {
	['"']  = 1,
	['&']  = 1,
	['\''] = 1,
	['<']  = 1,
	['>']  = 1,
};

/*
 * Count the total extra characters needed for escaping a UCS1 string.
 * Processes 4 bytes at a time: if none of the four need escaping, the
 * entire chunk is skipped with a single OR across four table lookups.
 * Falls back to per-byte delta lookup only for chunks containing a
 * special character. Returns 0 if no escaping is needed at all.
 */
static Py_ssize_t
count_delta_1(const Py_UCS1 *inp, Py_ssize_t len)
{
	Py_ssize_t i = 0;
	Py_ssize_t delta = 0;

	for (; i + 4 <= len; i += 4) {
		if (NEEDS_ESCAPE[inp[i]] | NEEDS_ESCAPE[inp[i+1]] |
		    NEEDS_ESCAPE[inp[i+2]] | NEEDS_ESCAPE[inp[i+3]]) {
			delta += DELTA_TABLE[inp[i]]   + DELTA_TABLE[inp[i+1]] +
			         DELTA_TABLE[inp[i+2]] + DELTA_TABLE[inp[i+3]];
		}
	}
	for (; i < len; i++)
		delta += DELTA_TABLE[inp[i]];

	return delta;
}

static PyObject *
escape_unicode_kind1(PyUnicodeObject *in)
{
	const Py_UCS1 *inp = PyUnicode_1BYTE_DATA(in);
	Py_ssize_t len = PyUnicode_GET_LENGTH(in);
	Py_ssize_t delta = count_delta_1(inp, len);

	if (!delta) {
		Py_INCREF(in);
		return (PyObject *)in;
	}

	PyObject *out = PyUnicode_New(len + delta,
	                              PyUnicode_IS_ASCII(in) ? 127 : 255);
	if (!out)
		return NULL;

	Py_UCS1 *outp = PyUnicode_1BYTE_DATA(out);
	Py_ssize_t prev = 0;
	for (Py_ssize_t i = 0; i < len; i++) {
		uint8_t ri = REPLACE_INDEX[inp[i]];
		if (ri) {
			if (i > prev) {
				memcpy(outp, inp + prev, i - prev);
				outp += i - prev;
			}
			uint8_t rlen = REPLACEMENT_LEN[ri];
			memcpy(outp, REPLACEMENT_STR[ri], rlen);
			outp += rlen;
			prev = i + 1;
		}
	}
	if (len > prev)
		memcpy(outp, inp + prev, len - prev);

	return out;
}

static PyObject *
escape_unicode_kind2(PyUnicodeObject *in)
{
	const Py_UCS2 *inp = PyUnicode_2BYTE_DATA(in);
	Py_ssize_t len = PyUnicode_GET_LENGTH(in);
	Py_ssize_t delta = 0;

	for (Py_ssize_t i = 0; i < len; i++)
		delta += (inp[i] < 256) ? DELTA_TABLE[inp[i]] : 0;

	if (!delta) {
		Py_INCREF(in);
		return (PyObject *)in;
	}

	PyObject *out = PyUnicode_New(len + delta, 65535);
	if (!out)
		return NULL;

	Py_UCS2 *outp = PyUnicode_2BYTE_DATA(out);
	Py_ssize_t prev = 0;
	for (Py_ssize_t i = 0; i < len; i++) {
		uint8_t ri = (inp[i] < 256) ? REPLACE_INDEX[inp[i]] : 0;
		if (ri) {
			if (i > prev) {
				memcpy(outp, inp + prev, (i - prev) * sizeof(Py_UCS2));
				outp += i - prev;
			}
			const char *repl = REPLACEMENT_STR[ri];
			uint8_t rlen = REPLACEMENT_LEN[ri];
			for (uint8_t j = 0; j < rlen; j++)
				*outp++ = (Py_UCS2)(unsigned char)repl[j];
			prev = i + 1;
		}
	}
	if (len > prev)
		memcpy(outp, inp + prev, (len - prev) * sizeof(Py_UCS2));

	return out;
}

static PyObject *
escape_unicode_kind4(PyUnicodeObject *in)
{
	const Py_UCS4 *inp = PyUnicode_4BYTE_DATA(in);
	Py_ssize_t len = PyUnicode_GET_LENGTH(in);
	Py_ssize_t delta = 0;

	for (Py_ssize_t i = 0; i < len; i++)
		delta += (inp[i] < 256) ? DELTA_TABLE[inp[i]] : 0;

	if (!delta) {
		Py_INCREF(in);
		return (PyObject *)in;
	}

	PyObject *out = PyUnicode_New(len + delta, 1114111);
	if (!out)
		return NULL;

	Py_UCS4 *outp = PyUnicode_4BYTE_DATA(out);
	Py_ssize_t prev = 0;
	for (Py_ssize_t i = 0; i < len; i++) {
		uint8_t ri = (inp[i] < 256) ? REPLACE_INDEX[inp[i]] : 0;
		if (ri) {
			if (i > prev) {
				memcpy(outp, inp + prev, (i - prev) * sizeof(Py_UCS4));
				outp += i - prev;
			}
			const char *repl = REPLACEMENT_STR[ri];
			uint8_t rlen = REPLACEMENT_LEN[ri];
			for (uint8_t j = 0; j < rlen; j++)
				*outp++ = (Py_UCS4)(unsigned char)repl[j];
			prev = i + 1;
		}
	}
	if (len > prev)
		memcpy(outp, inp + prev, (len - prev) * sizeof(Py_UCS4));

	return out;
}

static PyObject *
escape_unicode(PyObject *self, PyObject *s)
{
	if (!PyUnicode_Check(s))
		return NULL;

    // This check is no longer needed in Python 3.12.
	if (PyUnicode_READY(s))
		return NULL;

	switch (PyUnicode_KIND(s)) {
	case PyUnicode_1BYTE_KIND:
		return escape_unicode_kind1((PyUnicodeObject *) s);
	case PyUnicode_2BYTE_KIND:
		return escape_unicode_kind2((PyUnicodeObject *) s);
	case PyUnicode_4BYTE_KIND:
		return escape_unicode_kind4((PyUnicodeObject *) s);
	}
	assert(0);  /* shouldn't happen */
	return NULL;
}

static PyMethodDef module_methods[] = {
	{"_escape_inner", (PyCFunction)escape_unicode, METH_O, NULL},
	{NULL, NULL, 0, NULL}  /* Sentinel */
};

static PyModuleDef_Slot module_slots[] = {
#ifdef Py_mod_multiple_interpreters  // Python 3.12+
	{Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
#endif
#ifdef Py_mod_gil  // Python 3.13+
	{Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
	{0, NULL}  /* Sentinel */
};

static struct PyModuleDef module_definition = {
	.m_base = PyModuleDef_HEAD_INIT,
	.m_name = "markupsafe._speedups",
	.m_size = 0,
	.m_methods = module_methods,
	.m_slots = module_slots,
};

PyMODINIT_FUNC
PyInit__speedups(void)
{
	return PyModuleDef_Init(&module_definition);
}
