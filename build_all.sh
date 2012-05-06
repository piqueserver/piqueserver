find . -type f -name "*.so" -o -name "*.pyc" -o -name "*.pyd" | xargs rm -f
rm -rf build/*
python build.py build_ext -f --inplace
cd enet
python setup.py build_ext -f --inplace
