from acitoolkit import *
from credentials import *

def send_to_apic(tenant):
    # Login to APIC and push the config
    session = Session(URL, LOGIN, PASSWORD, False)
    session.login()
    resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
    if resp.ok:
        print 'Success'

# Basic Connectivity Example
# Equivalent to connecting to ports to the same VLAN

# Create a tenant
tenant = Tenant('Coke')

# Create a Context and a BridgeDomain
context = Context('VRF-1', tenant)
context.set_allow_all()
bd = BridgeDomain('BD-1', tenant)
bd.add_context(context)

# Create an App Profile and an EPG
app = AppProfile('sap', tenant)
epg = EPG('sapepg', app)

# Attach the EPG to 2 interfaces using VLAN 5 as the encap
if1 = Interface('eth','1','101','1','62')
if2 = Interface('eth','1','101','1','63')
vlan5_on_if1 = L2Interface('vlan5_on_if1', 'vlan', '5')
vlan5_on_if2 = L2Interface('vlan5_on_if2', 'vlan', '5')
vlan5_on_if1.attach(if1)
vlan5_on_if2.attach(if2)
epg.attach(vlan5_on_if1)
epg.attach(vlan5_on_if2)

# Dump the necessary configuration
print 'URL:', tenant.get_url()
print 'JSON:', tenant.get_json()

send_to_apic(tenant)

# Clean up
#tenant.mark_as_deleted()
#send_to_apic(tenant)


