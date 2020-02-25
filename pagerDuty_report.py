#!/usr/bin/env python
import subprocess
import json
import requests
import re
import logging
import traceback
import sys, getopt
import os
from datetime import datetime, timedelta
from operator import itemgetter

reload(sys)  
sys.setdefaultencoding('utf8')

if not os.path.exists('/tmp/pagerduty'):
   path = "/tmp/pagerduty"
   os.mkdir( path, 0755 );

### setup template to give exception details
traceback_template = '''Traceback (most recent call last):
  File "%(filename)s", line %(lineno)s, in %(name)s
%(type)s: %(message)s\n''' # Skipping the "actual line" item

### supress the python SSL message being generated
import warnings
warnings.filterwarnings("ignore")

curr_date = datetime.today().strftime('%Y-%m-%d_%H%M%S')
curr_date_csv = datetime.today().strftime('%m/%d/%y')
logfile = "pagerDuty_report_" + curr_date + ".txt"
csvFile = "op_alerts.csv"
target = open('/tmp/pagerduty/' + logfile, 'w')
target.truncate()
# define the csv file where the ops infr alerts will be appended
target_csv = open('/tmp/pagerduty/' + csvFile, 'a')
print_errors = False

### Variables that will be passed to the pagerduty API
### Update to match your API key
API_KEY = 'AsFbGuY4vF2Yh7T93kpy'
#SINCE = '2017-03-04'
#UNTIL = '2017-04-04'
DATE_RANGE = ''
STATUSES = []
INCIDENT_KEY = ''
SERVICE_IDS = []
TEAM_IDS = []
USER_IDS = []
URGENCIES = []
TIME_ZONE = 'UTC'
SORT_BY = []
INCLUDE = []
LIMIT = 100
OFFSET = 0
MORE = 'true'

### Variables that will be passed to the pagerduty API
ESCALATION_POLICY_IDS = []
SCHEDULE_IDS = []
EARLIEST = False

### determine beginning and end date of the report
date = datetime.today()
modified_date = date + timedelta(days=2)
SINCE = datetime.strftime(date, "%Y/%m/%d")
UNTIL = datetime.strftime(modified_date, "%Y/%m/%d")
UNTIL = ""
#SINCE = '2018-09-08'
#UNTIL = '2018-09-09'
_yr = int(datetime.strftime(date, "%Y"))
_mo = int(datetime.strftime(date, "%m"))
_dy = int(datetime.strftime(date, "%d"))
### Define dictionaries that will store API result details 
### based on incident number
dict_summary_esc= {}
dict_summary = {}
dict_policyName = {}
dict_hostName = {}
dict_errors = {}

### Define lists that will store API result details
escalation_list = []
host_list = []
x_list = []
service_list = []
error_down_list = []
ping_list = []
pingdom_down_list = []
container_list = []
vpn_list = []
sox_list = []
cloud_ampq_list = []
process_list = []
disk_utilization_list = []
rabbit_mq_list = []
mysql_db_slave_list = []
error_disk_usage_list = []
error_jenkins_list = []
error_checkmk_list = []
error_mount_list = []
error_cpu_load_list = []
error_memory_list = []
error_file_system_list= []
error_ntf_list = []
error_collection_nginx_list = []
error_other_list = []

### Define lists that will store on call API result details
escalation_list_all = []
escalation_policy_oc = []
OFFSET_ONCALL = 0

### get days difference
def differ_days(date1, date2):

    a = date1
    b = date2
    return (a-b).days 


### check for command line arg, -all, to print each summary for a given error type
def main(argv):
   global print_errors
   try:
      opts, args = getopt.getopt(argv,"ha:v:",["help", "all="])
   except getopt.GetoptError:
      print 'To print all alert summaries: '
      print 'pagerduty.py -all'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'usage: pagerduty.py -all'
         sys.exit(3)
      elif opt in ("-a", "--all"):
         print_errors = True 


### Print all the errors of a given kind
### Print the total error count and the error messages 
def writeError(errDesc, errCount, errName):
  if errCount > 0:
    target.write('<tr><td>%s </td><td align=center>%s</td></tr>\n' % (errDesc, errCount))
    if print_errors:
      for inc_ in errName:
       target.write("<tr><td align=center></td><td>%s</td></tr>\n" % dict_summary[inc_])

