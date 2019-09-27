from __future__ import absolute_import, unicode_literals

import json
import os
import threading
import time

from celery import shared_task

from .models import *
from .utils import SSH

def unique_name(task_object):
    if isinstance(task_object, SosTask):
        return f'sos_task_{task_object.id}'
    elif isinstance(task_object, LocalTask):
        return f'local_task_{task_object.id}'

def simulate_path(task_object, filename=''):
    if isinstance(task_object, SosTask):
        return '/'.join([task_object.server.base_path, '_'.join([task_object.name, task_object.project.name] + [label.name for label in task_object.project.soslabel_set.all()]), task_object.project.simulate_path, filename]).replace('//', '/')
    elif isinstance(task_object, LocalTask):
        return '/'.join([task_object.project.simulate_path, filename]).replace('//', '/')

def get_file_from_server(server_id, path):
    server = Server.objects.get(id=server_id)
    ssh = SSH(server.ip, server.username, server.password)
    try:
        content = ssh.get_file(path).read()
    except:
        content = None
    ssh.close()
    return content

def get_report_from_server(task_object, ssh=None, report_path=None, report_table=None):
    if not isinstance(report_table, dict):
        report_table = {}
    if report_path is None:
        report_path = simulate_path(task_object, 'regression.report')
    try:
        if ssh is None:
            content = get_file_from_server(task_object.server.id, report_path)
        else:
            content = ssh.get_file(report_path).read()
        data = json.loads(content)
        for testcase, seeds in data['testcase'].items():
            for seed, info in seeds.items():
                if testcase not in report_table:
                    report_table[testcase] = {}
                report_table[testcase][seed] = {
                    'passed': info['passed'],
                    'file': info['file'],
                    'server_id': task_object.server.id,
                }
        return data
    except:
        return None

def get_report_statistic(task_type, task_id, timestamp):
    try:
        with open(os.path.join('report', f'{task_type}_{task_id}_{timestamp}.json'), 'r') as f:
            content = f.read()
    except:
        content = ''
    passed_num = content.count('"passed": true,')
    failed_num = content.count('"passed": false,')
    unknown_num = content.count('"passed": null,')
    return {
        'pass': passed_num,
        'fail': failed_num,
        'unknown': unknown_num,
        'total': passed_num + failed_num + unknown_num,
        'passing_rate': round(passed_num / (passed_num + failed_num + unknown_num), 4) if passed_num + failed_num + unknown_num != 0 else 0,
    }

def get_report_list(task_type=None, task_id=None, latest=20):
    report_list = []
    for filename in os.listdir('report'):
        try:
            _task_type, _task_id, timestamp = filename.replace('.json', '').split('_', maxsplit=2)
            if ((_task_type == task_type) if task_type else True) and ((int(_task_id) == task_id) if task_id else True) and len(timestamp) == 14:
                format_time = f'{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}'
                report_list.append({
                    'filename': filename,
                    'task_type': _task_type,
                    'task_id': int(_task_id),
                    'timestamp': int(timestamp),
                    'format_time': format_time,
                    'link': f'./{timestamp}/',
                    'pass': 0,
                    'fail': 0,
                    'unknown': 0,
                    'total': 0,
                    'passing_rate': 0,
                })
        except:
            pass
    report_list.sort(key=lambda report: report['timestamp'])
    if latest:
        report_list = report_list[- latest:]
    for report in report_list:
        try:
            statistic = get_report_statistic(task_type, task_id, report['timestamp'])
            report['pass'] = statistic['pass']
            report['fail'] = statistic['fail']
            report['unknown'] = statistic['unknown']
            report['total'] = statistic['total']
            report['passing_rate'] = statistic['passing_rate']
        except:
            pass
    return report_list

