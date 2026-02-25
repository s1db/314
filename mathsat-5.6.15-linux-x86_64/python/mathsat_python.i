/* -*- swig -*- */
/* SWIG interface file to create the Python API for MathSAT */
/* author: Alberto Griggio <griggio@fbk.eu> */

%include "typemaps.i"
/*
%typemap(in) char *buf {
 if (PyString_Check($input)) {
        $1 = strdup(PyString_AsString($input));
 } else {
        PyErr_SetString(PyExc_TypeError, "String argument required");
        return NULL;
 }
}
%typemap(freearg) char *buf {
  if ($1) free($1);
}
*/

/* msat_term_repr allocates the return value, we have to free it before
 * getting back to python */
%typemap(out) char *msat_term_repr(msat_term t) {
  if ($1 == NULL) {
     Py_INCREF(Py_None);
     $result = Py_None;
  } else {
     $result = PyString_FromString($1);
     msat_free($1);
  }
}
%typemap(out) char *msat_to_smtlib1(msat_env e, msat_term term) {
  if ($1 == NULL) {
     Py_INCREF(Py_None);
     $result = Py_None;
  } else {
     $result = PyString_FromString($1);
     msat_free($1);
  }
}
%typemap(out) char *msat_to_smtlib2(msat_env e, msat_term term) {
  if ($1 == NULL) {
     Py_INCREF(Py_None);
     $result = Py_None;
  } else {
     $result = PyString_FromString($1);
     msat_free($1);
  }
}
%typemap(out) char *msat_decl_get_name(msat_decl d) {
    if ($1 == NULL) {
        Py_INCREF(Py_None);
        $result = Py_None;
    } else {
        $result = PyString_FromString($1);
        msat_free($1);
    }
}
%typemap(out) char *msat_type_repr(msat_type t) {
  if ($1 == NULL) {
     Py_INCREF(Py_None);
     $result = Py_None;
  } else {
     $result = PyString_FromString($1);
     msat_free($1);
  }
}
%typemap(out) char *msat_decl_repr(msat_decl d) {
  if ($1 == NULL) {
     Py_INCREF(Py_None);
     $result = Py_None;
  } else {
     $result = PyString_FromString($1);
     msat_free($1);
  }
}

/* we want to use python lists for C arrays */
%typemap(in) msat_type *param_types {
    int i, sz;
    msat_type *tmp;
    void *ptr;
    int r;
    if (!PySequence_Check($input)) {
        PyErr_SetString(PyExc_TypeError, "Sequence object required");
        return NULL;
    }
    sz = PySequence_Size($input);
    tmp = malloc(sizeof(msat_type) * sz);
    for (i = 0; i < sz; ++i) {
        PyObject *p = PySequence_ITEM($input, i);
        r = SWIG_ConvertPtr(p, &ptr, SWIGTYPE_p_msat_type, 0);
        Py_DECREF(p);
        if (!SWIG_IsOK(r)) {
            free(tmp);
            PyErr_SetString(PyExc_TypeError, "Invalid type for argument, " \
                            "msat_type object expected");
            return NULL;
        } else {
            tmp[i] = *((msat_type *)(ptr));
        }
     }
    $1 = tmp;
}
%typemap(freearg) msat_type *param_types {
   if ($1) free($1);
}
%rename(_msat_get_function_type) msat_get_function_type;

%typemap(in) msat_term args[] {
   int i, sz;
   msat_term *tmp;
   void *ptr;
   int r;
   if (!PySequence_Check($input)) {
       PyErr_SetString(PyExc_TypeError, "Sequence object required");
       return NULL;
   }
   sz = PySequence_Size($input);
   tmp = malloc(sizeof(msat_term) * sz);
   for (i = 0; i < sz; ++i) {
       PyObject *p = PySequence_ITEM($input, i);
       r = SWIG_ConvertPtr(p, &ptr, SWIGTYPE_p_msat_term, 0);
       Py_DECREF(p);
       if (!SWIG_IsOK(r)) {
           free(tmp);
           PyErr_SetString(PyExc_TypeError, "Invalid type for argument, " \
                           "msat_term object expected");
           return NULL;
       } else {
           tmp[i] = *((msat_term *)(ptr));
       }
   }
   $1 = tmp;
}
%typemap(freearg) msat_term args[] {
   if ($1) free($1);
}

%rename(_msat_model_iterator_next) msat_model_iterator_next;

%typemap(in) msat_term *important = msat_term args[];
%typemap(freearg) msat_term *important = msat_term args[];

%rename(_msat_all_sat) msat_all_sat;
%rename(_msat_all_sat_ext) msat_all_sat_ext;

