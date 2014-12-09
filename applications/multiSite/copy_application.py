import ast
import sys
import push_or_pull_github
from acitoolkit.acisession import Session
from credentials import *


def push_json_to_github(content):
    """
    :param content: the json to be pushed to github
    :return: None
    """
    push_or_pull_github.push_to_github(user_acct=github_info['git_account'],
                                       user_password=github_info['git_pw'],
                                       repo_owner=github_info['git_account'],
                                       repo_name=github_info['git_repo'],
                                       file_name=github_info['git_file'],
                                       commit_msg=github_info['commit_message'],
                                       content=content,
                                       branch=github_info['branch'])


def pull_json_from_github():
    """
    :return: the a configuration json file.
    """
    return push_or_pull_github.pull_from_github(user_acct=github_info['git_account'],
                                                user_passwood=github_info['git_pw'],
                                                repo_owner=github_info['git_account'],
                                                repo_name=github_info['git_repo'],
                                                file_name=github_info['git_file'])


def push_json_to_apic(json_content):
    """
    :param json_content: the json file to be pushed to APIC
    :return: the respond of the push action
    """
    session = Session(to_apic['URL'], to_apic['LOGIN'], to_apic['PASSWORD'])
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit()

    return session.push_to_apic('/api/mo/uni.json', json_content)


def pull_json_from_apic():
    """
    :return: all the json files that relate to the copied application profile.
    """
    def _push_to_list(l, i):
        if i not in l:
            l.append(i)

    def _push_child_to_tenant(mo):
        tenant_json['fvTenant']['children'].append(mo)

    session = Session(from_apic['URL'], from_apic['LOGIN'], from_apic['PASSWORD'])
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit()

    app_json = get_app_json_from_apic(session, from_apic['application'])
    # take out parameter 'dn':
    del app_json['fvAp']['attributes']['dn']

    cons = []
    filters = []
    bds = []
    private_networks = []

    # look for the contracts and bridge domains that are related
    for epg in app_json['fvAp']['children']:
        eliminated_children = []
        for child in epg['fvAEPg']['children']:
            if child.has_key('fvRsCons'):
                _push_to_list(cons, child['fvRsCons']['attributes']['tnVzBrCPName'])
            if child.has_key('fvRsProv'):
                _push_to_list(cons, child['fvRsProv']['attributes']['tnVzBrCPName'])
            if child.has_key('fvRsBd'):
                _push_to_list(bds, child['fvRsBd']['attributes']['tnFvBDName'])
            if child.has_key('fvRsNodeAtt') or child.has_key('fvRsPathAtt'):
                eliminated_children.append(epg['fvAEPg']['children'].index(child))
        eliminated_children.sort(reverse=True)
        for index in eliminated_children:
            epg['fvAEPg']['children'].pop(index)

    # achieve all the bridge domain json
    bds_json = []
    for bd in bds:
        bd_json = get_bridge_domain_json_from_apic(session, bd)
        del bd_json['fvBD']['attributes']['dn']
        bds_json.append(bd_json)
        if bd_json['fvBD']['children'][0]['fvRsCtx']['attributes']['tnFvCtxName']:
            private_networks.append(bd_json['fvBD']['children'][0]['fvRsCtx']['attributes']['tnFvCtxName'])

    private_networks_json = []
    for pn in private_networks:
        pn_json = get_private_network_json_from_apic(session, pn)
        del pn_json['fvCtx']['attributes']['dn']
        private_networks_json.append(pn_json)

    # achieve all the contracts json
    contracts_json = []
    for con in cons:
        con_json = get_contracts_json_from_apic(session, con)
        del con_json['vzBrCP']['attributes']['dn']
        contracts_json.append(con_json)
        # look for the filters that are related
        for subj in con_json['vzBrCP']['children']:
            if subj['vzSubj'].has_key('children'):
                for filter in subj['vzSubj']['children']:
                    _push_to_list(filters, filter['vzRsSubjFiltAtt']['attributes']['tnVzFilterName'])

    # achieve all the filters json
    filters_json = []
    for filter in filters:
        fil_json = get_filters_json_from_apic(session, filter)
        del fil_json['vzFilter']['attributes']['dn']
        filters_json.append(fil_json)

    # combine all the achieved json into one json object
    tenant_json = {'fvTenant': {'attributes': {'name': to_apic['tenant']}, 'children': []}}

    _push_child_to_tenant(app_json)
    for p_n in private_networks_json:
        _push_child_to_tenant(p_n)
    for b_j in bds_json:
        _push_child_to_tenant(b_j)
    for c_j in contracts_json:
        _push_child_to_tenant(c_j)
    for f_j in filters_json:
        _push_child_to_tenant(f_j)

    print "Successfully pull json from APIC."
    return tenant_json


def get_mo_json(session, mo_class, mo, mo_dn):
    """
    :param session: login session of APIC
    :param mo_class: class of mo
    :param mo: name of mo
    :param mo_dn: the dn of mo
    :return: the json file of mo
    """
    class_query_url = '/api/node/class/'+mo_class+'.json'
    ret = session.get(class_query_url)
    data = ret.json()['imdata']

    for fil in data:
        dn = fil[mo_class]['attributes']['dn']
        tenant_name = dn.split('/')[1][3:]
        mo_name = dn.split('/')[2][len(mo_dn)+1:]
        if tenant_name == from_apic['tenant'] and mo_name == mo:
            ap_query_url = '/api/mo/uni/tn-%s/%s-%s.json?rsp-subtree=full&rsp-prop-include=config-only' % (tenant_name, mo_dn, mo_name)
            ret = session.get(ap_query_url)
            return ast.literal_eval(ret.text)['imdata'][0]


def get_app_json_from_apic(session, application):
    """
    :param session: login session of APIC
    :param application: application profile name
    :return: json file of the application profile
    """
    return get_mo_json(session, 'fvAp', application, 'ap')


def get_bridge_domain_json_from_apic(session, bridge_domain):
    """
    :param session: login session of APIC
    :param bridge_domain: bridge domain name
    :return: json file of the bridge domain
    """
    return get_mo_json(session, 'fvBD', bridge_domain, 'BD')


def get_private_network_json_from_apic(session, private_network):
    """
    :param session: login session of APIC
    :param private_network: private network name
    :return: json file of the private network
    """
    return get_mo_json(session, 'fvCtx', private_network, 'ctx')


def get_contracts_json_from_apic(session, contract):
    """
    :param session: login session of APIC
    :param contract: contract name
    :return: json file of the contract
    """
    return get_mo_json(session, 'vzBrCP', contract, 'brc')


def get_filters_json_from_apic(session, filter):
    """
    :param session: login session of APIC
    :param filter: filter name
    :return: json file of the filter
    """
    return get_mo_json(session, 'vzFilter', filter, 'flt')


if __name__ == '__main__':

    if action['copy_json']:

        tenant_json = pull_json_from_apic()

        push_json_to_github(str(tenant_json))

    if action['paste_json']:

        tenant_json_from_github = pull_json_from_github()

        tenant_json_from_github = ast.literal_eval(tenant_json_from_github)

        # change Tenant and Application name before pushing to another APIC.
        tenant_json_from_github['fvTenant']['attributes']['name'] = to_apic['tenant']
        tenant_json_from_github['fvTenant']['attributes']['name'] = to_apic['tenant']
        if from_apic['application'] != to_apic['application']:
            for child in tenant_json_from_github['fvTenant']['children']:
                if child.has_key('fvAp'):
                    child['fvAp']['attributes']['name'] = to_apic['application']
                    break

        res = push_json_to_apic(tenant_json_from_github)

        print res
