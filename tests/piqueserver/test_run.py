import unittest
import tempfile
import shutil
import filecmp
import time
from os.path import join, isfile, getmtime

from piqueserver.run import copytree


def _setup_dir():
    return tempfile.mkdtemp(), tempfile.mkdtemp()


def _rm_dir(src_dir, dst_dir):
    shutil.rmtree(src_dir)
    shutil.rmtree(dst_dir)


def _write(fpath, body):
    with open(fpath, "w+") as f:
        f.write(body)


class TestCopytree(unittest.TestCase):
    def test_dst_noexist(self):
        """Should copy even if dst dir. doesn't exist"""
        src_dir, dst_dir = tempfile.mkdtemp(), join(tempfile.gettempdir(), "pique_noexist_dir")
        src_file, dst_file = join(src_dir, "test"), join(dst_dir, "test")

        _write(src_file, "Test")
        copytree(src_dir, dst_dir)

        self.assertTrue(isfile(dst_file))
        _rm_dir(src_dir, dst_dir)

    def test_file_noexist(self):
        """Should copy file if it doesn't exist"""
        src_dir, dst_dir = _setup_dir()
        src_file, dst_file = join(src_dir, "test"), join(dst_dir, "test")

        _write(src_file, "Test")
        copytree(src_dir, dst_dir)

        self.assertTrue(isfile(dst_file))
        _rm_dir(src_dir, dst_dir)

    def test_files_differ(self):
        """Should backup if src/dst files differ"""
        src_dir, dst_dir = _setup_dir()
        src_file, dst_file, bak_file = join(src_dir, "test"), join(dst_dir, "test"), join(dst_dir, "test.bak")

        _write(src_file, "Test!")
        _write(dst_file, "Test")
        copytree(src_dir, dst_dir)

        self.assertTrue(filecmp.cmp(src_file, dst_file))
        self.assertTrue(isfile(bak_file))
        self.assertFalse(filecmp.cmp(src_file, bak_file))
        _rm_dir(src_dir, dst_dir)

    def test_same(self):
        """
        Should not copy if src/dst files have same content.
        """
        src_dir, dst_dir = _setup_dir()
        src_file, dst_file = join(src_dir, "test"), join(dst_dir, "test")

        _write(src_file, "test")
        time.sleep(1)
        _write(dst_file, "test")

        t0 = getmtime(join(dst_dir, "test"))
        copytree(src_dir, dst_dir)
        t1 = getmtime(join(dst_dir, "test"))

        self.assertEqual(t0, t1)
        _rm_dir(src_dir, dst_dir)
