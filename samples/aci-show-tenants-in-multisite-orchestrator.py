# Sample code accessing the Cisco Multisite Orchestrator
from requests import Session


# Replace the following variables with the correct values for your deployment.
username = 'admin'
password = 'password'
mso_ip = '10.10.10.10'


def show_tenants():
    # Login to Multisite Orchestrator
    session = Session()
    data = {'username': username, 'password': password}
    resp = session.post('https://%s/api/v1/auth/login' % mso_ip, json=data, verify=False)
    if not resp.ok:
        print('Could not login to Multisite Orchestrator')
        return

    # Get the tenants
    headers = {"Authorization": "Bearer %s" % resp.json()['token']}
    resp = session.get('https://%s/api/v1/tenants' % mso_ip, headers=headers)
    if not resp.ok:
        print('Could not get tenants from Multisite Orchestrator')
        return

    # Print the result
    print('Tenants')
    print('-' * len('Tenants'))
    for tenant in resp.json()['tenants']:
        print(tenant['displayName'])


if __name__ == '__main__':
    show_tenants()