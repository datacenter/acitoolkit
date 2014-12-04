import ast
import push_or_pull_github
from acitoolkit.acisession import Session
from credentials import *

session = Session(URL, LOGIN, PASSWORD)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'


def push_json_to_github(content):
    git = push_or_pull_github.github_login(git_account, git_pw)
    repo = push_or_pull_github.get_repo(git, git_account, git_repo)
    json_file = push_or_pull_github.get_file(repo, git_file)
    if json_file:
        json_file.delete('delete')
    push_or_pull_github.create_file(repo, git_file, 'test pushing json', content)


def pull_json_from_github():
    return push_or_pull_github.pull_from_github(user_acct=git_account,
                                                user_passwood=git_pw,
                                                repo_owner=git_account,
                                                repo_name=git_repo,
                                                file_name=git_file)


def push_json_to_apic(content):
    session.login()
    return session.push_to_apic('api/mo/uni.json', content)


def get_mo_json(mo_class, mo, mo_dn):

    class_query_url = '/api/node/class/'+mo_class+'.json'
    ret = session.get(class_query_url)
    data = ret.json()['imdata']

    for fil in data:
        dn = fil[mo_class]['attributes']['dn']
        tenant_name = dn.split('/')[1][3:]
        mo_name = dn.split('/')[2][len(mo_dn)+1:]
        if tenant_name == old_tenant and mo_name == mo:
            ap_query_url = '/api/mo/uni/tn-%s/%s-%s.json?rsp-subtree=full&rsp-prop-include=config-only' % (tenant_name, mo_dn, mo_name)
            ret = session.get(ap_query_url)
            return ast.literal_eval(ret.text)['imdata'][0]


def get_app_json_from_apic(application):

    return get_mo_json('fvAp', application, 'ap')


def get_bridge_domain_json_from_apic(bridge_domain):

    return get_mo_json('fvBD', bridge_domain, 'BD')


def get_private_network_json_from_apic(private_network):

    return get_mo_json('fvCtx', private_network, 'ctx')


def get_contracts_json_from_apic(contract):

    return get_mo_json('vzBrCP', contract, 'brc')


def get_filters_json_from_apic(filter):

    return get_mo_json('vzFilter', filter, 'flt')


if __name__ == '__main__':

    def push_to_list(l, i):
        if i not in l:
            l.append(i)

# -----------------------------------------------------------------------------
# to obtain all the related json files from APIC

    app_json = get_app_json_from_apic(old_application)
    # take out parameter 'dn':
    del app_json['fvAp']['attributes']['dn']

    cons = []
    filters = []
    bds = []
    private_networks = []

    # look for the contracts and bridge domains that are in used
    for epg in app_json['fvAp']['children']:
        eliminated_children = []
        for child in epg['fvAEPg']['children']:
            if child.has_key('fvRsCons'):
                push_to_list(cons, child['fvRsCons']['attributes']['tnVzBrCPName'])
            if child.has_key('fvRsProv'):
                push_to_list(cons, child['fvRsProv']['attributes']['tnVzBrCPName'])
            if child.has_key('fvRsBd'):
                push_to_list(bds, child['fvRsBd']['attributes']['tnFvBDName'])
            if child.has_key('fvRsNodeAtt') or child.has_key('fvRsPathAtt'):
                eliminated_children.append(epg['fvAEPg']['children'].index(child))
        eliminated_children.sort(reverse=True)
        for index in eliminated_children:
            epg['fvAEPg']['children'].pop(index)

    if old_application != new_application:
        app_json['fvAp']['attributes']['name'] = new_application

    # achieve all the bridge domain json
    bds_json = []
    for bd in bds:
        bd_json = get_bridge_domain_json_from_apic(bd)
        del bd_json['fvBD']['attributes']['dn']
        bds_json.append(bd_json)
        if bd_json['fvBD']['children'][0]['fvRsCtx']['attributes']['tnFvCtxName']:
            private_networks.append(bd_json['fvBD']['children'][0]['fvRsCtx']['attributes']['tnFvCtxName'])

    private_networks_json = []
    for pn in private_networks:
        pn_json = get_private_network_json_from_apic(pn)
        del pn_json['fvCtx']['attributes']['dn']
        private_networks_json.append(pn_json)

    # achieve all the contracts json
    contracts_json = []
    for con in cons:
        con_json = get_contracts_json_from_apic(con)
        del con_json['vzBrCP']['attributes']['dn']
        contracts_json.append(con_json)
        # look for the filters that are in used
        for subj in con_json['vzBrCP']['children']:
            for filter in subj['vzSubj']['children']:
                push_to_list(filters, filter['vzRsSubjFiltAtt']['attributes']['tnVzFilterName'])

    # achieve all the filters json
    filters_json = []
    for filter in filters:
        fil_json = get_filters_json_from_apic(filter)
        del fil_json['vzFilter']['attributes']['dn']
        filters_json.append(fil_json)

    # combine all the achieved json into one json object
    content = {'fvTenant': {'attributes': {'name': 'bonB'}, 'children': []}}

    def push_child_to_tenant(mo):
        content['fvTenant']['children'].append(mo)

    push_child_to_tenant(app_json)
    for p_n in private_networks_json:
        push_child_to_tenant(p_n)
    for b_j in bds_json:
        push_child_to_tenant(b_j)
    for c_j in contracts_json:
        push_child_to_tenant(c_j)
    for f_j in filters_json:
        push_child_to_tenant(f_j)

    # remove some un-meaningful string
    content = str(content)
    content.replace('{},', '')

# -----------------------------------------------------------------------------

    push_json_to_github(content)

# -----------------------------------------------------------------------------

    content = pull_json_from_github()

# -----------------------------------------------------------------------------

    res = push_json_to_apic(ast.literal_eval(content))
    print res
