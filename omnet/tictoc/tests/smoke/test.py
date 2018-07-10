import subprocess
import shlex
import re
import os
import sys


ROOT_PATH = os.path.join('..', '..')
SHARED_LIBRARY = None
EXECUTABLE = 'tictoc'
PATH_SEPARATOR = ";" if sys.platform == 'win32' else ':'
PWD = os.path.dirname(os.path.abspath(__file__))


def which_executable():
    if SHARED_LIBRARY and not EXECUTABLE:
        return 'opp_run'
    elif not SHARED_LIBRARY and EXECUTABLE:
        return os.path.join('.', EXECUTABLE)
    else:
        raise Exception(
            f'ambiguous executable, both SHARED_LIBRARY="{SHARED_LIBRARY}" and '
            + f'EXECUTABLE="{EXECUTABLE}" are given')


def build_command(config_name, ned_paths, cpu_time_limit):
    fixed_args = [
        '-u Cmdenv', 
        '-r 0', 
        '--cmdenv-express-mode=false',
        '--vector-recording=false', 
        '--scalar-recording=false',
        f'--result-dir={os.path.join(PWD, "results")}',
    ]
    user_args = [
        f'-c {config_name}',
        f'-n {PATH_SEPARATOR.join(ned_paths)}',
        f'--cpu-time-limit={cpu_time_limit}',
    ]
    args = []
    args.extend(fixed_args)
    args.extend(user_args)
    if SHARED_LIBRARY:
        args.append(f'-l {SHARED_LIBRARY}')
    return which_executable() + " " + " ".join(args)
    

if __name__ == '__main__':
    command = build_command('TutorialNetwork', ('.', ), "5ms")
    print(command)
    args = shlex.split(command)

    process = subprocess.Popen(
        args,
        cwd=ROOT_PATH,
        stdout=subprocess.PIPE,    # we wouldn't like to flood the console
        stderr=subprocess.STDOUT,  # join both streams
        universal_newlines=True,   # we don't want to decode the stream
    )
    out = process.communicate()[0]
    if process.returncode:
        print(out)

    print('returncode: ', process.returncode)
