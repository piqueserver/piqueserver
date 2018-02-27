import unittest
import tempfile
import shutil
import filecmp
import time
import sys
from os.path import join, isfile, getmtime
from unittest.mock import patch, MagicMock, mock_open
from piqueserver.run import copytree, main


def _setup_dir():
    return tempfile.mkdtemp(), tempfile.mkdtemp()


def _rm_dir(src_dir, dst_dir):
    shutil.rmtree(src_dir)
    shutil.rmtree(dst_dir)


def _write(fpath, body):
    with open(fpath, "w+") as f:
        f.write(body)


class TestMain(unittest.TestCase):
    @patch("piqueserver.run.argparse")
    @patch("piqueserver.run.copy_config", return_value=0)
    @patch("piqueserver.run.update_geoip", return_value=0)
    def test_main_0(self, argparse, copy_config, update_geoip):
        """If the tasks copy_config and update_geoip are performed
        then the server should not be run.
        """
        with patch.object(sys, 'version_info') as v_info:
            v_info.major = 3
            v_info.minor = 6
            with patch("piqueserver.server.run") as mock:
                main()
                assert not mock.called

    @patch("piqueserver.run.SUPPORTED_PYTHONS", return_value=[])
    @patch("piqueserver.run.argparse")
    @patch("piqueserver.run.copy_config", return_value=0)
    @patch("piqueserver.run.update_geoip", return_value=0)
    def test_main_1(self, SUPPORTED_PYTHONS, argparse, copy_config, 
                    update_geoip):
        """If a python version is used that is not on the
        SUPPORTED_PYTHONS list then main() should output a
        warning.
        """
        from io import StringIO
        saved_stdout = sys.stdout
        try:
            out = StringIO()
            sys.stdout = out
            main()
            output = out.getvalue().strip()
            self.assertIn('Warning: you are running on an unsupported Python version.\n'
                      'The server may not run correctly.\n'
                      'Please see https://github.com/piqueserver/piqueserver/wiki/Supported-Environments '
                      'for more information.', output)
        finally:
            sys.stdout = saved_stdout

    @patch("piqueserver.run.argparse")
    @patch("piqueserver.run.copy_config", return_value=0)
    @patch("piqueserver.run.update_geoip", return_value=0)
    def test_main_2(self, argparse, copy_config,
                    update_geoip):
        """If python 2.7 is used then main() should output
        a text warning about deprecation.
        """
        with patch.object(sys, 'version_info') as v_info:
            v_info.major = 2
            v_info.minor = 7
            from io import StringIO
            saved_stdout = sys.stdout
            try:
                out = StringIO()
                sys.stdout = out
                main()
                output = out.getvalue().strip()
                self.assertIn('You are running piqueserver on Python 2.\n'
                              'This will be deprecated soon and it is recommended to upgrade to Python 3.\n'
                              'Please see https://github.com/piqueserver/piqueserver/wiki/Supported-Environments for more information.', output)
            finally:
                sys.stdout = saved_stdout

    def test_main_3(self):
        """If the config is correct and no tasks are performed,
        the server should be run.
        """
        with patch('argparse.ArgumentParser') as mock:
            arg_parser = mock.return_value
            args = MagicMock()
            args.copy_config = False
            args.update_geoip = False
            args.config_file = "asdioasod.json"
            args.json_parameters = False
            arg_parser.parse_args.return_value = args
            with patch("builtins.open", mock_open(read_data=MagicMock())):
                with patch("piqueserver.run.config") as mock:
                    mock.load_from_file.return_value = 0
                    with patch("piqueserver.server.run") as mock2:
                        main()
                        assert mock2.called


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
