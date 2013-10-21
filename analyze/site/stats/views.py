from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic import DetailView, ListView
import matplotlib, string
import matplotlib.pyplot as plt
from pylab import figure, hist, plot

from stats.models import Job

import os,sys
sys.path.append('/Users/rtevans/tacc_stats/monitor')
sys.path.append('/Users/rtevans/tacc_stats/analyze/process_pickles')
import masterplot as mp
import tspl
import job_stats as data
import  cPickle as pickle 

path = '/Users/rtevans/pickles/'

def dates(request):
    date_list = []

    for date in os.listdir(path):
        date_list.append(date)
    return render_to_response("stats/dates.html", { 'date_list' : date_list})

def index(request, date):

    #Job.objects.all().delete()
    from datetime import datetime
    from django.utils.timezone import utc

    for jobid in os.listdir(path+date):
        if Job.objects.filter(id=jobid).exists(): continue

        try:
            with open(os.path.join(path,date,jobid)) as f:
                data = pickle.load(f)
            if len(data.times) == 0: continue
            del data.acct['yesno'], data.acct['unknown']
        except: continue
        
        fields = data.acct
        fields['path'] = os.path.join(path,date,jobid)
        fields['date'] = date
        fields['start_time']=datetime.fromtimestamp(data.start_time).replace(tzinfo=utc)
        fields['end_time']=datetime.fromtimestamp(data.end_time).replace(tzinfo=utc)
        
        job_model, created = Job.objects.get_or_create(**fields) 

    job_list = Job.objects.filter(date = date).order_by('-id')
    nj = Job.objects.filter(date = date).count()
    return render_to_response("stats/index.html", {'job_list' : job_list, 'date' : date, 'nj' : nj})

def figure_to_response(f):
    response = HttpResponse(content_type='image/png')
    f.savefig(response, format='png')
    plt.close(f)
    f.clear()
    return response

def jobs_summary(request, date):

    fig = figure(figsize=(17,6))
    # Run times
    job_times = [job.timespent / 3600. for job in Job.objects.filter(date = date)]
    ax = fig.add_subplot(121)
    ax.hist(job_times, max(5,len(job_times)/20))
    ax.set_title('Run Times')
    ax.set_ylabel('# of jobs')
    ax.set_xlabel('# hrs')
    # Number of cores
    job_size = [job.cores for job in Job.objects.filter(date = date)]
    ax = fig.add_subplot(122)
    ax.hist(job_size, max(5,len(job_size)/20))
    ax.set_title('Job Sizes')
    ax.set_xlabel('# cores')
    fig.tight_layout()
    return figure_to_response(fig)

def stats_load(job):
    with open(job.path) as f:
        job.stats = pickle.load(f)
    job.save()

def get_schema(job, type_name):
    with open(job.path) as f:
        data = pickle.load(f)
    schema = data.get_schema(type_name).desc
    schema = string.replace(schema,',E',' ')
    schema = string.replace(schema,' ,',',').split()
    schema = [x.split(',')[0] for x in schema]

    return schema



def stats_unload(job):
    job.stats = []
    job.save()

def master_plot(request, pk):
    job = Job.objects.get(id = pk)
    #stats_load(job) 
    fig = mp.master_plot(job.path,mintime=600)
    #stats_unload(job)
    return figure_to_response(fig)

class JobDetailView(DetailView):

    model = Job
    
    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        job = context['job']
        stats_load(job)
        type_list = []
        host_list = []
        ctr = 0
        for host_name, host in job.stats.hosts.iteritems():
            #if counter
            host_list.append(host_name)
            ctr +=1
        for type_name, type in host.stats.iteritems():
            schema = job.stats.get_schema(type_name).desc
            schema = string.replace(schema,',E',' ')
            schema = string.replace(schema,',',' ')
            type_list.append( (type_name, schema) )

        type_list = sorted(type_list, key = lambda type_name: type_name[0])
        context['type_list'] = type_list
        context['host_list'] = host_list
        stats_unload(job)
        return context

def type_plot(request, pk, type_name):

    job = Job.objects.get(id = pk)
    schema = get_schema(job, type_name)

    k1 = {'intel_snb' : [type_name]*len(schema)}
    k2 = {'intel_snb': schema}

    ts = tspl.TSPLSum(job.path,k1,k2)
    
    nr_events = len(schema)
    fig, axarr = plt.subplots(nr_events, sharex=True, figsize=(8,nr_events*2), dpi=80)
    do_rate = True
    for i in range(nr_events):
        if type_name == 'mem': do_rate = False
        axarr[i].set_ylabel(schema[i],size='small')
        mp.plot_lines(axarr[i], ts, [i], 3600., do_rate = do_rate)

    axarr[-1].set_xlabel("Time (hr)")
    fig.subplots_adjust(hspace=0.0)
    fig.tight_layout()
    response = HttpResponse(content_type='image/png')
    fig.savefig(response, format='png')
    plt.close(fig)
    fig.clear()

    return response


def type_detail(request, pk, type_name):

    job = Job.objects.get(id = pk)
    stats_load(job)
    data = job.stats

    schema = data.get_schema(type_name).desc
    schema = string.replace(schema,',E',' ')
    schema = string.replace(schema,' ,',',').split()

    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []
    for t in range(len(raw_stats)):
        temp = []
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event])
        stats.append((data.times[t],temp))

    stats_unload(job)

    return render_to_response("stats/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})
    