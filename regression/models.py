from django.db import models

# Create your models here.

from django_celery_beat.models import PeriodicTask

class Server(models.Model):
    ip = models.GenericIPAddressField(protocol='IPv4', help_text='Server IP address')
    username = models.CharField(max_length=200, help_text='SSH username')
    password = models.CharField(max_length=200, help_text='SSH password')
    base_path = models.CharField(max_length=200, blank=True, help_text='Base directory path')
    online = models.BooleanField(verbose_name='Online', default=False)
    cpu_usage = models.FloatField(verbose_name='CPU Usage (%)', default=0)
    memory_free = models.FloatField(verbose_name='Memory Free (GB)', default=0)
    last_update_time = models.CharField(default='-', max_length=200)
    
    def __str__(self):
        return f'{self.username}@{self.ip}'

class SosProject(models.Model):
    name = models.CharField(max_length=200, help_text='SOS project name')
    simulate_path = models.CharField(max_length=200, help_text='Simulate path (relative in SOS project)')
    timeout = models.PositiveIntegerField(default=60, help_text='Expire time (minute) for each test case')
    passed_flag = models.CharField(max_length=200, help_text='Substring in test case log file standing for passed')
    failed_flag = models.CharField(max_length=200, help_text='Substring in test case log file standing for failed')

    def rso(self):
        return ' > '.join(str(label) for label in self.soslabel_set.all())
    
    def __str__(self):
        return f'{self.name}({self.rso()})@{self.simulate_path}'
    
    # rso.short_description = 'RSO'
    # get_rso.admin_order_field = 'book__author'

class SosLabel(models.Model):
    project = models.ForeignKey(SosProject, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Label name in SOS project')
    
    def __str__(self):
        return self.name

class SosPopulatePath(models.Model):
    project = models.ForeignKey(SosProject, on_delete=models.CASCADE)
    path = models.CharField(max_length=200, help_text='Populate path in SOS project')
    
    def __str__(self):
        return self.path

class SosEnvironmentVariable(models.Model):
    project = models.ForeignKey(SosProject, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Set the environment variable before executing commands')
    value = models.CharField(max_length=200, help_text='Set the environment variable before executing commands')
    
    def __str__(self):
        return f'{self.name}={self.value}'

class SosCommand(models.Model):
    project = models.ForeignKey(SosProject, on_delete=models.CASCADE)
    command = models.CharField(max_length=200, help_text='Command to execute')
    
    def __str__(self):
        return self.command

class SosTestCase(models.Model):
    project = models.ForeignKey(SosProject, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Test case to run')
    repeat = models.PositiveIntegerField(default=1, help_text='Times to repeat')
    
    def __str__(self):
        return f'{self.name} ×{self.repeat}'

class LocalProject(models.Model):
    name = models.CharField(max_length=200, help_text='Local project name')
    simulate_path = models.CharField(max_length=200, help_text='Simulate path (absolute)')
    timeout = models.PositiveIntegerField(default=60, help_text='Expire time (minute) for each test case')
    passed_flag = models.CharField(max_length=200, help_text='Substring in test case log file standing for passed')
    failed_flag = models.CharField(max_length=200, help_text='Substring in test case log file standing for failed')

    def __str__(self):
        return f'{self.name}@{self.simulate_path}'

class LocalEnvironmentVariable(models.Model):
    project = models.ForeignKey(LocalProject, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Set the environment variable before executing commands')
    value = models.CharField(max_length=200, help_text='Set the environment variable before executing commands')
    
    def __str__(self):
        return f'{self.name}={self.value}'

class LocalCommand(models.Model):
    project = models.ForeignKey(LocalProject, on_delete=models.CASCADE)
    command = models.CharField(max_length=200, help_text='Command to execute')
    
    def __str__(self):
        return self.command

class LocalTestCase(models.Model):
    project = models.ForeignKey(LocalProject, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text='Test case to run')
    repeat = models.PositiveIntegerField(default=1, help_text='Times to repeat')
    
    def __str__(self):
        return f'{self.name} ×{self.repeat}'

class SosTask(PeriodicTask):
    celery_task_id = models.CharField(default="", max_length=200)
    project = models.ForeignKey(SosProject, on_delete=models.CASCADE)
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    max_jobs = models.PositiveIntegerField(default=32, help_text='Max number of test cases to run simultaneously')
    update_workarea = models.BooleanField(default=True, help_text='Update SOS workarea everytime before running regression')
    cluster_mode = models.BooleanField(default=True, help_text='Dispatch test cases to all available servers, if set to True will force updating workarea')
    running = models.BooleanField(verbose_name='Running', default=False)
    status = models.CharField(default="-", max_length=200)
    last_run_time = models.CharField(default='-', max_length=200)

class LocalTask(PeriodicTask):
    celery_task_id = models.CharField(default="", max_length=200)
    project = models.ForeignKey(LocalProject, on_delete=models.CASCADE)
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    max_jobs = models.PositiveIntegerField(default=32, help_text='Max number of test cases to run simultaneously')
    running = models.BooleanField(verbose_name='Running', default=False)
    status = models.CharField(default="-", max_length=200)
    last_run_time = models.CharField(default='-', max_length=200)
