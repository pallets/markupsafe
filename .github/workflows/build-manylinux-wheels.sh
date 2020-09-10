#!/bin/bash
set -e -x

#Requires variable PLAT=[docker name] inside the Docker to be defined
# auditwheel can't detect the Docker name automatically.

mkdir -p /io/temp-wheels

for PYBIN in /opt/python/cp3[6789]*/bin; do
    "${PYBIN}/pip" install -q -U setuptools
    (cd /io/ && "${PYBIN}/python" setup.py -q bdist_wheel -d /io/temp-wheels)
done

"$PYBIN/pip" install -q auditwheel

# Wheels aren't considered manylinux unless they have been through
# auditwheel. Audited wheels go in /io/dist/.
mkdir -p /io/dist/

for whl in /io/temp-wheels/*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w /io/dist/
done
