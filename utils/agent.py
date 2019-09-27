#!/usr/bin/env python3.7

import argparse
import json
import os
import signal
import subprocess
import threading
import time
from multiprocessing import freeze_support, Pool

def __subprocess_run(args):
    try:
        p = subprocess.Popen(args[0], shell=True, preexec_fn=os.setsid, env=args[2])
        p.wait(args[1])
    except:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)

def generate_report(once=False):
    def core():
        report = {
            'compile': None,
            'testcase': {},
        }
        # os.system('make gen_sim_rpt')
        try:
            with open(os.path.join('logs', 'comp_.log'), 'r') as f:
                content = f.read()
                if 'Error' in content:
                    report['compile'] = False
                elif 'up to date' in content:
                    report['compile'] = True
        except:
            pass
        if any(filename.endswith('.err') for filename in os.listdir('logs')):
            filelist = filter(lambda filename: filename.endswith('.err'), os.listdir('logs'))
        else:
            filelist = filter(lambda filename: '-r' in filename and filename.endswith('.log'), os.listdir('logs'))
        for filename in filelist:
            info = filename.replace('_sim', '').replace('.err', '').replace('.log', '').split('-', maxsplit=1)
            testcase = info[0]
            seed = info[1] if len(info) == 2 else ''
            if testcase not in report['testcase']:
                report['testcase'][testcase] = {}
            report['testcase'][testcase][seed] = {
                'passed': None,
                'file': filename,
            }
            try:
                with open(os.path.join('logs', filename), 'r') as f:
                    content = f.read()
                    if args.failed in content:
                        report['testcase'][testcase][seed]['passed'] = False
                    elif args.passed in content:
                        report['testcase'][testcase][seed]['passed'] = True
            except:
                pass
        with open('regression.report', 'w') as f:
            f.write(json.dumps(report, indent=4, ensure_ascii=False))
    
    if once:
        core()
    else:
        global flag
        __flag = False
        while not __flag:
            __flag = flag
            try:
                core()
            except:
                pass
            time.sleep(5)

if __name__ == '__main__':
    freeze_support()

    parser = argparse.ArgumentParser(prog='agent', description='Pango Regression Agent')
    parser.add_argument('-i', '--identifier', nargs='*', help='process identifier')
    parser.add_argument('-e', '--environment', nargs='*', help='environment variable')
    parser.add_argument('-c', '--command', nargs='+', help='parallel command')
    parser.add_argument('-t', '--testcase', nargs='*', help='test case name')
    parser.add_argument('-j', '--job', type=int, default=32, help='number of parallel jobs')
    parser.add_argument('-p', '--passed', default='PASS', help='substring in test case log file standing for passed')
    parser.add_argument('-f', '--failed', default='FAIL', help='substring in test case log file standing for failed')
    parser.add_argument('-r', '--report', action='store_true', help='generate report only')
    parser.add_argument('-n', '--noreport', action='store_true', help='do not generate report')
    parser.add_argument('-o', '--timeout', type=int, default=60, help='timeout for each test case')

    args = parser.parse_args()
    if args.command is None:
        args.command = []
    if args.testcase is None:
        args.testcase = []
    if args.report:
        generate_report(once=True)
    else:
        flag = False
        if not args.noreport:
            threading.Thread(target=generate_report).start()
        if args.environment:
            env = os.environ
            for env_str in args.environment:
                if '=' in env_str:
                    name, value = env_str.split('=', maxsplit=1)
                    env[name] = value
        else:
            env=None
        for command in args.command:
            if '{TESTCASE}' in command:
                with Pool(min(args.job, len(args.testcase))) as p:
                    p.map(__subprocess_run, [(command.replace('{TESTCASE}', testcase), args.timeout * 60, env) for testcase in args.testcase]) # '>/dev/null 2>&1'
                    p.close()
                    p.join()
            else:
                __subprocess_run((command, None, env))
        flag = True
