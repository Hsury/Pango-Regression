from django.contrib import admin

# Register your models here.

import json
from copy import deepcopy
from celery.task.control import revoke

from django import forms
from django.utils.html import mark_safe
from django_celery_beat.admin import PeriodicTaskAdmin

from django_celery_beat.models import PeriodicTasks, IntervalSchedule
from .models import *
from .tasks import simulate_path, get_server_status, task_kill

if PeriodicTaskAdmin.form.clean:
    del(PeriodicTaskAdmin.form.clean)

class SosTaskAdmin(PeriodicTaskAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'project', 'server', 'max_jobs', 'update_workarea', 'cluster_mode', 'enabled', 'status', 'last_run_time'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('SCHEDULE', {
            'fields': ('interval', 'crontab', 'solar', 'clocked', 'start_time', 'expires', 'one_off'),
            'classes': ('extrapretty', 'wide'),
        }),
    )
    readonly_fields = (
        'status', 'last_run_time',
    )
    
    list_display = ('__str__', 'project', 'server', 'update_workarea', 'cluster_mode', 'enabled', 'running', 'status', 'last_run_time', 'view_log', 'view_report')
    list_filter = ('enabled', 'running')
    actions = PeriodicTaskAdmin.actions + ('stop_tasks', 'delete_tasks')

    def view_log(self, obj):
        return mark_safe(f'<input type="button" onclick="location.href=\'../getfile/{obj.server.id}/{simulate_path(obj, "agent.log")}\';" value="View" style="padding: 1px 8px;" />')
    view_log.short_description = 'Log'

    def view_report(self, obj):
        return mark_safe(f'<input type="button" onclick="location.href=\'../sosreport/{obj.id}/\';" value="View" style="padding: 1px 8px;" />')
    view_report.short_description = 'Report'

    def stop_tasks(self, request, queryset):
        for obj in queryset:
            task_kill(obj)
            if obj.celery_task_id:
                revoke(obj.celery_task_id, terminate=True)
                obj.celery_task_id = ''
            obj.running = False
            obj.status = '-'
            obj.save(update_fields=['celery_task_id', 'running', 'status'])
        self._message_user_about_update(request, len(queryset), 'stopped')
    stop_tasks.short_description = 'Stop selected tasks'
    
    def delete_tasks(self, request, queryset):
        for obj in queryset:
            if obj.celery_task_id:
                revoke(obj.celery_task_id, terminate=True)
            obj.delete()
        self._message_user_about_update(request, len(queryset), 'deleted')
    delete_tasks.short_description = 'Delete selected tasks'
    
    def save_model(self, request, obj, form, change):
        if obj.cluster_mode:
            obj.update_workarea = True
        if obj.celery_task_id:
            revoke(obj.celery_task_id, terminate=True)
            obj.celery_task_id = ''
        obj.running = False
        obj.status = '-'
        obj.task = 'regression.tasks.sos_regression_task'
        obj.kwargs = json.dumps({'task_name': obj.name})
        PeriodicTasks.update_changed()
        super().save_model(request, obj, form, change)
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class LocalTaskAdmin(PeriodicTaskAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'project', 'server', 'max_jobs', 'enabled', 'status', 'last_run_time'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('SCHEDULE', {
            'fields': ('interval', 'crontab', 'solar', 'clocked', 'start_time', 'expires', 'one_off'),
            'classes': ('extrapretty', 'wide'),
        }),
    )
    readonly_fields = (
        'status', 'last_run_time',
    )
    
    list_display = ('__str__', 'project', 'server', 'enabled', 'running', 'status', 'last_run_time', 'view_log', 'view_report')
    list_filter = ('enabled', 'running')
    
    actions = PeriodicTaskAdmin.actions + ('stop_tasks', 'delete_tasks')

    def view_log(self, obj):
        return mark_safe(f'<input type="button" onclick="location.href=\'../getfile/{obj.server.id}/{simulate_path(obj, "agent.log")}\';" value="View" style="padding: 1px 8px;" />')
    view_log.short_description = 'Log'

    def view_report(self, obj):
        return mark_safe(f'<input type="button" onclick="location.href=\'../localreport/{obj.id}/\';" value="View" style="padding: 1px 8px;" />')
    view_report.short_description = 'Report'

    def stop_tasks(self, request, queryset):
        for obj in queryset:
            task_kill(obj)
            if obj.celery_task_id:
                revoke(obj.celery_task_id, terminate=True)
                obj.celery_task_id = ''
            obj.running = False
            obj.status = '-'
            obj.save(update_fields=['celery_task_id', 'running', 'status'])
        self._message_user_about_update(request, len(queryset), 'stopped')
    stop_tasks.short_description = 'Stop selected tasks'
    
    def delete_tasks(self, request, queryset):
        for obj in queryset:
            if obj.celery_task_id:
                revoke(obj.celery_task_id, terminate=True)
            obj.delete()
        self._message_user_about_update(request, len(queryset), 'deleted')
    delete_tasks.short_description = 'Delete selected tasks'
    
    def save_model(self, request, obj, form, change):
        if obj.celery_task_id:
            revoke(obj.celery_task_id, terminate=True)
            obj.celery_task_id = ''
        obj.running = False
        obj.status = '-'
        obj.task = 'regression.tasks.local_regression_task'
        obj.kwargs = json.dumps({'task_name': obj.name})
        PeriodicTasks.update_changed()
        super().save_model(request, obj, form, change)
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class SosProjectAdmin(admin.ModelAdmin):
    class SosLabelInline(admin.TabularInline):
        model = SosLabel
        extra = 1

    class SosPopulatePathInline(admin.TabularInline):
        model = SosPopulatePath
        extra = 1

    class SosEnvironmentVariableInline(admin.TabularInline):
        model = SosEnvironmentVariable
        extra = 1

    class SosCommandInline(admin.TabularInline):
        model = SosCommand
        extra = 1

    class SosTestCaseInline(admin.TabularInline):
        model = SosTestCase
        extra = 1

    fieldsets = [
        (None,               {'fields': ['name', 'simulate_path', 'timeout']}),
        ('FLAG',             {'fields': ['passed_flag', 'failed_flag']}),
    ]
    inlines = [SosLabelInline, SosPopulatePathInline, SosEnvironmentVariableInline, SosCommandInline, SosTestCaseInline]
    list_display = ('name', 'simulate_path', 'rso')
    # list_filter = ['pub_date']
    search_fields = ['name']
    
    actions = ['clone_projects',] + admin.ModelAdmin.actions

    def clone_projects(self, request, queryset):
        for obj in queryset:
            _obj = deepcopy(obj)
            obj.pk = None
            obj.save()
            for attr in ['soslabel_set', 'sospopulatepath_set', 'sosenvironmentvariable_set', 'soscommand_set', 'sostestcase_set']:
                for sub_obj in getattr(_obj, attr).all():
                    sub_obj.pk = None
                    sub_obj.project = obj
                    sub_obj.save()
    clone_projects.short_description = 'Clone selected projects'

    def get_changeform_initial_data(self, request):
        return {
            'passed_flag': 'UVM TEST PASS',
            'failed_flag': 'UVM TEST FAIL',
        }

