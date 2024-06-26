#include <Python.h>

#define GET_DELTA(inp, inp_end, delta) \
	while (inp < inp_end) { \
		switch (*inp++) { \
		case '"': \
		case '\'': \
		case '&': \
			delta += 4; \
			break; \
		case '<': \
		case '>': \
			delta += 3; \
			break; \
		} \
	}

#define DO_ESCAPE(inp, inp_end, outp) \
	{ \
		Py_ssize_t ncopy = 0; \
		while (inp < inp_end) { \
			switch (*inp) { \
			case '"': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = '#'; \
				*outp++ = '3'; \
				*outp++ = '4'; \
				*outp++ = ';'; \
				break; \
			case '\'': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = '#'; \
				*outp++ = '3'; \
				*outp++ = '9'; \
				*outp++ = ';'; \
				break; \
			case '&': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = 'a'; \
				*outp++ = 'm'; \
				*outp++ = 'p'; \
				*outp++ = ';'; \
				break; \
			case '<': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = 'l'; \
				*outp++ = 't'; \
				*outp++ = ';'; \
				break; \
			case '>': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = 'g'; \
				*outp++ = 't'; \
				*outp++ = ';'; \
				break; \
			default: \
				ncopy++; \
			} \
			inp++; \
		} \
		memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
	}

static PyObject*
escape_unicode_kind1(PyObject *in, const void *data, Py_ssize_t size)
{
	Py_UCS1 *inp = (Py_UCS1*)data;
	Py_UCS1 *inp_end = inp + size;
	Py_UCS1 *outbuf, *outp;
	PyObject *out;
	Py_ssize_t delta = 0;

	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		return Py_NewRef(in);
	}

	outbuf = PyMem_Malloc((size + delta) * sizeof(Py_UCS1));
	if (outbuf == NULL) {
		return NULL;
	}
	inp = (Py_UCS1*)data;
	outp = outbuf;
	DO_ESCAPE(inp, inp_end, outp);

	out = PyUnicode_Import(outbuf, (size + delta) * sizeof(Py_UCS1),
	                       PyUnicode_FORMAT_UCS1);
	PyMem_Free(outbuf);
	return out;
}

static PyObject*
escape_unicode_kind2(PyObject *in, const void *data, Py_ssize_t size)
{
	Py_UCS2 *inp = (Py_UCS2*)data;
	Py_UCS2 *inp_end = inp + size;
	Py_UCS2 *outbuf, *outp;
	PyObject *out;
	Py_ssize_t delta = 0;

	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		return Py_NewRef(in);
	}

	outbuf = PyMem_Malloc((size + delta) * sizeof(Py_UCS2));
	if (outbuf == NULL) {
		return NULL;
	}
	inp = (Py_UCS2*)data;
	outp = outbuf;
	DO_ESCAPE(inp, inp_end, outp);

	out = PyUnicode_Import(outbuf, (size + delta) * sizeof(Py_UCS2),
	                       PyUnicode_FORMAT_UCS2);
	PyMem_Free(outbuf);
	return out;
}


static PyObject*
escape_unicode_kind4(PyObject *in, const void *data, Py_ssize_t size)
{
	Py_UCS4 *inp = (Py_UCS4*)data;
	Py_UCS4 *inp_end = inp + size;
	Py_UCS4 *outbuf, *outp;
	PyObject *out;
	Py_ssize_t delta = 0;

	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		return Py_NewRef(in);
	}

	outbuf = PyMem_Malloc((size + delta) * sizeof(Py_UCS4));
	if (outbuf == NULL) {
		return NULL;
	}
	inp = (Py_UCS4*)data;
	outp = outbuf;
	DO_ESCAPE(inp, inp_end, outp);

	out = PyUnicode_Import(outbuf, (size + delta) * sizeof(Py_UCS4),
	                       PyUnicode_FORMAT_UCS4);
	PyMem_Free(outbuf);
	return out;
}

static PyObject*
escape_unicode(PyObject *self, PyObject *s)
{
	uint32_t formats = (PyUnicode_FORMAT_ASCII
	                    | PyUnicode_FORMAT_UCS1
	                    | PyUnicode_FORMAT_UCS2
	                    | PyUnicode_FORMAT_UCS4);
	uint32_t format;
	Py_ssize_t size;
	const void *data = PyUnicode_Export(s, formats, &size, &format);
	if (data == NULL) {
		return NULL;
	}

	PyObject *res;
	switch (format) {
	case PyUnicode_FORMAT_ASCII:
	case PyUnicode_FORMAT_UCS1:
		res = escape_unicode_kind1(s, data, size);
		break;
	case PyUnicode_FORMAT_UCS2:
		res = escape_unicode_kind2(s, data, size / 2);
		break;
	case PyUnicode_FORMAT_UCS4:
		res = escape_unicode_kind4(s, data, size / 4);
		break;
	default:
		assert(0);  /* shouldn't happen */
		res = NULL;
	}
	PyUnicode_ReleaseExport(s, data, format);
	return res;
}

static PyMethodDef module_methods[] = {
	{"_escape_inner", (PyCFunction)escape_unicode, METH_O, NULL},
	{NULL, NULL, 0, NULL}  /* Sentinel */
};

static struct PyModuleDef module_definition = {
	PyModuleDef_HEAD_INIT,
	"markupsafe._speedups",
	NULL,
	-1,
	module_methods,
	NULL,
	NULL,
	NULL,
	NULL
};

PyMODINIT_FUNC
PyInit__speedups(void)
{
	return PyModule_Create(&module_definition);
}
