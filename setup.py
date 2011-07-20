import os
import sys
from setuptools import setup, Extension, Feature
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError, DistutilsExecError, \
    DistutilsPlatformError

# fail safe compilation shamelessly stolen from the simplejson
# setup.py file.  Original author: Bob Ippolito


speedups = Feature(
    'optional C speed-enhancement module',
    standard=True,
    ext_modules = [
        Extension('markupsafe._speedups', ['markupsafe/_speedups.c']),
    ],
)

is_jython = 'java' in sys.platform

try:
    import __pypy__
    is_pypy = True
except ImportError:
    is_pypy = False

if is_pypy or is_jython:
    # Jython cannot build the C optimizations, while on PyPy they are
    # anti-optimizations (the C extension compatibility layer is known-slow,
    # and defeats JIT opportunities).
    extra = {}
else:
    extra = {'features':{'speedups':speedups}}

ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)
if sys.platform == 'win32' and sys.version_info > (2, 6):
   # 2.6's distutils.msvc9compiler can raise an IOError when failing to
   # find the compiler
    ext_errors += (IOError,)


if sys.version_info >= (3, 0):
    extra['use_2to3'] = True

class optional_build_ext(build_ext):
    """This class subclasses build_ext and allows
       the building of C extensions to fail.
    """
    def run(self):
        try:
            build_ext.run(self)
        
        except DistutilsPlatformError:
            # The sys.exc_info()[1] is to preserve compatibility with both
            # Python 2.5 and 3.x, which is needed in setup.py.
            self._unavailable(sys.exc_info()[1])

    def build_extension(self, ext):
       try:
           build_ext.build_extension(self, ext)
           
       except ext_errors:
           # The sys.exc_info()[1] is to preserve compatibility with both
           # Python 2.5 and 3.x, which is needed in setup.py.
           self._unavailable(sys.exc_info()[1])

    def _unavailable(self, e):
        # Write directly to stderr to preserve compatibility with both
        # Python 2.5 and 3.x, which is needed in setup.py.
        sys.stderr.write('*' * 80 + '\n')
        sys.stderr.write("""WARNING:

        An optional code optimization (C extension) could not be compiled.

        Optimizations for this package will not be available!
        
        """)
        sys.stderr.write(str(e) + '\n')
        sys.stderr.write('*' * 80 + '\n')

def echo(msg=''):
    sys.stdout.write(msg + '\n')


readme = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()


setup(
   name='MarkupSafe',
   version='0.13',
   url='http://dev.pocoo.org/',
   license='BSD',
   author='Armin Ronacher',
   author_email='armin.ronacher@active-4.com',
   description='Implements a XML/HTML/XHTML Markup safe string for Python',
   long_description=readme,
   zip_safe=False,
   classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Web Environment',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: BSD License',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      'Topic :: Software Development :: Libraries :: Python Modules',
      'Topic :: Text Processing :: Markup :: HTML'
      ],
   packages=['markupsafe'],
   test_suite='markupsafe.tests.suite',
   include_package_data=True,
   cmdclass={'build_ext': optional_build_ext},
   **extra
)

