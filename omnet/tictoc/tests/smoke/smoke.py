import subprocess
import shlex
import re
import os
import sys
import csv
import time
import collections
import glob
import unittest


ROOT_PATH = os.path.join('..', '..')  # path to the project root
SHARED_LIBRARY = None  # None if testing against an executable, or library name
EXECUTABLE = 'tictoc'  # None if testing against a library, or executable name
PATH_SEPARATOR = ";" if sys.platform == 'win32' else ':'
PWD = os.path.dirname(os.path.abspath(__file__))  # path of this file
NED_PATHS = ['.',]
CPU_TIME_LIMIT = "5ms"
RESULTS_DIR = 'results'
LOG_FILE_NAME = 'smoke.log'


def which_executable():
    if SHARED_LIBRARY and not EXECUTABLE:
        return 'opp_run'
    elif not SHARED_LIBRARY and EXECUTABLE:
        return os.path.join('.', EXECUTABLE)
    else:
        raise Exception(
            f'ambiguous executable, both SHARED_LIBRARY="{SHARED_LIBRARY}" and '
            + f'EXECUTABLE="{EXECUTABLE}" are given')


SimResult = collections.namedtuple('SimResult', (
    'exitcode', 'command', 'path', 'error_msg', 'simulated_time', 
    'elapsed_time', 'cpu_time', 'cpu_time_limit_reached', 'num_events',
    ))


def simulate(path, config_name, cpu_time_limit):
    # Building command arguments
    args = [
        which_executable(),
        '-u Cmdenv', 
        '--cmdenv-express-mode=false', 
        '--vector-recording=false', 
        '--scalar-recording=false', 
        f'--result-dir={os.path.join(PWD, "results")}',
        f'-c {config_name}',
        f'-n {PATH_SEPARATOR.join(NED_PATHS)}',
        f'--cpu-time-limit={CPU_TIME_LIMIT}',
    ]
    command = " ".join(args)
    path = os.path.join(ROOT_PATH, path)

    # Running the simulation
    start_time = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=path,
        shell=True,
        stdout=subprocess.PIPE,    # we wouldn't like to flood the console
        stderr=subprocess.STDOUT,  # join both streams
        universal_newlines=True,   # we don't want to decode the stream
    )
    out = process.communicate()[0]
    elapsed_time = time.perf_counter() - start_time

    # Extracting and building the simulation results
    cpu_time_limit_reached = False
    num_events = 0
    simulated_time = "0s"
    error_lines = re.findall('^<!>.*', out, re.M)
    for line in error_lines:
        if re.search('CPU time limit reached', line):
            cpu_time_limit_reached = True
        m = re.search("t=([0-9]*(\\.[0-9]+)?)s, event #([0-9]+)", line)
        if m:
            simulated_time = m.group(1)
            num_events = int(m.group(3))
    
    result = SimResult(
        exitcode=process.returncode, 
        command=" ".join(args),
        path=path,
        error_msg="\n".join(error_lines),
        simulated_time=simulated_time,
        cpu_time=cpu_time_limit,
        cpu_time_limit_reached=cpu_time_limit_reached,
        num_events=num_events,
        elapsed_time=elapsed_time,
    )
    
    # Recording the log file
    with open(os.path.join(LOG_FILE_NAME), "a") as f:
        f.write(f'$ cd {result.path}\n')
        f.write(f'$ {result.command}\n\n')
        f.write(result.error_msg)
        f.write('\n\n')
        f.write(f'* simulated time: {result.simulated_time}\n')
        f.write(f'* cpu time limit: {cpu_time_limit}')
        if not result.cpu_time_limit_reached:
            f.write(' -- not reached')
        f.write('\n')
        f.write(f'* elapsed time  : {result.elapsed_time}\n')
        f.write(f'* num of events : {result.num_events}\n')
        f.write(f'* exit code     : {result.exitcode}\n')
        f.write('\n')
        if result.exitcode:
            f.write('[-] FAILURE\n\n')
        else:
            f.write('[+] SUCCESS\n\n')

    return result


def string_to_class_name(string):
    string = string.strip()
    string = re.sub('[#\-$@\!\?\.,;]', ' ', string)
    string = ''.join(char for char in string.title() if not char.isspace())
    return string


def string_to_method_name(string):
    string = string.strip()
    string = re.sub('[#\-$@,;\.]', '_', string)
    string = re.sub('[\!\?]', '', string)
    return string


SimSpec = collections.namedtuple(
    'SimSpec', 
    ('path', 'config_name', 'args', 'file_name', 'line_number', 'line')
)


def parse_csv(file_name):

    def filter_comments(lines):
        comment_regex = re.compile(' *#.*$')
        endline_regex = re.compile('\\n')
        for index, line in enumerate(lines):
            line = comment_regex.sub('', line)
            line = endline_regex.sub('', line)
            if line:
                yield index + 1, line

    with open(file_name) as file:
        for number, line in filter_comments(file):
            path, config_name, args = list(csv.reader([line]))[0]
            path = path.strip()
            config_name = config_name.strip()
            args = args.strip()
            yield SimSpec(path, config_name, args, file_name, number, line)


def _build_test_method(spec):
    def test_method(self):
        with open(LOG_FILE_NAME, 'a') as log_file:
            log_file.write('#' * 80 + '\n')
            log_file.write(
                f'# {spec.file_name}:{spec.line_number}: {spec.line}\n'
            )
            log_file.write('#' * 80 + '\n')

        result = simulate(spec.path, spec.config_name, CPU_TIME_LIMIT)
        
        self.assertEqual(
            result.exitcode, 0, 
            f"error at {spec.file_name}:{spec.line_number}, "
            f"config '{spec.config_name}'"
        )
    test_method.__name__ = 'test_' + string_to_method_name(spec.config_name)
    return test_method


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()

    # Open log file to clear it    
    with open(LOG_FILE_NAME, 'w') as dummy_file:
        pass

    # Find all CSV files        
    csv_files = glob.glob('*.csv')

    # Build TestCase for each CSV-file
    for file_name in csv_files:
        specs = parse_csv(file_name)
        cname = string_to_class_name('Test-' + file_name)
        testcase = type(cname, (unittest.TestCase, ), {})
        for spec in specs:
            method = _build_test_method(spec)
            setattr(testcase, method.__name__, method)
        tests = loader.loadTestsFromTestCase(testcase)
        suite.addTests(tests)
    
    # Return the suite
    return suite


if __name__ == '__main__':
    unittest.main()
