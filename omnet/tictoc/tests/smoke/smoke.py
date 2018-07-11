import subprocess
import shlex
import re
import os
import sys
import csv
import time
import collections
import glob
import multiprocessing
import threading
import argparse
import unittest
import copy
import io


ROOT_PATH = os.path.join('..', '..')  # path to the project root
SHARED_LIBRARY = None  # None if testing against an executable, or library name
EXECUTABLE = 'tictoc'  # None if testing against a library, or executable name
PATH_SEPARATOR = ";" if sys.platform == 'win32' else ':'
PWD = os.path.dirname(os.path.abspath(__file__))  # path of this file
NED_PATHS = ['.',]
CPU_TIME_LIMIT = "10s"
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


SimResult = collections.namedtuple(
    'SimResult', 
    (
        'exitcode', 'command', 'path', 'error_msg', 'simulated_time', 
        'elapsed_time', 'cpu_time', 'cpu_time_limit_reached', 'num_events',
    )
)


SimSpec = collections.namedtuple(
    'SimSpec', 
    ('path', 'config_name', 'args', 'file_name', 'line_number', 'line')
)


def simulate(spec, cpu_time_limit, log_file):
    # Building command arguments
    args = [
        which_executable(),
        '-u Cmdenv', 
        '--cmdenv-express-mode=false', 
        '--vector-recording=false', 
        '--scalar-recording=false', 
        f'--result-dir={os.path.join(PWD, RESULTS_DIR)}',
        f'-c {spec.config_name}',
        f'-n {PATH_SEPARATOR.join(NED_PATHS)}',
        f'--cpu-time-limit={cpu_time_limit}',
    ]
    command = " ".join(args)
    path = os.path.join(ROOT_PATH, spec.path)

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
    with open(os.path.join(log_file), "a") as f:
        f.write('#' * 80 + '\n')
        f.write(f'# {spec.file_name}:{spec.line_number}: {spec.line}\n')
        f.write('#' * 80 + '\n')
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


def _build_test_method(spec, cpu_time_limit, log_file):
    def test_method(self):
        result = simulate(spec, cpu_time_limit, log_file)
        self.assertEqual(
            result.exitcode, 0, 
            f"error at {spec.file_name}:{spec.line_number}, "
            f"config '{spec.config_name}'"
        )
    test_method.__name__ = 'test_' + string_to_method_name(spec.config_name)
    return test_method


class ThreadSafeIter:
    """Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    @author: Andras Varga
    """
    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def __next__(self):
        with self.lock:
            return next(self.it)


class ThreadedTestSuite(unittest.BaseTestSuite):
    """ runs toplevel tests in n threads
    @author: Andras Varga
    """

    # How many test process at the time.
    thread_count = multiprocessing.cpu_count()

    def run(self, result):
        it = ThreadSafeIter(self.__iter__())

        result.buffered = True

        threads = []

        for i in range(self.thread_count):
            # Create self.thread_count number of threads that together will
            # cooperate removing every ip in the list. Each thread will do the
            # job as fast as it can.
            t = threading.Thread(target=self.runThread, args=(result, it))
            t.daemon = True
            t.start()
            threads.append(t)

        # Wait until all the threads are done. .join() is blocking.
        #for t in threads:
        #    t.join()
        runApp = True
        while runApp and threading.active_count() > 1:
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                runApp = False
        return result

    def runThread(self, result, it):
        tresult = result.startThread()
        for test in it:
            if result.shouldStop:
                break
            test(tresult)
        tresult.stopThread()


class ThreadedTestResult(unittest.TestResult):
    """TestResult with threads
    @author: Andras Varga
    """

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        super(ThreadedTestResult, self).__init__()
        self.parent = None
        self.lock = threading.Lock()

    def startThread(self):
        ret = copy.copy(self)
        ret.parent = self
        return ret

    def stop():
        super(ThreadedTestResult, self).stop()
        if self.parent:
            self.parent.stop()

    def stopThread(self):
        if self.parent == None:
            return 0
        self.parent.testsRun += self.testsRun
        return 1

    def startTest(self, test):
        "Called when the given test is about to be run"
        super(ThreadedTestResult, self).startTest(test)
        self.oldstream = self.stream
        self.stream = io.StringIO()

    def stopTest(self, test):
        """Called when the given test has been run"""
        super(ThreadedTestResult, self).stopTest(test)
        out = self.stream.getvalue()
        with self.lock:
            self.stream = self.oldstream
            self.stream.write(out)