def get_report(task_type, task_id, timestamp, failed_first=True):
    testcase_list = []
    try:
        if task_type == 'sos':
            task_object = SosTask.objects.get(id=task_id)
        elif task_type == 'local':
            task_object = LocalTask.objects.get(id=task_id)
        report_path = simulate_path(task_object, 'logs')
    except:
        report_path = ''
    try:
        with open(os.path.join('report', f'{task_type}_{task_id}_{timestamp}.json'), 'r') as f:
            for testcase, seed_table in json.loads(f.read()).items():
                for seed, info in seed_table.items():
                    testcase_list.append({
                        'test_case': testcase,
                        'seed': seed,
                        'status': 'Pass' if info['passed'] == True else 'Fail' if info['passed'] == False else 'Unknown',
                        'server_id': info['server_id'],
                        'link': f"../../../getfile/{info['server_id']}/{report_path}/{info['file']}",
                    })
    except:
        pass
    if failed_first:
        _weight = {
            'Fail': 1,
            'Unknown': 2,
            'Pass': 3,
        }
        testcase_list.sort(key=lambda testcase: _weight.get(testcase['status'], 0))
    return testcase_list

def balance_load():
    server_table = {}
    _total_cpu_free = 0
    _total_memory_free = 0
    for server in Server.objects.all():
        if server.online and server.ip not in server_table:
            server_table[server.ip] = {
                'server_id': server.id,
                'weight': 0,
                'cpu_free': 100 - server.cpu_usage,
                'memory_free': server.memory_free,
            }
            _total_cpu_free += 100 - server.cpu_usage
            _total_memory_free += server.memory_free
    for ip, data in server_table.items():
        server_table[ip]['weight'] = (data['cpu_free'] / _total_cpu_free) * 0.7 + (data['memory_free'] / _total_memory_free) * 0.3
    return [{
        'server_id': server['server_id'],
        'weight': server['weight'],
    } for server in server_table.values()]

def task_kill(task_object):
    try:
        ssh = SSH(task_object.server.ip, task_object.server.username, task_object.server.password)
        _, _, _, _, _ = ssh.execute(f'pkill -f {unique_name(task_object)}')
        ssh.close()
    except:
        pass

@shared_task
def get_server_status(server_id):
    server = Server.objects.get(id=server_id)
    try:
        ssh = SSH(server.ip, server.username, server.password)
        ssh.put_file(os.path.join('utils', 'sysinfo.py'), '.sysinfo.py')
        _, stdout, _, _, _ = ssh.execute('python3.7 .sysinfo.py')
        ssh.close()
        data = json.loads(stdout.read().decode('utf-8'))
        server.online = True
        server.cpu_usage = data.get('cpu_usage', 0)
        server.memory_free = data.get('memory_free', 0)
    except:
        server.online = False
    server.last_update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    server.save(update_fields=['online', 'cpu_usage', 'memory_free', 'last_update_time'])
    return server.online

