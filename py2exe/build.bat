rmdir /S /Q dist
python -d build.py py2exe
python post_build.py