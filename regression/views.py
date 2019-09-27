from django.shortcuts import render

# Create your views here.

import json
import os

from .models import *
from .tasks import get_file_from_server, get_report_statistic, get_report_list, get_report

from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic.base import TemplateView

from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required

@method_decorator(staff_member_required, 'dispatch')
class SosReportListView(TemplateView):
    template_name = 'regression/report_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            task_object = SosTask.objects.get(id=context['id'])
            context['task'] = task_object.__str__()
            context['task_link'] = f'../../sostask/{task_object.id}/change/'
            context['project'] = task_object.project.__str__()
            context['project_link'] = f'../../sosproject/{task_object.project.id}/change/'
        except:
            context['task'] = 'Unknown'
            context['task_link'] = ''
            context['project'] = 'Unknown'
            context['project_link'] = ''
        context['report_list'] = get_report_list(task_type='sos', task_id=context['id'], latest=20)
        context['latest_report_link'] = context['report_list'][-1]['link'] if context['report_list'] else ''
        return context

@method_decorator(staff_member_required, 'dispatch')
class LocalReportListView(TemplateView):
    template_name = 'regression/report_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            task_object = LocalTask.objects.get(id=context['id'])
            context['task'] = task_object.__str__()
            context['task_link'] = f'../../localtask/{task_object.id}/change/'
            context['project'] = task_object.project.__str__()
            context['project_link'] = f'../../localproject/{task_object.project.id}/change/'
        except:
            context['task'] = 'Unknown'
            context['task_link'] = ''
            context['project'] = 'Unknown'
            context['project_link'] = ''
        context['report_list'] = get_report_list(task_type='local', task_id=context['id'], latest=20)
        context['latest_report_link'] = context['report_list'][-1]['link'] if context['report_list'] else ''
        return context

@method_decorator(staff_member_required, 'dispatch')
class SosReportDetailView(TemplateView):
    template_name = 'regression/report_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            task_object = SosTask.objects.get(id=context['id'])
            context['task'] = task_object.__str__()
            context['task_link'] = f'../../../sostask/{task_object.id}/change/'
            context['project'] = task_object.project.__str__()
            context['project_link'] = f'../../../sosproject/{task_object.project.id}/change/'
        except:
            context['task'] = 'Unknown'
            context['task_link'] = ''
            context['project'] = 'Unknown'
            context['project_link'] = ''
        timestamp_str = str(context['timestamp'])
        context['format_time'] = f'{timestamp_str[:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]} {timestamp_str[8:10]}:{timestamp_str[10:12]}:{timestamp_str[12:14]}' if len(timestamp_str) == 14 else 'Unknown'
        context['report'] = get_report(task_type='sos', task_id=context['id'], timestamp=context['timestamp'])
        context['statistic'] = get_report_statistic(task_type='sos', task_id=context['id'], timestamp=context['timestamp'])
        return context

@method_decorator(staff_member_required, 'dispatch')
class LocalReportDetailView(TemplateView):
    template_name = 'regression/report_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            task_object = LocalTask.objects.get(id=context['id'])
            context['task'] = task_object.__str__()
            context['task_link'] = f'../../../localtask/{task_object.id}/change/'
            context['project'] = task_object.project.__str__()
            context['project_link'] = f'../../../localproject/{task_object.project.id}/change/'
        except:
            context['task'] = 'Unknown'
            context['task_link'] = ''
            context['project'] = 'Unknown'
            context['project_link'] = ''
        timestamp_str = str(context['timestamp'])
        context['format_time'] = f'{timestamp_str[:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]} {timestamp_str[8:10]}:{timestamp_str[10:12]}:{timestamp_str[12:14]}' if len(timestamp_str) == 14 else 'Unknown'
        context['report'] = get_report(task_type='local', task_id=context['id'], timestamp=context['timestamp'])
        context['statistic'] = get_report_statistic(task_type='local', task_id=context['id'], timestamp=context['timestamp'])
        return context

@staff_member_required
def get_file(request, id, path):
    content = get_file_from_server(id, path)
    if content is None:
        return HttpResponseNotFound("The file you request cannot be found on this server")
    else:
        return HttpResponse(content, content_type='text/plain')
