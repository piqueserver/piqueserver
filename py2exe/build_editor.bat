rmdir /S /Q dist
python build_editor.py py2exe
python post_build_editor.py