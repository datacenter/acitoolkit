import ast
import push_or_pull_github
from acitoolkit.acisession import Session
from credentials import *

session = Session(URL, LOGIN, PASSWORD)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'


def push_to_github(content):
    git = push_or_pull_github.github_login(git_account, git_pw)
    repo = push_or_pull_github.get_repo(git, git_account, git_repo)
    json_file = push_or_pull_github.get_file(repo, git_file)
    if json_file:
        json_file.delete('delete')
    push_or_pull_github.create_file(repo, git_file, 'test pushing json', content)


def get_json_file_from_apic():
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
            if tenant_name == old_tenant:
                return ret

    json_file = get_contract_json()
    return json_file.content


def pull_from_github():
    return push_or_pull_github.pull_from_github(user_acct=git_account,
                                                user_passwood=git_pw,
                                                repo_owner=git_account,
                                                repo_name=git_repo,
                                                file_name=git_file)


def push_to_apic(content):
    session.login()
    return session.push_to_apic('api/mo/uni.json', content)


contract_json = get_json_file_from_apic()
push_to_github(contract_json)

pull_content = pull_from_github()
pull_content = ast.literal_eval(pull_content)
pull_content = pull_content['imdata'][0]
# take out some parameters:
for key in ['dn']:
    del pull_content['fvTenant']['attributes'][key]
# change tenant name
pull_content['fvTenant']['attributes']['name'] = new_tenant

content = pull_content
res = push_to_apic(content)
print res.text
