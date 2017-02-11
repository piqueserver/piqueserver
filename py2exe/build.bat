rmdir /S /Q dist
python build.py py2exe
python post_build.py