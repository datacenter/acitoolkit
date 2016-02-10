# all the imports
from flask import Flask, request, redirect, url_for, render_template

import acitoolkit.acitoolkit as ACI
from acitoolkit.acitoolkitlib import Credentials


# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
description = 'Simple application that logs on to the APIC and displays stats for all of the Interfaces.'
creds = Credentials('apic', description)
args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)

object_type = 'mo'
mo = 'topology'
aciClass = 'fabricTopology'
history_list = []


def login(session):
    """
    Does login and reports result
    :param session:
    """
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
    else:
        print 'Logged into {0} {1}'.format(args.url, args.login)


@app.route('/')
def show_object():
    """


    :return:
    """
    global history_list

    if object_type == 'class':
        if aciClass == 'topRoot':
            aci_objects = get_children('')
        else:
            aci_objects = get_objects(aciClass)

        history_list.append((object_type, aciClass))
        return render_template('show_class.html', aciObjects=aci_objects,
                               history=history_list[len(history_list) - 2::-1])
    else:
        (mo_class, attributes) = get_attributes(mo)
        children = get_children(mo)
        counters = get_counters(mo)
        history_list.append((object_type, mo))
        return render_template('show_mo.html', moClass=mo_class, mo=mo, attributes=attributes, children=children,
                               counters=counters, history=history_list[len(history_list) - 2::-1])


@app.route('/class_object', methods=['GET', 'POST'])
def class_object():
    """


    :return:
    """
    global object_type
    global aciClass
    object_type = 'class'
    passed_class = request.args.get('aciClass', '')
    if passed_class:
        aciClass = passed_class
    if request.method == 'POST':
        aciClass = request.form['aciClass']

    return redirect(url_for('show_object'))


@app.route('/managed_object', methods=['GET', 'POST'])
def managed_object():
    """


    :return:
    """
    global object_type
    global mo
    object_type = 'mo'
    passed_mo = request.args.get('mo', '')
    if passed_mo:
        mo = passed_mo
    if request.method == 'POST':
        mo = request.form['mo']

    return redirect(url_for('show_object'))


@app.route('/history', methods=['GET', 'POST'])
def history():
    """


    :return:
    """
    global object_type
    global mo
    global aciClass

    history = request.args.get('history', '')
    history.replace('%2F', '/')
    fields = history.split('?', 1)
    object_type = fields[0]
    if object_type == 'mo':
        mo = fields[1]
    else:
        aciClass = fields[1]

    return redirect(url_for('show_object'))


def get_attributes(dn):
    """

    :param dn:
    :return:
    """
    mo_query_url = '/api/mo/' + dn + '.json?query-target=self'
    ret = session.get(mo_query_url)
    ret._content = ret._content.replace('\n', '')
    data = ret.json()['imdata']
    result = []
    key = 'error'

    # check for timeout and re-login
    if len(data) > 0:
        if 'error' in data[0]:
            if data[0]['error']['attributes']['code'] == '403':
                print 'attempting re-login'
                login(session)
                ret = session.get(mo_query_url)
                ret._content = ret._content.replace('\n', '')
                data = ret.json()['imdata']

    for node in data:
        for key in node:
            if 'attributes' in node[key]:
                for attrib in node[key]['attributes']:
                    if attrib in ['dn', 'tDn', 'monPolDn', 'ctxDn', 'epgDn', 'epgPKey', 'ctxDefDn', 'ctrlrPKey', 'oDn',
                                  'eppDn', 'faultDKey', 'nodeDn', 'lsNodeDn', 'portDn', 'nodeDn']:
                        attrib_type = 'mo'
                    elif attrib in ['tCl', 'scope', 'oCl']:
                        attrib_type = 'aciClass'
                    else:
                        attrib_type = 'text'
                    result.append((str(attrib), str(node[key]['attributes'][attrib]), attrib_type))
    if key == 'error':
        print 'found error', data

    result.sort()
    return key, result


def get_children(dn):
    """

    :param dn:
    :return:
    """
    result = []
    mo_query_url = '/api/mo/' + dn + '.json?query-target=children'
    ret = session.get(mo_query_url)
    ret._content = ret._content.replace('\n', '')
    mo_data = ret.json()['imdata']
    for child in mo_data:
        for objectName in child:
            if objectName != 'error':
                child_dn = child[objectName]['attributes']['dn']
                result.append((objectName, child_dn))
    result.sort()
    return result


def get_counters(dn):
    """

    :param dn:
    :return:
    """
    result = []
    mo_query_url = '/api/mo/' + dn + '.json?query-target=self&rsp-subtree-include=stats'
    ret = session.get(mo_query_url)
    ret._content = ret._content.replace('\n', '')
    mo_data = ret.json()['imdata']
    for node in mo_data:
        for key in node:
            if 'children' in node[key]:
                for child in node[key]['children']:
                    for childkey in child:
                        result.append(
                            (childkey, node[key]['attributes']['dn'] + '/' + child[childkey]['attributes']['rn']))
    result.sort()
    return result


def get_objects(aci_class):
    """

    :param aci_class:
    :return:
    """
    class_query_url = '/api/node/class/' + aci_class + '.json?query-target=self'
    ret = session.get(class_query_url)
    ret._content = ret._content.replace('\n', '')
    data = ret.json()['imdata']
    result = []
    for node in data:
        for key in node:
            if 'dn' in node[key]['attributes']:
                result.append((key, str(node[key]['attributes']['dn'])))
            else:
                result.append((key, ''))

    return result


if __name__ == '__main__':
    login(session)
    print "point your browswer to http://127.0.0.1:5000"
    app.run()