### Call pagerduty API with an OFFSET value incremented by 100. 
### The pagerduty API will return a maximum of 100 records. The 
### API will be called until all results are returned 
def requestIncidents(OFFSET):
  url = 'https://api.pagerduty.com/incidents'
  headers = {
    'Accept': 'application/vnd.pagerduty+json;version=2',
    'Authorization': 'Token token={token}'.format(token=API_KEY)
  }
  payload = {
    'since': SINCE,
    'Authorization': 'Token token={token}'.format(token=API_KEY)
  }
  payload = {
    'since': SINCE,
    'since': SINCE,
    'until': UNTIL,
    'date_range': DATE_RANGE,
    'statuses[]': STATUSES,
    'incident_key': INCIDENT_KEY,
    'service_ids[]': SERVICE_IDS,
    'team_ids[]': TEAM_IDS,
    'guser_ids[]': USER_IDS,
    'urgencies[]': URGENCIES,
    'time_zone': TIME_ZONE,
    'sort_by[]': SORT_BY,
    'limit': LIMIT,
    'offset': OFFSET,
    'more': MORE,
    'include[]': INCLUDE
  }

  incident1 = requests.get(url, headers=headers, params=payload)
  return incident1

### Call the pagerduty api, parse the results and save the appropriate data 
def list_incidents():
  global OFFSET
  opsAlerts_total = 0
  number_of_incidents = 0
  ### call the pagerduty API and save results
  incident = requestIncidents(OFFSET)
  status_code = incident.status_code
  ### a status code off 200 equates to success  
  if status_code == 200:
    while status_code == 200:
      ### Store API results in a json structure
      jdata = incident.content
      json_data_parsed = json.loads(jdata)
      #print "json_data_parsed = ", json_data_parsed
      ### parse each record in the json object 
      for x in json_data_parsed['incidents']:
        number_of_incidents += 1
        ### print the pagerduty record. This statement is very useful for seeing the data  
        ### whether you're debugging or adding updates or new code  
        #print json.dumps(x, sort_keys=True, indent=4)  
        
        ### parse and save the API results data  
        try:
            summary = x['summary'].encode('utf-8')
            if not (x['escalation_policy'] is None):
               escalation_policy = x['escalation_policy']['summary'].encode('utf-8')
            else:
               escalation_policy = "NULL ESCALATION POLICY"
            incident_num = x['incident_number']

            ### append to the escaltion policy to the list
            escalation_list.append(escalation_policy)

            ### Build dictionaries using the incident number as the key
            dict_summary[incident_num] = summary
            dict_summary_esc[escalation_policy] = summary 
            if "Operational Support" in escalation_policy:
              x_list.append(summary)
            ### If the summary contains a host then populate host list else populate service list. 
            ### The regular expression matche the standarized naming process for nodes
            found_host = re.search('(oob)?(dev|qa|prod|ops|itops)-[\w\-]+\d+\.(nj|ma|tx|nyc?)\d+\.[\w\-]+\.[\w\-]+', summary)
            if found_host:
                host_list.append(found_host.group(0))
            else:
                service_list.append(summary)

            ### Search summary known errors. If a given error is found then populate the error list
            #print "summary = ", summary
            if "is DOWN" in summary:
                error_down_list.append(incident_num)
            elif "MySQL" in summary:
                mysql_db_slave_list.append(incident_num)
            elif "Pingdom" in summary:
                pingdom_down_list.append(incident_num)
            elif "Process " in summary:
                process_list.append(incident_num)
            elif "Check_MK" in summary:
                error_checkmk_list.append(incident_num)
            elif "Container " in summary:
                container_list.append(incident_num)
            elif "VPN " in summary:
                vpn_list.append(incident_num)
            elif "Sox " in summary:
                sox_list.append(incident_num)
            elif "CloudAMQP " in summary:
                cloud_ampq_list.append(incident_num)
            elif "PING " in summary:
                ping_list.append(incident_num)
            elif "Disk Utilization" in summary:
                disk_utilization_list.append(incident_num)
            elif "RabbitMQ" in summary:
                rabbit_mq_list.append(incident_num)
            elif "Disk Usage" in summary:
                error_disk_usage_list.append(incident_num)
            elif "Mount" in summary:
                error_mount_list.append(incident_num)
            elif "CPU load" in summary:
                error_cpu_load_list.append(incident_num)
            elif "Memory" in summary:
                error_memory_list.append(incident_num)
            elif "Filesystem" in summary:
                error_file_system_list.append(incident_num)
            elif "NTF Problem" in summary:
                error_ntf_list.append(incident_num)
            elif "collection_nginx_response_latency" in summary:
                error_collection_nginx_list.append(incident_num)
            elif "Jenkins" in summary:
                error_jenkins_list.append(incident_num)
            else:
                error_other_list.append(incident_num)
        except Exception as e:
            ### setup to retrieve exception details
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback_details = {
                                   'filename': exc_traceback.tb_frame.f_code.co_filename,
                                   'lineno'  : exc_traceback.tb_lineno,
                                   'name'    : exc_traceback.tb_frame.f_code.co_name,
                                   'type'    : exc_type.__name__,
                                   'message' : exc_value.message, # or see traceback._some_str()
                                }
            ### So we don't leave our local labels/objects dangling
            del(exc_type, exc_value, exc_traceback) # So we don't leave our local labels/objects dangling

            ### this exception detail is written to output wrapped in a comment for information sakes
            target.write("<!--\n")
            exception_string = str(e)
            target.write("Exception: %s\n" % exception_string)
            tback_string = str(traceback.print_exc())
            tback_string = traceback_template % traceback_details 
            target.write("Command that through Exception: %s\n" % tback_string)
            target.write(" ++++++++++++ skipping this message due to parsing error\n")
            target.write("-->\n")

      ### if more_incidents is true then call the pagerduty API to process the remaining records
      more_incidents = json_data_parsed['more']
      if more_incidents:
        OFFSET = OFFSET + 100
        incident = requestIncidents(OFFSET)
        status_code = incident.status_code
      else: 
       break
  else:
        target.write("<tr><td align=center><th>***********************</th></td></tr>\n")
        target.write("<tr><td align=center><th>Failed, status code = </th></td><td>%s</td></tr>\n" % status_code)
        target.write("<tr><td align=center><th>***********************</th></td></tr>\n")
        target.close()
        cmd = ('mailx -r "Infra Ops <tech.infrastructure.team@shutterstock.com>" -s "Pagerduty Report :: From %s to %s \nContent-Type: text/html""" "tech.infrastructure.team@shutterstock.com" < %s' % (SINCE, UNTIL, '/tmp/pagerduty/' +logfile))
        subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]
        # email report2
        exit()

  target.write("<p align=justify>The following is a report of all PagerDuty activity over the report period,\n")
  target.write("this report includes a summary of per host and per event type as well as a summary of\n")
  target.write("escalation policies")
  target.write("</p><br>\n")

  ### the set command removes any duplicates
  noDupes_escalation_list = set(escalation_list)
  for policyName in noDupes_escalation_list:
    esc_policy_name_count = escalation_list.count(policyName)
    dict_policyName[policyName] = esc_policy_name_count 
  ### sort policy names by error count in descending order
  sorted_by_count = reversed(sorted(dict_policyName.items(), key=itemgetter(1)))

  target.write("<hr>\n")
  target.write('<p style="text-align: center;"><strong>Alert Summary - Total alerts: %s</strong></p>\n' % str(number_of_incidents))
  target.write("<hr><br>\n")
  ### Escalation Policy results
  target.write('<table style="height: 192px;" width="100%">\n')
  target.write('<tr><th><span style="text-decoration: underline;">Policy Name</span></th><th><span style="text-decoration: underline;">Count</span></th><th><span style="text-decoration: underline;">Last Alert</span></th></tr>\n')
   
  for escalation_policy_name in sorted_by_count:
     escalation_policy_name = escalation_policy_name[0]
     escalation_policy_name_count = escalation_list.count(escalation_policy_name)
     if escalation_policy_name == "Operational Support":
       opsAlerts_total = escalation_policy_name_count
     ### This will write the last escaltion for the host
     target.write("<tr>\n")
     target.write('<td align="center">%s</td>\n' % escalation_policy_name.encode('utf-8'))
     target.write('<td align="center">%s</td>\n' %  str(escalation_policy_name_count))
     target.write('<td align="center">%s</td>\n' %  dict_summary_esc[escalation_policy_name].encode('utf-8'))
     target.write("</tr>\n")

  ### write host name and and number of alerts associated with the host
  target.write("<br/>")
  target.write("<br/>")
  target.write('<tr><th><span style="text-decoration: underline;">Alerts for Operational Support</span></th></tr>\n')
  ### header line:
  down = 0; fileSystem = 0; checkMk = 0; cpuLoad = 0; mount = 0; interface = 0; prodIssue = 0; raid = 0; ping = 0; ipmitool = 0; pingdom = 0; notFound = 0
  #target_csv.write("Date,OPS Alerts,DOWN,Filesystem,Check_MK,CPU load,Mount,Interface,Production Issue,RAID,PING,ipmitool,Pingdom,Week number \n")
  for line_ in x_list:
     target.write("<tr>\n")
     target.write('<p style="text-align: left;">%s</td>\n' % line_)
     target.write("</tr>\n")
     ### write csv file
     if "Filesystem" in line_:
       fileSystem += 1
       #print "Filesystem Found "   
     elif "DOWN" in line_:
       down += 1
       #print "DOWN Found "   
     elif "Check_MK" in line_:
       checkMk += 1
       #print "Check_MK Found "   
     elif "CPU load" in line_:
       cpuLoad += 1
       #print "CPU load Found "   
     elif "Mount" in line_:
       mount += 1
       #print "Mount Found "   
     elif "Interface" in line_:
       interface += 1
       #print "Interface Found "   
     elif "Production Issue" in line_:
       prodIssue += 1
       #print "Production Issue Found "   
     elif "RAID" in line_:
       raid += 1
       #print "RAID Found "   
     elif "PING" in line_:
       ping += 1
       #print "PING Found "   
     elif "ipmitool" in line_:
       ipmitool += 1
       #print "ipmitool Found "   
     elif "Pingdom" in line_:
       pingdom += 1
       #print "Pingdom Found "   
     else:
       notFound += 1
       #print "error not found "   
  week = (differ_days(datetime(_yr,_mo,_dy), datetime(2018,1,1)) // 7)  + 1
  curr_date_csv = str(_mo) + "/" + str(_dy) +"/" + str(_yr)
  target_csv.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s \n" % (curr_date_csv, opsAlerts_total, down, fileSystem, checkMk, cpuLoad, mount, interface, prodIssue, raid, ping, ipmitool, pingdom, week))
  target.write("</table>\n<br><hr>\n")
  target.write('<p style="text-align: center;"><strong>Per Host Alert Summary</strong></p>\n')
  target.write("<hr><br>\n")

  ### Host names and number of alerts per host
  target.write('<table style="height: 97px;" width="100%">\n')
  target.write("<tr><th align=left><u><strong>Host Name</strong></u></th><th><u><strong>Alert Count</strong></u></th></tr>\n")


  noDupes_host_list = set(host_list)
  ### Convert "set" to "list" then sort the list
  noDupes_host_list = list(noDupes_host_list)
  noDupes_host_list.sort()

  for hostName in noDupes_host_list:
    host_name_count = host_list.count(hostName)
    dict_hostName[hostName] = host_name_count 
  ### sort host names by error count in descending order
  sorted_by_countH = reversed(sorted(dict_hostName.items(), key=itemgetter(1)))


  ### write host name and and number of alerts associated with the host
  for host_name in sorted_by_countH:
     host_name = host_name[0]
     escalation_policy_name_count = host_list.count(host_name)
     target.write("<tr>\n")
     target.write("<td>%s</td>\n" % host_name)
     target.write("<td align=center>%s</td>\n" % str(host_list.count(host_name)))
     target.write("</tr>\n")

  target.write("</table>\n<br><hr>\n")

  ### calls writeError function for defined specific errors
  ### and write all summaries associated with the error 
  target.write('<p style="text-align: center;"><strong>Per Alert Type Summary</strong></p>\n')
  target.write("<hr><br>\n")
  target.write('<table style="height: 97px;" width="100%">\n')
  target.write("<tr><td><u><b>Error Type</b></u></td><td align=center><u><b>Count</b></u></td></tr>\n")

  allErrList = ['error_down_list', 'mysql_db_slave_list', 'error_disk_usage_list', 'error_jenkins_list', 'error_checkmk_list', \
               'error_mount_list', 'error_cpu_load_list', 'error_memory_list', 'pingdom_down_list','container_list', \
               'vpn_list', 'sox_list', 'cloud_ampq_list', 'ping_list', 'disk_utilization_list', 'rabbit_mq_list', \
               'process_list', 'error_file_system_list', 'error_ntf_list', 'error_collection_nginx_list']

  for err in allErrList:
    if len(err) > 0:
      ### err is a string and converted to list in errN
      errN = eval(err)
      dict_errors[err] = len(errN)

  sorted_by_error_count = reversed(sorted(dict_errors.items(), key=itemgetter(1)))
  for err_name in sorted_by_error_count:
     errName = err_name[0]
     errCount = err_name[1]
     if (errName == "error_down_list"): 
        errD = "DOWN"
     elif (errName == "mysql_db_slave_list"):
        errD = "MySQL (Unactionable)"
     elif (errName == "pingdom_down_list"):
        errD = "Pingdom (Unactionable)"
     elif (errName == "process_list"):
        errD = "Process (Unactionable)"
     elif (errName == "container_list"):
        errD = "Container (Unactionable)"
     elif (errName == "vpn_list"):
        errD = "VPN (Unactionable)"
     elif (errName == "sox_list"):
        errD = "SOX (Unactionable)"
     elif (errName == "cloud_ampq_list"):
        errD = "CloudAMQP"
     elif (errName == "ping_list"):
        errD = "Ping"
     elif (errName == "disk_utilization_list"):
        errD = "Disk Utilization"
     elif (errName == "rabbit_mq_list"):
        errD = "RabbitMQ (Unactionable)"
     elif (errName == "error_disk_usage_list"):
        errD = "Disk Usage"
     elif (errName == "error_jenkins_list"):
        errD = "Jenkins (Unactionable)"
     elif (errName == "error_checkmk_list"):
        errD = "Check MK (Unactionable)"
     elif (errName == "error_mount_list"):
        errD = "Mount Options (Unactionable)"
     elif (errName == "error_cpu_load_list"):
        errD = "CPU Load (Unactionable)"
     elif (errName == "error_memory_list"):
        errD = "Memory (Unactionable)"
     elif (errName == "error_file_system_list"):
        errD = "File System"
     elif (errName == "error_ntf_list"):
        errD = "NTF (Unactionable)"
     elif (errName == "error_collection_nginx_list"):
        errD = "Collection nginx (Unactionable)"
     else:
        errD = "No error found"

     writeError(errD,errCount,eval(errName))
     
  target.write("</table>\n")
 
### On Call reporting
### Call pagerduty API with an OFFSET_ONCALL value incremented by 25.
### The pagerduty API will return a maximum of 25 records. The
### API will be called until all results are returned
def requestOncall(OFFSET_ONCALL):
    url = 'https://api.pagerduty.com/oncalls'
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token={token}'.format(token=API_KEY)
    }
    payload = {
        'time_zone': TIME_ZONE,
        'include[]': INCLUDE,
        'user_ids[]': USER_IDS,
        'escalation_policy_ids[]': ESCALATION_POLICY_IDS,
        'schedule_ids[]': SCHEDULE_IDS,
        'since': SINCE,
        'until': UNTIL,
        'offset': OFFSET_ONCALL,
        'earliest': EARLIEST
    }

    oncall_results = requests.get(url, headers=headers, params=payload)
    return oncall_results


