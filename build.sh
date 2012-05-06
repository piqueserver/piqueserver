rm pyspades/navigation.cpp
python build.py build_ext --inplace
cd enet
python setup.py build_ext --inplace