#
# Copy/paste of TextTestResult, with minor modifications in the output:
# we want to print the error text after ERROR and FAIL, but we don't want
# to print stack traces.
#
class SimulationTextTestResult(ThreadedTestResult):
    """A test result class that can print formatted text results to a stream.
    Used by TextTestRunner.
    @author: Andras Varga
    """
    def __init__(self, stream, descriptions, verbosity):
        super(SimulationTextTestResult, self).__init__()
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions

    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)

    def startTest(self, test):
        super(SimulationTextTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super(SimulationTextTestResult, self).addSuccess(test)
        if self.showAll:
            self.stream.write(": PASS\n")
        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    def addError(self, test, err):
        # modified
        super(SimulationTextTestResult, self).addError(test, err)
        self.errors[-1] = (test, err[1])  # super class method inserts stack trace; we don't need that, so overwrite it
        if self.showAll:
            (cause, detail) = self._splitMsg(err[1])
            self.stream.write(": ERROR (%s)\n" % cause)
            if detail:
                self.stream.write(detail)
                self.stream.write("\n")
        elif self.dots:
            self.stream.write('E')
            self.stream.flush()

    def addFailure(self, test, err):
        # modified
        super(SimulationTextTestResult, self).addFailure(test, err)
        self.failures[-1] = (test, err[1])  # super class method inserts stack trace; we don't need that, so overwrite it
        if self.showAll:
            (cause, detail) = self._splitMsg(err[1])
            self.stream.write(": FAIL (%s)\n" % cause)
            if detail:
                self.stream.write(detail)
                self.stream.write("\n")
        elif self.dots:
            self.stream.write('F')
            self.stream.flush()

    def addSkip(self, test, reason):
        super(SimulationTextTestResult, self).addSkip(test, reason)
        if self.showAll:
            self.stream.write(": skipped {0!r}".format(reason))
            self.stream.write("\n")
        elif self.dots:
            self.stream.write("s")
            self.stream.flush()

    def addExpectedFailure(self, test, err):
        super(SimulationTextTestResult, self).addExpectedFailure(test, err)
        if self.showAll:
            self.stream.write(":FAIL (expected)\n")
        elif self.dots:
            self.stream.write("x")
            self.stream.flush()

    def addUnexpectedSuccess(self, test):
        super(SimulationTextTestResult, self).addUnexpectedSuccess(test)
        if self.showAll:
            self.stream.write(": PASS (unexpected)\n")
        elif self.dots:
            self.stream.write("u")
            self.stream.flush()

    def printErrors(self):
        # modified
        if self.dots or self.showAll:
            self.stream.write("\n")
        self.printErrorList('Errors', self.errors)
        self.printErrorList('Failures', self.failures)

    def printErrorList(self, flavour, errors):
        # modified
        if errors:
            self.stream.writeln("%s:" % flavour)
        for test, err in errors:
            self.stream.write("  %s (%s)\n" % (self.getDescription(test), self._splitMsg(err)[0]))

    def _splitMsg(self, msg):
        cause = str(msg)
        detail = None
        if cause.count(': '):
            (cause, detail) = cause.split(': ',1)
        return (cause, detail)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run the fingerprint tests specified in the input files.'
    )
    parser.add_argument(
        'csvs', 
        nargs='*', 
        help=('CSV files that contain the tests to run (default: *.csv). ' +
              'Expected CSV file columns: path, config name, args'))
    parser.add_argument(
        '-s', '--cpu-time-limit', 
        default=CPU_TIME_LIMIT, 
        dest='cpu_time_limit', 
        help='cpu time limit (default: 6s)'
    )
    parser.add_argument(
        '-t', '--threads', 
        type=int,
        dest='num_threads',
        default=multiprocessing.cpu_count(), 
        help=('number of parallel threads (default: number of CPUs, ' +
              f'currently {multiprocessing.cpu_count()})')
    )
    parser.add_argument(
        '-l', '--logfile', 
        default=LOG_FILE_NAME, 
        dest='log_file', 
        help=f'name of logfile (default: {LOG_FILE_NAME})'
    )
    args = parser.parse_args()
    csv_files = glob.glob('*.csv') if not args.csvs else args.csvs

    with open(args.log_file, "w") as dummy_file:
        pass

    loader = unittest.TestLoader()
    suite = ThreadedTestSuite()
    suite.thread_count = args.num_threads
    for csv_file in csv_files:
        specs = parse_csv(csv_file)
        cname = string_to_class_name('Test-' + csv_file)
        testcase = type(cname, (unittest.TestCase, ), {})
        for spec in specs:
            fn = _build_test_method(spec, args.cpu_time_limit, args.log_file)
            setattr(testcase, fn.__name__, fn)
        tests = loader.loadTestsFromTestCase(testcase)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(
        stream=sys.stdout, 
        verbosity=9, 
        resultclass=SimulationTextTestResult
    )

    runner.run(suite)

    print('')
    print(f"Log has been saved to {args.log_file}")
