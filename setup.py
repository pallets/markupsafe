from setuptools import setup, Feature, Extension


setup(
    name='MarkupSafe',
    version='0.9',
    url='http://dev.pocoo.org/',
    license='BSD',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    description='Implements a XML/HTML/XHTML Markup safe string for Python',
    long_description=__doc__,
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
    features={
        'speedups': Feature("optional C speed-enhancements",
            standard=False,
            ext_modules=[
                Extension('markupsafe._speedups', ['markupsafe/_speedups.c'])
            ]
        )
    }
)
