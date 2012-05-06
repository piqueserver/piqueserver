rd /s /q build
md build
del /s /q *.pyc;*.pyd
python build.py build_ext -f --inplace -c mingw32
pushd enet
python setup.py build_ext -f --inplace -c mingw32
popd