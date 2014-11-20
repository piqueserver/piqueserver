find . -type f -name "*.so" -o -name "*.pyc" -o -name "*.pyd" | xargs rm -f
rm -rf build/*
python2 build.py build_ext -f --inplace
cd enet
python2 setup.py build_ext -f --inplace
