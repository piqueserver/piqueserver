import pytest

from collections import defaultdict, Counter
import sys
import inspect
import re
import os
import shutil
from rcfile import rcfile
from fnmatch import fnmatch
from itertools import chain
from termcolor import colored

class CoverageData(object):
    """docstring for CoverageData."""
    def __init__(self, cwd):
        super(CoverageData, self).__init__()
        self.cwd = cwd
        self.collector = defaultdict(set)
        self.sources = set()
        self.filtered_sources = set()
        self.rc = rcfile("robocov")
        self.print_code = False

    def compute_filtered_sources(self):
        sources = self.sources
        omit = self.rc["omit"].strip().split("\n")
        filtered = {path for path in sources
                    if not any(fnmatch(path, pattern) for pattern in omit)}
        self.filtered_sources = filtered

_robocov = CoverageData(os.getcwd())

def trace_calls(frame, event, arg):
    co = frame.f_code
    function_line_no = frame.f_lineno
    prev_line_no = frame.f_lineno
    cur_filename = co.co_filename

    def trace_lines(frame2, event2, arg):
        nonlocal prev_line_no
        nonlocal cur_filename
        nonlocal function_line_no
        global _robocov
        if event2 == "return":
            _robocov.collector[cur_filename].add((prev_line_no, function_line_no))
            return
        if event2 != 'line':
            return
        co = frame2.f_code
        line_no = frame2.f_lineno
        _robocov.collector[cur_filename].add((prev_line_no, line_no))
        prev_line_no = line_no

    try:
        source_file = inspect.getsourcefile(co)
        if source_file in _robocov.filtered_sources:
            return trace_lines
    except:
        return

def print_colored(line, success):
    if success:
        print(colored(line, "green"))
    else:
        print(colored(line, "red"))

def pytest_terminal_summary(terminalreporter, exitstatus):
    global _robocov
    if not _robocov.enable:
        return
    print()
    terminal_width = shutil.get_terminal_size(fallback=(80, 20)).columns
    collected = dict(_robocov.collector)
    sources = _robocov.filtered_sources
    total_branches = 0
    total_branches_covered = 0
    cwd = _robocov.cwd
    for sourcefilename in sources:
        if sourcefilename not in collected:
            continue
        from_lines = Counter(prev for (prev, curr) in collected[sourcefilename])
        to_lines = Counter(curr for (prev, curr) in collected[sourcefilename])
        allLines = from_lines | to_lines
        sourcefile = open(sourcefilename).read().split("\n")
        branchlines = {i for i, line in enumerate(sourcefile) if re.search("^\s*(while)|(if)|(for) ", line)}
        covered_branches = 0
        adjusted_path = "." + str(sourcefilename)[len(cwd):]
        output_data = []
        print(adjusted_path.ljust(60), end="")
        for i, line in enumerate(sourcefile):
            line_number = i + 1
            success = False
            if len(line.strip()) == 0:
                success = True
            elif line.startswith("import") or line.startswith("from"):
                success = True
            elif line_number in allLines:
                if i in branchlines:
                    if from_lines[line_number] > 1:
                        success = True
                        covered_branches += 1
                    else:
                        success = False
                        line += " <- only one branch covered"
                else:
                    success = True
            output_data.append((line, success))
        branch_amount = len(branchlines)
        total_branches += branch_amount
        total_branches_covered += covered_branches
        print(colored(f"[{covered_branches}/{branch_amount}] ".rjust(terminal_width-60), "cyan"))
        if _robocov.print_code:
            for line, success in output_data:
                print_colored(line, success)
            print()
            print()
    print()
    print(f"Total branch coverage {total_branches_covered}/{total_branches}" )
def pytest_addoption(parser):
    parser.addoption("--robocov", action="store_true", default=False)
    parser.addoption("--roboprint", action="store_true", default=False)

def pytest_configure(config):
    global _robocov
    _robocov.enable = config.getoption("--robocov")
    _robocov.print_code = config.getoption("--roboprint")
    print(_robocov.enable)

def pytest_runtestloop(session):
    global _robocov
    if not _robocov.enable:
        return
    _robocov.compute_filtered_sources()
    sys.settrace(trace_calls)

def pytest_collect_file(path, parent):
    global _robocov
    if str(path).endswith(".py"):
        _robocov.sources.add(path)