def list_oncalls():
  global OFFSET_ONCALL
  oncall = requestOncall(OFFSET_ONCALL)
  status_code = oncall.status_code
  if status_code == 200:
    while status_code == 200:
      ### Store API results in a json structure
      jdata = oncall.content
      json_data_parsed = json.loads(jdata)
      #print "json_data_parsed = ", json_data_parsed
      for x in json_data_parsed['oncalls']:
        #print json.dumps(x, sort_keys=True, indent=4)

        ### parse and save the API results data
        escalation_level = x['escalation_level']
        escalation_policy_oc_name = x['escalation_policy']['summary'].encode('utf-8')
        escalation_contact_name = x['user']['summary'].encode('utf-8')
        escalation_policy_oc.append({"esc_level": escalation_level, "esc_policy": escalation_policy_oc_name, "esc_contact": escalation_contact_name})
        escalation_list_all.append(escalation_policy_oc_name)

      ### if more_incidents is true then call the pagerduty API to process the remaining records
      more_incidents = json_data_parsed['more']
      if more_incidents:
       OFFSET_ONCALL = OFFSET_ONCALL + 25
       oncall = requestOncall(OFFSET_ONCALL)
       status_code = oncall.status_code
      else:
       break
  else:
    ### status code did not equal 200
    print "staus code is not 200, status code = ", status_code
    exit()

  escalation_list_all_unique = set(escalation_list_all)
  escalation_list_all_unique = sorted(escalation_list_all_unique, key=str.lower)
  target.write("<br><hr>\n")
  target.write('<p style="text-align: center;"><strong>Escalation Policies and On-Call contacts</strong></p>\n')
  target.write("<hr><br>\n")
  target.write('<table width="100%" cellspacing="0" cellpadding="0">\n')
  target.write('<tr><th><span style="text-decoration: underline;">Policy</span></th><th><span style="text-decoration: underline;">On Call</span></th><th><span style="text-decoration: underline;">On Call Level</span></th></tr>\n')
  target.write("<tr><th>&nbsp;</th><th>&nbsp;</th><th>&nbsp;</th></tr>\n")

  for ep in escalation_list_all_unique:
    ### filter by escalation policy
    policy_filtered = filter(lambda policy_: policy_['esc_policy'] == ep, escalation_policy_oc)
    ### sort dictionary by escaltion level 
    sorted_by_level = sorted(policy_filtered, key=itemgetter('esc_level'))
    for rec in sorted_by_level:
        level = rec.get('esc_level')
        policy = rec.get('esc_policy')
        contact = rec.get('esc_contact')
        target.write("<tr>")
        target.write('<td align="center">%s</td>\n' % policy)
        target.write('<td align="center">%s</td>\n' %  contact)
        target.write('<td align="center">%s</td>\n' %  level)
        target.write("</tr>\n")