%typemap(in) (msat_all_sat_model_callback func, void *user_data) {
    if ($input == Py_None) {
        $1 = NULL;
        $2 = NULL;
    } else {
        if (!PyCallable_Check($input)) {
            PyErr_SetString(PyExc_TypeError, "Callable object required!\n");
            return NULL;
        }
        $1 = call_allsat_python_callable;
        $2 = (void *)$input;
    }
}
%typemap(in) (msat_visit_term_callback func, void *user_data) {
    if ($input == Py_None) {
        $1 = NULL;
        $2 = NULL;
    } else {
        if (!PyCallable_Check($input)) {
            PyErr_SetString(PyExc_TypeError, "Callable object required!\n");
            return NULL;
        }
        $1 = call_visit_python_callable;
        $2 = (void *)$input;
    }
}
%typemap(in) (msat_termination_test func, void *user_data) {
    if ($input == Py_None) {
        $1 = NULL;
        $2 = NULL;
    } else {
        if (!PyCallable_Check($input)) {
            PyErr_SetString(PyExc_TypeError, "Callable object required!\n");
            return NULL;
        }
        $1 = call_termtest_python_callable;
        $2 = (void *)$input;
    }
}


%typemap(in) msat_term *diversifiers = msat_term args[];
%typemap(freearg) msat_term *diversifiers = msat_term args[];

%rename(_msat_solve_diversify) msat_solve_diversify;

%typemap(in) (msat_solve_diversify_model_callback func, void *user_data) {
    if ($input == Py_None) {
        $1 = NULL;
        $2 = NULL;
    } else {
        if (!PyCallable_Check($input)) {
            PyErr_SetString(PyExc_TypeError, "Callable object required!\n");
            return NULL;
        }
        $1 = call_solve_diversify_python_callable;
        $2 = (void *)$input;
    }
}

%typemap(in) mpq_t out {
    mpq_init($1);
}
%typemap(freearg) mpq_t out {
    mpq_clear($1);
}
%typemap(out) int msat_term_to_number(msat_env e, msat_term t, mpq_t out) {
    char *s;
    $result = NULL;
    s = mpq_get_str(NULL, 10, arg3);
    if (s) {
        $result = PyString_FromString(s);
        free(s);
    }
}
%rename(_msat_term_to_number) msat_term_to_number;

%typemap(in) mpz_t out_mod {
    mpz_init_set_si($1, 0);
}
%typemap(freearg) mpz_t out_mod {
    mpz_clear($1);
}
%typemap(out) int msat_term_is_int_modular_congruence(msat_env e, msat_term t, mpz_t out_mod) {
    char *s;
    $result = NULL;
    s = mpz_get_str(NULL, 10, arg3);
    if (s) {
        $result = Py_BuildValue("is", $1, s);
        free(s);
    }
}
%rename(_msat_term_is_int_modular_congruence) msat_term_is_int_modular_congruence;

%typemap(in) mpz_t modulus {
    char *s = PyString_AsString($input);
    mpz_init_set_str($1, s, 10);
}
%typemap(freearg) mpz_t modulus {
    mpz_clear($1);
}
%rename(_msat_make_int_modular_congruence) msat_make_int_modular_congruence;


%typemap(in) size_t * {
   $1 = (size_t *)malloc(sizeof(size_t));
}
%typemap(freearg) size_t * {
   free($1);
}


