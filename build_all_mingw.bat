python build.py build_ext -f --inplace -c mingw32
pushd enet
python setup.py build_ext -f --inplace -c mingw32
popd