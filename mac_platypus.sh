nicotine=$1/Contents/Resources/nicotine.py
home=$1/Contents/Frameworks/Python.framework/Versions/2.6
python=$home/bin/python
export PYTHONHOME=$home
$python -OO $nicotine