if __name__ == '__main__':
    main(sys.argv[1:])
    list_incidents()
    list_oncalls()
    target.write("<hr><p><strong>Confluence Documentation:</strong> https://shutterstock-confluence.codefactori.com/display/OPS/Pagerduty+Monitoring <br /><strong>Generated automatically by:</strong> https://github.shuttercorp.net/ops/hacks/blob/master/pagerDuty_report.py</p>")
    target.close()
    target_csv.close()
    if UNTIL == "":
      modified_date = date + timedelta(days=1)
      UNTIL = datetime.strftime(modified_date, "%Y/%m/%d")

    cmd = ('mailx -r "Infra Ops <tech.infrastructure.team@shutterstock.com>" -s "Pagerduty Report :: From %s to %s\nContent-Type: text/html""" "tech.infrastructure.team@shutterstock.com" < %s' % (SINCE, UNTIL, '/tmp/pagerduty/' + logfile))
    subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]

    cmd1 = ('mailx -r "Infra Ops <tech.infrastructure.team@shutterstock.com>" -s "Pagerduty Report :: From %s to %s\nContent-Type: text/html""" "jwaldron@shutterstock.com" < %s' % (SINCE, UNTIL, '/tmp/pagerduty/' + logfile))
    subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True).communicate()[0]
    # shell script will email the attachment, $target_csv. The call subprocess.Popen with mailx with an attachment was blowing up in python library.
    # The same call in a bourne shell works. My guess and research says the failure may be fixed in the current python version. We're running v2.7 
    os.system('sh /usr/local/bin/email_file.sh')