%typemap(out) msat_term *msat_get_asserted_formulas(msat_env e,
                                                    size_t *num_asserted) {
    size_t l = *arg2;
    size_t i;
    PyObject *r;
    $result = PyList_New(l);
    for (i = 0; i < l; ++i) {
        r = SWIG_NewPointerObj(
            (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                &($1[i]), sizeof(msat_term)),
            SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
        PyList_SET_ITEM($result, i, r);
    }
    if ($1) msat_free($1);
}
%rename(_msat_get_asserted_formulas) msat_get_asserted_formulas;

%typemap(out) msat_term *msat_get_unsat_core(msat_env e, size_t *core_size) {
    size_t l = *arg2;
    size_t i;
    PyObject *r;
    $result = PyList_New(l);
    for (i = 0; i < l; ++i) {
        r = SWIG_NewPointerObj(
            (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                &($1[i]), sizeof(msat_term)),
            SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
        PyList_SET_ITEM($result, i, r);
    }
    if ($1) msat_free($1);
}
%rename(_msat_get_unsat_core) msat_get_unsat_core;

%typemap(out) msat_term *msat_get_theory_lemmas(msat_env e, size_t *num_tlemmas) {
    size_t l = *arg2;
    size_t i;
    PyObject *r;
    $result = PyList_New(l);
    for (i = 0; i < l; ++i) {
        r = SWIG_NewPointerObj(
            (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                &($1[i]), sizeof(msat_term)),
            SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
        PyList_SET_ITEM($result, i, r);
    }
    if ($1) msat_free($1);
}
%rename(_msat_get_theory_lemmas) msat_get_theory_lemmas;


%typemap(in) msat_term *assumptions = msat_term args[];
%typemap(freearg) msat_term *assumptions = msat_term args[];

%typemap(out) msat_term *msat_get_unsat_assumptions(msat_env e, size_t *assumps_size) {
    size_t l = *arg2;
    size_t i;
    PyObject *r;
    $result = PyList_New(l);
    for (i = 0; i < l; ++i) {
        r = SWIG_NewPointerObj(
            (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                &($1[i]), sizeof(msat_term)),
            SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
        PyList_SET_ITEM($result, i, r);
    }
    if ($1) msat_free($1);
}
%rename(_msat_get_unsat_assumptions) msat_get_unsat_assumptions;
%rename(_msat_solve_with_assumptions) msat_solve_with_assumptions;


/* we want to use python lists for C arrays */
%typemap(in) int *groups_of_a {
    int i, sz;
    int *tmp;
    if (!PySequence_Check($input)) {
        PyErr_SetString(PyExc_TypeError, "Sequence object required");
        return NULL;
    }
    sz = PySequence_Size($input);
    tmp = malloc(sizeof(int) * sz);
    for (i = 0; i < sz; ++i) {
        PyObject *p = PySequence_ITEM($input, i);
        tmp[i] = PyInt_AsLong(p);
        Py_DECREF(p);
    }
    $1 = tmp;
}
%typemap(freearg) int *groups_of_a {
   if ($1) free($1);
}
%rename(_msat_get_interpolant) msat_get_interpolant;

%ignore msat_from_smtlib1_file;
%ignore msat_from_smtlib2_file;
%ignore msat_to_smtlib1_file;
%ignore msat_to_smtlib2_file;
%ignore msat_to_smtlib2_ext_file;

%rename(_msat_create_env) msat_create_env;
%rename(_msat_create_shared_env) msat_create_shared_env;

%exception msat_all_sat {
    if (setjmp(exception_buffer) == 0) {
        $action
    } else {
        SWIG_fail;
    }
}
%exception msat_all_sat_ext {
    if (setjmp(exception_buffer) == 0) {
        $action
    } else {
        SWIG_fail;
    }
}
%exception msat_visit_term {
    if (setjmp(exception_buffer) == 0) {
        $action
    } else {
        SWIG_fail;
    }
}

%typemap(out) int msat_is_bv_type(msat_env env, msat_type tp, size_t *out_width) {
    size_t w = *arg3;
    $result = Py_BuildValue("(ik)", $1, w);
}
%rename(_msat_is_bv_type) msat_is_bv_type;

%typemap(out) int msat_is_fp_type(msat_env env, msat_type tp, size_t *out_exp_width, size_t *out_mant_width) {
    size_t ew = *arg3;
    size_t mw = *arg4;
    $result = Py_BuildValue("(ikk)", $1, ew, mw);
}
%rename(_msat_is_fp_type) msat_is_fp_type;


%typemap(in) msat_type *out_itp {
    $1 = (msat_type *)malloc(sizeof(msat_type));
}
%typemap(freearg) msat_type *out_itp {
    free($1);
}
%typemap(in) msat_type *out_etp {
    $1 = (msat_type *)malloc(sizeof(msat_type));
}
%typemap(freearg) msat_type *out_etp {
    free($1);
}
%typemap(out) int msat_is_array_type(msat_env env, msat_type tp, msat_type *out_itp, msat_type *out_etp) {
    PyObject *py_itp = SWIG_NewPointerObj(
            (msat_type *)memcpy((msat_type *)malloc(sizeof(msat_type)),
                                arg3, sizeof(msat_type)),
            SWIGTYPE_p_msat_type, SWIG_POINTER_OWN);
    PyObject *py_etp = SWIG_NewPointerObj(
            (msat_type *)memcpy((msat_type *)malloc(sizeof(msat_type)),
                                arg4, sizeof(msat_type)),
            SWIGTYPE_p_msat_type, SWIG_POINTER_OWN);
    $result = Py_BuildValue("(iOO)", $1, py_itp, py_etp);
}
%rename(_msat_is_array_type) msat_is_array_type;

%rename(_msat_get_enum_type) msat_get_enum_type;

%typemap(in) msat_decl **out_domain {
    $1 = (msat_decl **)malloc(sizeof(msat_decl *));
}
%typemap(freearg) msat_decl **out_domain {
    free($1);
}
%typemap(out) int msat_is_enum_type(msat_env env, msat_type tp, size_t *out_domain_size, msat_decl **out_domain) {
    size_t i;
    size_t n = *arg3;
    PyObject *py_d = PyList_New(n);
    msat_decl *domain = *arg4;
    for (i = 0; i < n; ++i) {
        PyObject *v = SWIG_NewPointerObj(
            (msat_decl *)memcpy((msat_decl *)malloc(sizeof(msat_decl)),
                                &(domain[i]), sizeof(msat_decl)),
            SWIGTYPE_p_msat_decl, SWIG_POINTER_OWN);
        PyList_SET_ITEM(py_d, i, v);
    }
    $result = Py_BuildValue("(iO)", $1, py_d);
}
%rename(_msat_is_enum_type) msat_is_enum_type;

%typemap(in) char **out_name {
    $1 = (char **)malloc(sizeof(char *));
}
%typemap(freearg) char **out_name {
    free($1);
}
%typemap(out) int msat_is_simple_type(msat_env env, msat_type tp, char **out_name) {
    char *name = *arg3;
    PyObject *py_name;
    if ($1) {
        py_name = PyString_FromString(name);
    } else {
        py_name = Py_None;
        Py_INCREF(Py_None);
    }
    $result = Py_BuildValue("(iO)", $1, py_name);
}
%rename(_msat_is_simple_type) msat_is_simple_type;


%typemap(in) msat_type **out_param_types {
    $1 = (msat_type **)malloc(sizeof(msat_type *));
}
%typemap(freearg) msat_type **out_param_types {
    free($1);
}
%typemap(in) msat_type *out_return_type {
    $1 = (msat_type *)malloc(sizeof(msat_type));
}
%typemap(freearg) msat_type *out_return_type {
    free($1);
}
%typemap(out) int msat_is_function_type(msat_env env, msat_type tp, size_t *out_num_params, msat_type **out_param_types, msat_type *out_return_type) {
    size_t i;
    size_t n = *arg3;
    PyObject *py_p = PyList_New(n);
    msat_type *params = *arg4;
    msat_type ret = *arg5;
    for (i = 0; i < n; ++i) {
        PyObject *v = SWIG_NewPointerObj(
            (msat_type *)memcpy((msat_type *)malloc(sizeof(msat_type)),
                                &(params[i]), sizeof(msat_type)),
            SWIGTYPE_p_msat_type, SWIG_POINTER_OWN);
        PyList_SET_ITEM(py_p, i, v);
    }
    PyObject *r;
    if ($1) {
        r = SWIG_NewPointerObj(
            (msat_type *)memcpy((msat_type *)malloc(sizeof(msat_type)),
                                &ret, sizeof(msat_type)),
            SWIGTYPE_p_msat_type, SWIG_POINTER_OWN);
    } else {
        r = Py_None;
        Py_INCREF(Py_None);
    }
    $result = Py_BuildValue("(iOO)", $1, py_p, r);
}
%rename(_msat_is_function_type) msat_is_function_type;


%typemap(out) int msat_term_is_bv_extract(msat_env e, msat_term t, size_t *out_msb, size_t *out_lsb) {
    size_t msb = *arg3;
    size_t lsb = *arg4;
    return Py_BuildValue("(ikk)", $1, msb, lsb);
}
%rename(_msat_term_is_bv_extract) msat_term_is_bv_extract;

%typemap(out) int msat_term_is_bv_zext(msat_env e, msat_term t, size_t *out_amount) {
    size_t amount = *arg3;
    return Py_BuildValue("(ik)", $1, amount);
}
%rename(_msat_term_is_bv_zext) msat_term_is_bv_zext;

%typemap(out) int msat_term_is_bv_sext(msat_env e, msat_term t, size_t *out_amount) {
    size_t amount = *arg3;
    return Py_BuildValue("(ik)", $1, amount);
}
%rename(_msat_term_is_bv_sext) msat_term_is_bv_sext;

%typemap(out) int msat_term_is_bv_rol(msat_env e, msat_term t, size_t *out_amount) {
    size_t amount = *arg3;
    return Py_BuildValue("(ik)", $1, amount);
}
%rename(_msat_term_is_bv_rol) msat_term_is_bv_rol;

%typemap(out) int msat_term_is_bv_ror(msat_env e, msat_term t, size_t *out_amount) {
    size_t amount = *arg3;
    return Py_BuildValue("(ik)", $1, amount);
}
%rename(_msat_term_is_bv_ror) msat_term_is_bv_ror;

%ignore msat_free;

%ignore msat_parse_config_file;
%rename(_msat_parse_config) msat_parse_config;

/***************************************************************************/
/* named_list support */

%typemap(in) char *** {
    $1 = (char ***)malloc(sizeof(char **));
}
%typemap(freearg) char *** {
    free($1);
}

%typemap(in) msat_term ** {
    $1 = (msat_term **)malloc(sizeof(msat_term *));
}
%typemap(freearg) msat_term ** {
    free($1);
}

%typemap(out) int msat_named_list_from_smtlib2(msat_env e, const char *data,
                                 size_t *out_n,
                                 char ***out_names, msat_term **out_terms) {
    if ($1 != 0) {
        Py_INCREF(Py_None);
        $result = Py_None;
    } else {
        size_t n = *arg3;
        size_t i;
        PyObject *r, *rn, *rt;
        $result = PyList_New(n);
        for (i = 0; i < n; ++i) {
            rt = SWIG_NewPointerObj(
                (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                    &((*arg5)[i]), sizeof(msat_term)),
                 SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
            rn = PyString_FromString((*arg4)[i]);
            r = Py_BuildValue("NN", rn, rt);
            PyList_SET_ITEM($result, i, r);
        }
    }
}

%typemap(in) msat_term *terms = msat_term args[];
%typemap(freearg) msat_term *terms = msat_term args[];

%typemap(in) const char **names {
    int i, sz;
    char **tmp;
    if (!PySequence_Check($input)) {
        PyErr_SetString(PyExc_TypeError, "Sequence object required");
        return NULL;
    }
    sz = PySequence_Size($input);
    tmp = malloc(sizeof(const char *) * sz);
    for (i = 0; i < sz; ++i) {
        PyObject *p = PySequence_ITEM($input, i);
        char *s = PyString_AsString(p);
        Py_DECREF(p);
        if (s == NULL) {
            free(tmp);
            return NULL;
        } else {
            tmp[i] = s;
        }
    }
    $1 = tmp;
}
%typemap(freearg) const char **names {
    if ($1) free($1);
}

%typemap(in) const char **domain = const char **names;
%typemap(freearg) const char **domain = const char **names;

%rename(_msat_named_list_from_smtlib2) msat_named_list_from_smtlib2;
%rename(_msat_named_list_to_smtlib2) msat_named_list_to_smtlib2;

%ignore msat_named_list_from_smtlib2_file;
%ignore msat_named_list_to_smtlib2_file;

%typemap(out) int msat_annotated_list_from_smtlib2(msat_env e, const char *data,
                                 size_t *out_n, msat_term **out_terms,
                                 char ***out_annots) {
    if ($1 != 0) {
        Py_INCREF(Py_None);
        $result = Py_None;
    } else {
        size_t n = *arg3;
        size_t i;
        PyObject *rt, *ra, *rv;
        PyObject *res_t, *res_a;
        res_t = PyList_New(n);
        res_a = PyList_New(2 * n);
        $result = NULL;
        for (i = 0; i < n; ++i) {
            rt = SWIG_NewPointerObj(
                (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                    &((*arg4)[i]), sizeof(msat_term)),
                 SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
            ra = PyString_FromString((*arg5)[2*i]);
            rv = PyString_FromString((*arg5)[2*i+1]);
            PyList_SET_ITEM(res_t, i, rt);
            PyList_SET_ITEM(res_a, 2*i, ra);
            PyList_SET_ITEM(res_a, 2*i+1, rv);
        }
        $result = Py_BuildValue("NN", res_t, res_a);
    }
}

%typemap(in) const char **annots = const char **names;
%typemap(freearg) const char *annots = const char **names;

%rename(_msat_annotated_list_from_smtlib2) msat_annotated_list_from_smtlib2;
%rename(_msat_annotated_list_to_smtlib2) msat_annotated_list_to_smtlib2;

%ignore msat_annotated_list_from_smtlib2_file;
%ignore msat_annotated_list_to_smtlib2_file;

%ignore msat_make_int_number;
%ignore msat_make_mpq_number;
%ignore msat_make_bv_int_number;
%ignore msat_make_bv_mpz_number;

/***************************************************************************/

%typemap(in) msat_term *tokeep = msat_term args[];
%typemap(freearg) msat_term *tokeep = msat_term args[];
%rename(_msat_gc_env) msat_gc_env;

%rename(_msat_exist_elim) msat_exist_elim;
%typemap(in) msat_term *vars_to_elim = msat_term args[];
%typemap(freearg) msat_term *vars_to_elim = msat_term args[];

%rename(_msat_exist_elim_model) msat_exist_elim_model;
%typemap(in) msat_term *model_vars = msat_term args[];
%typemap(freearg) msat_term *model_vars = msat_term args[];
%typemap(in) msat_term *model_values = msat_term args[];
%typemap(freearg) msat_term *model_values = msat_term args[];

%typemap(in) msat_term *to_subst = msat_term args[];
%typemap(freearg) msat_term *to_subst = msat_term args[];
%typemap(in) msat_term *values = msat_term args[];
%typemap(freearg) msat_term *values = msat_term args[];
%rename(_msat_apply_substitution) msat_apply_substitution;

%typemap(in) msat_term *to_protect {
   int i, sz;
   msat_term *tmp;
   void *ptr;
   int r;
   if ($input == Py_None) {
       tmp = NULL;
   } else if (!PySequence_Check($input)) {
       PyErr_SetString(PyExc_TypeError, "Sequence object required");
       return NULL;
   } else {
       sz = PySequence_Size($input);
       tmp = malloc(sizeof(msat_term) * sz);
       for (i = 0; i < sz; ++i) {
           PyObject *p = PySequence_ITEM($input, i);
           r = SWIG_ConvertPtr(p, &ptr, SWIGTYPE_p_msat_term, 0);
           Py_DECREF(p);
           if (!SWIG_IsOK(r)) {
               free(tmp);
               PyErr_SetString(PyExc_TypeError, "Invalid type for argument, " \
                               "msat_term object expected");
               return NULL;
           } else {
               tmp[i] = *((msat_term *)(ptr));
           }
       }
   }
   $1 = tmp;
}
%typemap(freearg) msat_term *to_protect = msat_term args[];
%rename(_msat_simplify) msat_simplify;

%typemap(in) msat_aig {
    $1 = (msat_aig)PyLong_AsVoidPtr($input);
}

%typemap(out) msat_aig {
    $result = PyLong_FromVoidPtr((void *)$1);
}

%typemap(out) msat_aig *msat_aig_encode(msat_aig_manager mgr, msat_term t, size_t *out_size) {
    if ($1 == NULL) {
        Py_INCREF(Py_None);
        $result = Py_None;
    } else {
        size_t l = *arg3;
        size_t i;
        PyObject *r;
        $result = PyList_New(l);
        for (i = 0; i < l; ++i) {
            r = PyLong_FromVoidPtr((void *)$1[i]);
            PyList_SET_ITEM($result, i, r);
        }
    }
}
%rename(_msat_aig_encode) msat_aig_encode;

%typemap(out) char *msat_aig_to_aiger(msat_aig_manager mgr, msat_aig a) {
  if ($1 == NULL) {
     Py_INCREF(Py_None);
     $result = Py_None;
  } else {
     $result = PyString_FromString($1);
     msat_free($1);
  }
}

#if MSATIC3
%include "msatic3_swig.i"
#endif /* MSATIC3 */

#if OPTIMATHSAT
%include "swig_code.i"
#endif /* OPTIMATHSAT */

%{
#include "mathsat.h"
#include "mathsataig.h"
#include "msatexistelim.h"
#include <setjmp.h>
%}
#if MSATIC3
%include "msatic3_c_include.i"
#endif /* MSATIC3 */
#if OPTIMATHSAT
%include "c_include_code.i"
#endif /* OPTIMATHSAT */

%include "mathsat.h"
%include "mathsataig.h"
%include "msatexistelim.h"
#if MSATIC3
%include "msatic3_swig_include.i"
#endif /* MSATIC3 */
#if OPTIMATHSAT
%include "swig_include_code.i"
#endif /* OPTIMATHSAT */

%{

static jmp_buf exception_buffer;


static int call_allsat_python_callable(msat_term *model, int size, void *data)
{
    PyObject *callable = (PyObject *)data;
    PyObject *result;
    PyObject *pymodel = PyList_New(size);
    PyObject *args;
    int i, retval;
    for (i = 0; i < size; ++i) {
        result = SWIG_NewPointerObj(
               (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                                   &(model[i]), sizeof(msat_term)),
                SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
        PyList_SET_ITEM(pymodel, i, result);
    }
    /* call the python callback */
    args = Py_BuildValue("(O)", pymodel);
    result = PyObject_CallObject(callable, args);
    if (PyErr_Occurred()) {
        longjmp(exception_buffer, 1);
    }
    retval = (int)PyInt_AsLong(result);
    if (PyErr_Occurred()) {
        longjmp(exception_buffer, 1);
    }
    Py_XDECREF(result);
    /* free the args list */
    Py_DECREF(args);
    Py_DECREF(pymodel);

    return retval;
}

static msat_visit_status call_visit_python_callable(msat_env e, msat_term t,
                                                    int preorder, void *data)
{
    PyObject *callable = (PyObject *)data;
    PyObject *args;
    PyObject *pyenv;
    PyObject *pyterm;
    PyObject *pypreorder;
    PyObject *result;
    msat_visit_status retval;

    pyenv = SWIG_NewPointerObj(
        (msat_env *)memcpy((msat_env *)malloc(sizeof(msat_env)),
                            &(e), sizeof(msat_env)),
        SWIGTYPE_p_msat_env, SWIG_POINTER_OWN);
    pyterm = SWIG_NewPointerObj(
        (msat_term *)memcpy((msat_term *)malloc(sizeof(msat_term)),
                            &(t), sizeof(msat_term)),
        SWIGTYPE_p_msat_term, SWIG_POINTER_OWN);
    pypreorder = PyBool_FromLong(preorder);
    /* call the python callback */
    args = Py_BuildValue("(OOO)", pyenv, pyterm, pypreorder);
    result = PyObject_CallObject(callable, args);
    if (PyErr_Occurred()) {
        longjmp(exception_buffer, 1);
    }
    retval = (msat_visit_status)(PyInt_AsLong(result));
    if (PyErr_Occurred()) {
        longjmp(exception_buffer, 1);
    }
    if (retval == -1) {
        retval = MSAT_VISIT_ABORT;
    }
    Py_XDECREF(result);
    /* free the args list */
    Py_DECREF(args);
    Py_DECREF(pypreorder);
    Py_DECREF(pyterm);
    Py_DECREF(pyenv);

    return retval;
}

static int call_termtest_python_callable(void *data)
{
    PyObject *callable = (PyObject *)data;
    PyObject *result;
    PyObject *args;
    int retval;

    /* call the python callback */
    args = PyTuple_New(0);
    result = PyObject_CallObject(callable, args);
    retval = PyInt_AsLong(result);
    Py_XDECREF(result);
    /* free the args list */
    Py_DECREF(args);

    return retval;
}


static int call_solve_diversify_python_callable(msat_model_iterator it,
                                                void *data)
{
    PyObject *callable = (PyObject *)data;
    PyObject *result;
    PyObject *arg, *args;
    int retval;
    arg = SWIG_NewPointerObj(
           (msat_model_iterator *)memcpy((msat_model_iterator *)malloc(sizeof(msat_model_iterator)),
           &(it), sizeof(msat_model_iterator)),
           SWIGTYPE_p_msat_model_iterator, SWIG_POINTER_OWN);
    /* call the python callback */
    args = Py_BuildValue("(O)", arg);
    result = PyObject_CallObject(callable, args);
    if (PyErr_Occurred()) {
        longjmp(exception_buffer, 1);
    }
    retval = (int)PyInt_AsLong(result);
    if (PyErr_Occurred()) {
        longjmp(exception_buffer, 1);
    }
    Py_XDECREF(result);
    /* free the args list */
    Py_DECREF(args);
    Py_DECREF(arg);

    return retval;
}
%}

#if MSATIC3
%include "msatic3_c_static.i"
#endif /* MSATIC3 */

#if OPTIMATHSAT
%include "c_static_code.i"
#endif /* OPTIMATHSAT */


/* redefine the error checking "macros" */
%inline %{
static int MSAT_ERROR_CONFIG(msat_config c) { return c.repr == NULL; }
static int MSAT_ERROR_ENV(msat_env e) { return e.repr == NULL; }
static int MSAT_ERROR_TERM(msat_term t) { return t.repr == NULL; }
static int MSAT_ERROR_DECL(msat_decl d) { return d.repr == NULL; }
static msat_term MSAT_MAKE_ERROR_TERM(void) { msat_term t = { NULL }; return t; }
static int MSAT_ERROR_TYPE(msat_type t) { return t.repr == NULL; }
static int MSAT_ERROR_MODEL_ITERATOR(msat_model_iterator i) { return i.repr == NULL; }
static int MSAT_ERROR_MODEL(msat_model m) { return m.repr == NULL; }
static int MSAT_ERROR_PROOF_MANAGER(msat_proof_manager pm) { return pm.repr == NULL; }
static int MSAT_ERROR_PROOF(msat_proof p) { return p.repr == NULL; }

/* EXTRA_C_INLINE_CODE_TAG */

%}

/* %apply msat_term *OUTPUT {msat_term *t, msat_term *v} */

%pythoncode %{

import sys

if sys.version_info[0] >= 3:
    def _enc(s):
        if isinstance(s, str): s = s.encode('ascii')
        return s
else:
    def _enc(s): return s        


def msat_parse_config(data_or_file):
    if hasattr(data_or_file, 'read'):
        data_or_file = data_or_file.read()
    return _msat_parse_config(data_or_file)

def msat_parse_config_file(f):
    return _msat_parse_config(f.read())

def msat_create_env(conf=None, other=None):
    try:
        if conf is None:
            cfg = msat_create_config()
        elif hasattr(conf, 'items'):
            cfg = msat_create_config()
            for (k, v) in conf.items():
                msat_set_option(cfg, k, v)
        elif hasattr(conf, 'read'):
            cfg = _msat_parse_config(conf.read())
        else:
            try:
                cfg = conf + ""
            except:
                cfg = conf
            else:
                if '=' not in cfg:
                    cfg = msat_create_default_config(cfg)
                else:
                    cfg = msat_parse_config(cfg)
        if other is not None:
            return _msat_create_shared_env(cfg, other)
        else:
            return _msat_create_env(cfg)
    finally:
        if cfg is not conf:
            msat_destroy_config(cfg)

msat_create_shared_env = msat_create_env

def msat_get_function_type(env, param_types, return_type):
    return _msat_get_function_type(env, param_types, len(param_types), return_type)

def msat_model_iterator_next(i):
    "returns a tuple (term, value)"
    t = msat_term()
    v = msat_term()
    _msat_model_iterator_next(i, t, v)
    return (t, v)

def msat_all_sat(env, important, callback):
    return _msat_all_sat(env, important, len(important), callback)

def msat_all_sat_ext(env, important, phase, callback):
    return _msat_all_sat_ext(env, important, len(important), phase, callback)
                   
def msat_solve_diversify(env, diversifiers, callback):
    return _msat_solve_diversify(env, diversifiers, len(diversifiers), callback)

def msat_get_asserted_formulas(env):
    return _msat_get_asserted_formulas(env, 0)

def msat_get_unsat_core(env):
    return _msat_get_unsat_core(env, 0)

def msat_get_theory_lemmas(env):
    return _msat_get_theory_lemmas(env, 0)

def msat_solve_with_assumptions(env, assumptions):
    return _msat_solve_with_assumptions(env, assumptions, len(assumptions))

def msat_get_unsat_assumptions(env):
    return _msat_get_unsat_assumptions(env, 0)

def msat_get_interpolant(env, groups_of_a):
    return _msat_get_interpolant(env, groups_of_a, len(groups_of_a))

def msat_from_smtlib1_file(env, fileobj):
    return _msat_from_smtlib1(env, fileobj.read())

def msat_from_smtlib2_file(env, fileobj):
    return _msat_from_smtlib2(env, fileobj.read())

def msat_term_to_number(env, term):
    return _msat_term_to_number(env, term, 0)

def msat_make_int_modular_congruence(env, modulus, t1, t2):
    return _msat_make_int_modular_congruence(env, str(modulus), t1, t2)

def msat_term_is_int_modular_congruence(env, term):
    "returns a tuple (res, number)"
    return _msat_term_is_int_modular_congruence(env, term, 0)


def msat_is_bv_type(env, tp):
    "returns a tuple (res, width)"
    return _msat_is_bv_type(env, tp, None)


def msat_is_array_type(env, tp):
    "returns a tuple (res, indextp, elemtp)"
    return _msat_is_array_type(env, tp, None, None)


def msat_is_fp_type(env, tp):
    "returns a tuple (res, exp_width, mant_width)"
    return _msat_is_fp_type(env, tp, None, None)


def msat_get_enum_type(env, name, domain):
    return _msat_get_enum_type(env, name, len(domain),
                               [_enc(d) for d in domain])


def msat_is_enum_type(env, tp):
    "returns a tuple (res, domain)"
    return _msat_is_enum_type(env, tp, None, None)


def msat_is_simple_type(env, tp):
    "returns a tuple (res, name)"
    return _msat_is_simple_type(env, tp, None)


def msat_is_function_type(env, tp):
    "returns a tuple (res, param_types, return_type)"
    return _msat_is_function_type(env, tp, None, None, None)
                   

def msat_term_is_bv_extract(env, term):
    "returns a tuple (res, msb, lsb)"
    return _msat_term_is_bv_extract(env, term, None, None)


def msat_term_is_bv_zext(env, term):
    "returns a tuple (res, amount)"
    return _msat_term_is_bv_zext(env, term, None)


def msat_term_is_bv_sext(env, term):
    "returns a tuple (res, amount)"
    return _msat_term_is_bv_sext(env, term, None)


def msat_term_is_bv_rol(env, term):
    "returns a tuple (res, amount)"
    return _msat_term_is_bv_rol(env, term, None)


def msat_term_is_bv_ror(env, term):
    "returns a tuple (res, amount)"
    return _msat_term_is_bv_ror(env, term, None)


def msat_named_list_from_smtlib2(env, data):
    ret = _msat_named_list_from_smtlib2(env, data, 0, 0, 0)
    if ret is not None:
        ret = [p[0] for p in ret], [p[1] for p in ret]
    return ret

def msat_named_list_from_smtlib2_file(env, f):
    return msat_named_list_from_smtlib2(env, f.read())


def msat_named_list_to_smtlib2(env, names, terms):
    names = [_enc(n) for n in names]
    return _msat_named_list_to_smtlib2(env, len(names), names, terms)


def msat_named_list_to_smtlib2_file(env, names, terms, out):
    names = [_enc(n) for n in names]
    data = msat_named_list_to_smtlib2(env, names, terms)
    out.write(data)


def msat_annotated_list_from_smtlib2(env, data):
    return _msat_annotated_list_from_smtlib2(env, data, 0, 0, 0)


def msat_annotated_list_from_smtlib2_file(env, f):
    return msat_annotated_list_from_smtlib2(env, f.read())


def msat_annotated_list_to_smtlib2(env, terms, annots):
    annots = [_enc(n) for n in annots]
    return _msat_annotated_list_to_smtlib2(env, len(terms), terms, annots)


def msat_annotated_list_to_smtlib2_file(env, terms, annots, out):
    annots = [_enc(n) for n in annots]
    data = msat_annotated_list_to_smtlib2(env, terms, annots)
    out.write(data)


def msat_gc_env(env, tokeep):
    return _msat_gc_env(env, tokeep, len(tokeep))


# add suitable __eq__, __hash__ and __str__ methods to the msat classes

def _term_hash(self):
    return msat_term_id(self)
msat_term.__hash__ = _term_hash
del _term_hash

def _term_eq(self, other):
    return isinstance(other, msat_term) and msat_term_id(self) == msat_term_id(other)
msat_term.__eq__ = _term_eq
del _term_eq

def _term_str(self):
    if MSAT_ERROR_TERM(self): return "<ERROR>"
    return msat_term_repr(self)
msat_term.__str__ = _term_str
del _term_str

def _decl_hash(self):
    return msat_decl_id(self)
msat_decl.__hash__ = _decl_hash
del _decl_hash

def _decl_eq(self, other):
    return isinstance(other, msat_decl) and msat_decl_id(self) == msat_decl_id(other)
msat_decl.__eq__ = _decl_eq
del _decl_eq

def msat_exist_elim(env, formula, to_elim, algo,
                    toplevel_propagation=True,
                    boolean_simplifications=True,
                    remove_redundant_constraints=True):
    opts = msat_exist_elim_options()
    opts.toplevel_propagation = toplevel_propagation
    opts.boolean_simplifications = boolean_simplifications
    opts.remove_redundant_constraints = remove_redundant_constraints
    return _msat_exist_elim(env, formula, to_elim, len(to_elim), algo, opts)

def msat_exist_elim_model(env, formula, to_elim, model, model_values=None):
    if model_values is None:
        model_vars, model_values = [], []
        for (k, v) in getattr(model, 'iteritems', getattr(model, 'items'))():
            model_vars.append(k)
            model_values.append(v)
    else:
        model_vars = model
    return _msat_exist_elim_model(env, formula, to_elim, len(to_elim),
                                  model_vars, model_values, len(model_vars))

def msat_apply_substitution(env, term, to_subst, values=None):
    if values is None:
        m = to_subst
        to_subst = []
        values = []
        if hasattr(m, 'items'):
            for (k, v) in getattr(m, 'iteritems', m.items)():
                to_subst.append(k)
                values.append(v)
        else:
            ## assume m is a sequence of (k, v) pairs
            for (k, v) in m:
                to_subst.append(k)
                values.append(v)
    return _msat_apply_substitution(env, term, len(to_subst), to_subst, values)

def msat_simplify(env, formula, to_protect):
    return _msat_simplify(env, formula, to_protect,
                          0 if to_protect is None else len(to_protect))


def msat_aig_encode(mgr, term):
    return _msat_aig_encode(mgr, term, 0)


MSAT_TAG_FP_TO_BV = MSAT_TAG_FP_TO_SBV        

%}

#if MSATIC3
%pythoncode "msatic3_pythoncode.py"
#endif /* MSATIC3 */

#if OPTIMATHSAT
%pythoncode "python_code.py"
#endif /* OPTIMATHSAT */