@shared_task
def sos_regression_task(task_name):
    terminate_flag = False
    
    def core(server_id, test_case_list):
        try:
            nonlocal terminate_flag
            status_prefix = f'Server {server_id}: ' if task_object.cluster_mode else ''
            server = Server.objects.get(id=server_id)
            workarea_dir = '_'.join([task_object.name, project['name']] + project['label'])
            workarea_path = '/'.join([server.base_path, workarea_dir])
            if terminate_flag:
                task_object.status = status_prefix + 'Terminated'
                return
            try:
                task_object.status = status_prefix + 'Connecting via SSH'
                task_object.save(update_fields=['status'])
                ssh = SSH(server.ip, server.username, server.password, port=22, environment=project['environment_variable'])
            except:
                terminate_flag = True
                task_object.status = status_prefix + 'Failed to connect via SSH'
                task_object.save(update_fields=['status'])
                return
            if terminate_flag:
                task_object.status = status_prefix + 'Terminated'
                return
            task_object.status = status_prefix + 'Preparing workarea'
            task_object.save(update_fields=['status'])
            _, _, _, _, status_code = ssh.execute([
                f"mkdir -p {workarea_path}",
                f"cd {workarea_path}",
            ])
            if status_code != 0:
                terminate_flag = True
                task_object.status = status_prefix + 'Failed to enter workarea'
                task_object.save(update_fields=['status'])
                return
            if terminate_flag:
                task_object.status = status_prefix + 'Terminated'
                return
            try:
                ssh.put_file(os.path.join('utils', 'agent.py'), '/'.join([workarea_path, '.agent.py']))
            except:
                terminate_flag = True
                task_object.status = status_prefix + 'Failed to upload agent'
                task_object.save(update_fields=['status'])
                return
            if terminate_flag:
                task_object.status = status_prefix + 'Terminated'
                return
            _, _, _, _, status_code = ssh.execute([
                f"cd {workarea_path}",
                f"soscmd newworkarea {project['name']} {project['name']} . {' '.join(['-l' + label for label in project['label']])}",
                f"soscmd populate {' '.join(project['populate_path'])} {project['simulate_path']}",
                "soscmd update" if task_object.update_workarea else "",
                "soscmd exitsos",
            ])
            if status_code != 0:
                terminate_flag = True
                task_object.status = status_prefix + 'Failed to update workarea'
                task_object.save(update_fields=['status'])
                return
            if terminate_flag:
                task_object.status = status_prefix + 'Terminated'
                return
            task_object.status = status_prefix + 'Running'
            task_object.save(update_fields=['status'])
            _environment_args = ' '.join(['\"' + name + '=' + value + '\"' for name, value in project['environment_variable'].items()])
            _command_args = ' '.join(['\"' + command + '\"' for command in project['command']])
            _testcase_args = ' '.join(['\"' + test_case + '\"' for test_case in test_case_list])
            command = f"python3.7 {'/'.join([workarea_path, '.agent.py'])} -i {unique_name(task_object)} -j {task_object.max_jobs} -e {_environment_args} -c {_command_args} -t {_testcase_args} -p \"{task_object.project.passed_flag}\" -f \"{task_object.project.failed_flag}\" -o {task_object.project.timeout} >& agent.log"
            print(status_prefix + command)
            ssh.execute([
                f"cd {'/'.join([workarea_path, project['simulate_path']])}",
                command,
            ])
            get_report_from_server(task_object, ssh=ssh, report_table=report)
            task_object.status = status_prefix + 'Done'
            task_object.save(update_fields=['status'])
        except:
            terminate_flag = True
            task_object.status = status_prefix + 'Error'
            task_object.save(update_fields=['status'])
        finally:
            try:
                ssh.close()
            except:
                pass
            return task_object.status

    task_object = SosTask.objects.get(name=task_name)
    if not task_object.running:
        task_object.celery_task_id = sos_regression_task.request.id
        task_object.running = True
        task_object.last_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        task_object.save(update_fields=['celery_task_id', 'running', 'last_run_time'])
    else:
        return 'Already running'
    project = {
        'name': task_object.project.name,
        'label': [label.name for label in task_object.project.soslabel_set.all()],
        'populate_path': [populate_path.path for populate_path in task_object.project.sospopulatepath_set.all()],
        'simulate_path': task_object.project.simulate_path,
        'environment_variable': {environment_variable.name: environment_variable.value for environment_variable in task_object.project.sosenvironmentvariable_set.all()},
        'command': [command.command for command in task_object.project.soscommand_set.all()],
        'test_case': {test_case.name: test_case.repeat for test_case in task_object.project.sostestcase_set.all()},
    }
    test_case_list = []
    for name, repeat in project['test_case'].items():
        test_case_list.extend([name] * repeat)
    # report = {test_case: {} for test_case in project['test_case']}
    report = {}
    if task_object.cluster_mode:
        test_case_table = {}
        for server in balance_load():
            test_case_table[server['server_id']], test_case_list = test_case_list[:round(len(test_case_list) * server['weight'])], test_case_list[round(len(test_case_list) * server['weight']):]
        thread_list = []
        for server_id, test_case_list in test_case_table.items():
            thread_list.append(threading.Thread(target=core, kwargs={'server_id': server_id, 'test_case_list': test_case_list}))
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()
    else:
        core(task_object.server.id, test_case_list)
    with open(os.path.join('report', f"sos_{task_object.id}_{time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))}.json"), 'w') as f:
        f.write(json.dumps(report, indent=4, ensure_ascii=False))
    task_object.celery_task_id = ''
    task_object.running = False
    if not terminate_flag:
        task_object.status = 'Done'
    task_object.save(update_fields=['celery_task_id', 'running', 'status'])
    return task_object.status

