# -*- coding: utf-8 -*-
import os
import sys
import ConfigParser
import getpass
import base64

from xml.dom import minidom

parentdir = os.path.dirname(os.path.abspath(__file__))
libdir = parentdir + '/youtrack/'
sys.path.append(libdir)
from youtrack.connection import Connection
from youtrack import YouTrackException

Config = ConfigParser.ConfigParser()
Config.read('config')

server = Config.get('YOUTRACK', 'Server')
domain = Config.get('YOUTRACK', 'domain')
project = Config.get('YOUTRACK', 'Project')
category = Config.get('YOUTRACK', 'Category')
user = Config.get('USER', 'Username')

try:
    passwd_encoded = Config.get('USER', 'PASSWORD')
    passwd = base64.b64decode(passwd_encoded)
except ConfigParser.NoOptionError:
    passwd = getpass.getpass('Password is not set! Type password: ')
    passwd_encoded = base64.b64encode(passwd)
    Config.set('USER', 'PASSWORD', passwd_encoded)
    with open('config', 'w') as cfg_file:
        Config.write(cfg_file)
try:
    connection = Connection(server, domain + '\\' + user, passwd)

    # Get array of issues
    issues_list = connection.getIssues(project, 'Category: {' + category + '} State: -Obsolete sort by: {issue id} asc', 0, 2000)

    doc = minidom.Document()
    root = doc.createElement('sections')

    def get_super_parents(issues):
        parent_dict = dict()
        for issue in issues:
            parent_dict[issue.id] = (connection.getIssues(project, 'Category: {' + category + '} State: -Obsolete Parent for: ' + issue.id, 0, 2000))
        parents = []
        for s in range(len(parent_dict.items())):
            if not parent_dict.items()[s][1]:
                parents.append(parent_dict.items()[s][0])
        return parents

    def get_subtasks(issue_id):
        return connection.getIssues(project, 'Subtask of: ' + issue_id + ' State: -Obsolete', 0, 2000)

    def is_parent(issue_id):
        result = connection.getIssues(project, 'Subtask of: ' + issue_id + ' State: -Obsolete', 0, 2000)
        return len(result) != 0

    def get_child(issue_id, t):
        section = doc.createElement('section')
        name = doc.createElement('name')
        name_text = doc.createTextNode(connection.getIssue(issue_id).summary.split('->')[-1])
        title_text = doc.createTextNode(connection.getIssue(issue_id).summary.split('->')[-1])
        cases = doc.createElement('cases')
        case = doc.createElement('case')
        title = doc.createElement('title')
        name.appendChild(name_text)
        title.appendChild(title_text)
        case.appendChild(title)
        cases.appendChild(case)
        section.appendChild(name)

        for issue in get_subtasks(issue_id):
            if not is_parent(issue.id):
                issue_text = doc.createTextNode(connection.getIssue(issue.id).summary.split('->')[-1])
                issue_case = doc.createElement('case')
                title_case = doc.createElement('title')
                title_case.appendChild(issue_text)
                issue_case.appendChild(title_case)
                cases.appendChild(issue_case)

        section.appendChild(cases)

        for issue in get_subtasks(issue_id):
            if is_parent(issue.id):
                sections_issue = doc.createElement('sections')
                for issue in get_subtasks(issue_id):
                    if is_parent(issue.id):
                        get_child(issue.id, sections_issue)
                section.appendChild(sections_issue)
                break

        t.appendChild(section)

    for parent in get_super_parents(issues_list):
        get_child(parent, root)

    doc.appendChild(root)
    xml_str = doc.toprettyxml(indent="  ")
    with open(category + ".xml", "w") as f:
        f.write(xml_str)
except YouTrackException:
    print 'PASSWORD is incorrect!'
    print 'Delete password option from the config file'
