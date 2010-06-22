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

ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)
if sys.platform == 'win32' and sys.version_info > (2, 6):
   # 2.6's distutils.msvc9compiler can raise an IOError when failing to
   # find the compiler
   ext_errors += (IOError,)


class BuildFailed(Exception):
    pass


class ve_build_ext(build_ext):
    """This class allows C extension building to fail."""

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError, x:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors, x:
            raise BuildFailed()


description = open(os.path.join(os.path.dirname(__file__), 'README')).read()


def run_setup(with_binary):
    features = {}
    if with_binary:
        features['speedups'] = speedups
    setup(
        name='MarkupSafe',
        version='0.9',
        url='http://dev.pocoo.org/',
        license='BSD',
        author='Armin Ronacher',
        author_email='armin.ronacher@active-4.com',
        description='Implements a XML/HTML/XHTML Markup safe string for Python',
        long_description=description,
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
        include_package_data=True,
        cmdclass={'build_ext': ve_build_ext},
        features=features
    )


try:
    run_setup(True)
except BuildFailed:
    LINE = '=' * 74
    BUILD_EXT_WARNING = 'WARNING: The C extension could not be compiled, speedups are not enabled.'

    print LINE
    print BUILD_EXT_WARNING
    print 'Failure information, if any, is above.'
    print 'Retrying the build without the C extension now.'
    print

    run_setup(False)

    print LINE
    print BUILD_EXT_WARNING
    print 'Plain-Python installation succeeded.'
    print LINE
