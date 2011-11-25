python build.py build_ext --inplace -c mingw32
pushd enet
python setup.py build_ext --inplace -c mingw32
popd