class LocalProjectAdmin(admin.ModelAdmin):
    class LocalEnvironmentVariableInline(admin.TabularInline):
        model = LocalEnvironmentVariable
        extra = 1

    class LocalCommandInline(admin.TabularInline):
        model = LocalCommand
        extra = 1

    class LocalTestCaseInline(admin.TabularInline):
        model = LocalTestCase
        extra = 1

    fieldsets = [
        (None,               {'fields': ['name', 'simulate_path', 'timeout']}),
        ('FLAG',             {'fields': ['passed_flag', 'failed_flag']}),
    ]
    inlines = [LocalEnvironmentVariableInline, LocalCommandInline, LocalTestCaseInline]
    list_display = ('name', 'simulate_path')
    # list_filter = ['pub_date']
    search_fields = ['name']
    
    actions = ['clone_projects',] + admin.ModelAdmin.actions

    def clone_projects(self, request, queryset):
        for obj in queryset:
            _obj = deepcopy(obj)
            obj.pk = None
            obj.save()
            for attr in ['localenvironmentvariable_set', 'localcommand_set', 'localtestcase_set']:
                for sub_obj in getattr(_obj, attr).all():
                    sub_obj.pk = None
                    sub_obj.project = obj
                    sub_obj.save()
    clone_projects.short_description = 'Clone selected projects'

    def get_changeform_initial_data(self, request):
        return {
            'passed_flag': 'UVM TEST PASS',
            'failed_flag': 'UVM TEST FAIL',
        }

class ServerForm(forms.ModelForm):
    # password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = Server
        fields = '__all__'
        widgets = {
            'password': forms.PasswordInput(),
        }

class ServerAdmin(admin.ModelAdmin):
    form = ServerForm
    fieldsets = [
        (None,               {'fields': ['ip', 'username', 'password', 'base_path']}),
        #('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    list_display = ('__str__', 'online', 'cpu_usage', 'memory_free', 'last_update_time')
    list_filter = ('online',)
    search_fields = ['name']
    actions = ('delete_servers',)

    def save_model(self, request, obj, form, change):
        obj.online = False
        obj.cpu_usage = 0
        obj.memory_free = 0
        obj.last_update_time = '-'
        super().save_model(request, obj, form, change)
        schedule, created = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.SECONDS)
        PeriodicTask.objects.get_or_create(interval=schedule, name=f"get_server_status_{obj.id}", task="regression.tasks.get_server_status", kwargs=json.dumps({'server_id': obj.id}))
        get_server_status(obj.id)
    
    def delete_servers(self, request, queryset):
        for obj in queryset:
            PeriodicTask.objects.get(name=f"get_server_status_{obj.id}").delete()
            obj.delete()
    delete_servers.short_description = 'Delete selected servers'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

admin.site.index_title = 'Welcome to Pango Regression Control Panel'
admin.site.site_header = 'Pango Regression'
admin.site.site_title = 'Pango Regression'
admin.site.register(SosTask, SosTaskAdmin)
admin.site.register(LocalTask, LocalTaskAdmin)
admin.site.register(SosProject, SosProjectAdmin)
admin.site.register(LocalProject, LocalProjectAdmin)
admin.site.register(Server, ServerAdmin)
