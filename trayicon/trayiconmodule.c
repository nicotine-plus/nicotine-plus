/* -*- Mode: C; c-basic-offset: 4 -*- */

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void trayicon_register_classes (PyObject *d);

extern PyMethodDef trayicon_functions[];

DL_EXPORT(void)
inittrayicon(void)
{
    PyObject *m, *d;
	
    init_pygobject ();

    m = Py_InitModule ("trayicon", trayicon_functions);
    d = PyModule_GetDict (m);
	
    trayicon_register_classes (d);

    if (PyErr_Occurred ()) {
	Py_FatalError ("can't initialise module trayicon :(");
    }
}
