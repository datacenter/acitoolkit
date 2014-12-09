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


def get_json_file_from_apic():

    session = Session(from_apic['URL'], from_apic['LOGIN'], from_apic['PASSWORD'])
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit()

    def get_contract_json():
        class_query_url = '/api/node/class/fvTenant.json'
        ret = session.get(class_query_url)
        data = ret.json()['imdata']
        for ap in data:
            dn = ap['fvTenant']['attributes']['dn']
            tenant_name = dn.split('/')[1][3:]
            #class_query_url = '/api/mo/uni/tn-aci-toolkit-demo.json?query-target=subtree&rsp-subtree=full&rsp-subtree-include=audit-logs,no-scoped'
            ap_query_url = '/api/mo/uni/tn-%s.json?rsp-subtree=full&rsp-prop-include=config-only' % (tenant_name)
            ret = session.get(ap_query_url)
            if tenant_name == from_apic['tenant']:
                return ast.literal_eval(ret.text)['imdata'][0]

    json_file = get_contract_json()
    return json_file


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


if __name__ == '__main__':

    if action['copy_json']:

        contract_json = get_json_file_from_apic()
        del contract_json['fvTenant']['attributes']['dn']
        push_json_to_github(str(contract_json))

    if action['paste_json']:

        tenant_json_from_github = pull_json_from_github()
        tenant_json_from_github = ast.literal_eval(tenant_json_from_github)

        # change tenant name before pushing to another APIC
        if from_apic['tenant'] != to_apic['tenant']:
            tenant_json_from_github['fvTenant']['attributes']['name'] = to_apic['tenant']

        res = push_json_to_apic(tenant_json_from_github)
        print res