@shared_task
def local_regression_task(task_name):
    try:
        task_object = LocalTask.objects.get(name=task_name)
        if not task_object.running:
            task_object.celery_task_id = local_regression_task.request.id
            task_object.running = True
            task_object.last_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            task_object.save(update_fields=['celery_task_id', 'running', 'last_run_time'])
        else:
            return
        project = {
            'name': task_object.project.name,
            'simulate_path': task_object.project.simulate_path,
            'environment_variable': {environment_variable.name: environment_variable.value for environment_variable in task_object.project.localenvironmentvariable_set.all()},
            'command': [command.command for command in task_object.project.localcommand_set.all()],
            'test_case': {test_case.name: test_case.repeat for test_case in task_object.project.localtestcase_set.all()},
        }
        try:
            task_object.status = 'Connecting via SSH'
            task_object.save(update_fields=['status'])
            ssh = SSH(task_object.server.ip, task_object.server.username, task_object.server.password, port=22, environment=project['environment_variable'])
        except:
            task_object.celery_task_id = ''
            task_object.running = False
            task_object.status = 'Failed to connect via SSH'
            task_object.save(update_fields=['celery_task_id', 'running', 'status'])
            return
        try:
            ssh.execute(f"mkdir -p {project['simulate_path']}")
            ssh.put_file(os.path.join('utils', 'agent.py'), '/'.join([project['simulate_path'], '.agent.py']))
        except:
            task_object.celery_task_id = ''
            task_object.running = False
            task_object.status = 'Failed to upload agent'
            task_object.save(update_fields=['celery_task_id', 'running', 'status'])
            return
        test_case_list = []
        for name, repeat in project['test_case'].items():
            test_case_list.extend([name] * repeat)
        task_object.status = 'Running'
        task_object.save(update_fields=['status'])
        _environment_args = ' '.join(['\"' + name + '=' + value + '\"' for name, value in project['environment_variable'].items()])
        _command_args = ' '.join(['\"' + command + '\"' for command in project['command']])
        _testcase_args = ' '.join(['\"' + test_case + '\"' for test_case in test_case_list])
        command = f"python3.7 {'/'.join([project['simulate_path'], '.agent.py'])} -i {unique_name(task_object)} -j {task_object.max_jobs} -e {_environment_args} -c {_command_args} -t {_testcase_args} -p \"{task_object.project.passed_flag}\" -f \"{task_object.project.failed_flag}\" -o {task_object.project.timeout} >& agent.log"
        print(command)
        ssh.execute([
            f"cd {project['simulate_path']}",
            command,
        ])
        report = {}
        get_report_from_server(task_object, ssh=ssh, report_table=report)
        with open(os.path.join('report', f"local_{task_object.id}_{time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))}.json"), 'w') as f:
            f.write(json.dumps(report, indent=4, ensure_ascii=False))
        task_object.celery_task_id = ''
        task_object.running = False
        task_object.status = 'Done'
        task_object.save(update_fields=['celery_task_id', 'running', 'status'])
    except:
        task_object.celery_task_id = ''
        task_object.running = False
        task_object.status = 'Error'
        task_object.save(update_fields=['celery_task_id', 'running', 'status'])
    finally:
        try:
            ssh.close()
        except:
            pass
        return task_object.status

try:
    task_list = {
        'sos': [],
        'local': [],
    }
    for task_object in SosTask.objects.all():
        task_list['sos'].append(task_object.id)
        task_object.celery_task_id = ''
        task_object.running = False
        task_object.status = '-'
        task_object.save()
    for task_object in LocalTask.objects.all():
        task_list['local'].append(task_object.id)
        task_object.celery_task_id = ''
        task_object.running = False
        task_object.status = '-'
        task_object.last_run_time = '-'
        task_object.save()
    for server in Server.objects.all():
        server.online = False
        server.cpu_usage = 0
        server.memory_free = 0
        server.last_update_time = '-'
        server.save()
    for report in get_report_list(latest=None):
        if report['task_id'] not in task_list[report['task_type']]:
            os.remove(os.path.join('report', report['filename']))
except:
    pass
