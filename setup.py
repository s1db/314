from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
import os
import sys

# Define the ABC extension
# We assume libabc.a is built in src/bindings/abc_lib
abc_lib_dir = os.path.abspath("src/bindings/abc_lib")
abc_include_dir = os.path.join(abc_lib_dir, "src")

extensions = [
    Extension(
        "src.bindings.abc_wrapper",
        sources=["src/bindings/abc_wrapper.pyx"],
        include_dirs=[abc_include_dir],
        library_dirs=[abc_lib_dir],
        libraries=["abc", "m", "dl", "pthread"],
        extra_compile_args=["-fPIC", "-O3", "-Wno-unused-function", "-Wno-unused-result", "-Wno-narrowing"],
        define_macros=[('ABC_USE_STDINT_H', '1')],
        language="c++", # ABC is C but often linked with C++ if needed, though pure C is fine. keeping flexible.
    )
]

setup(
    name="314",
    version="0.1.0",
    packages=find_packages(),
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}, annotate=True),
    install_requires=[
        "numpy>=2.4.2",
        "pycmsgen>=6.1.1",
        "scikit-learn>=1.8.0",
        "Cython",
    ],
    zip_safe=False,
)
