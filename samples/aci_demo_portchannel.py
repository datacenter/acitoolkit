from acitoolkit import *

# Create the physical interface objects
intf1 = Interface('eth','1','101','1','38')
intf2 = Interface('eth','1','101','1','39')
intf3 = Interface('eth','1','102','1','38')
intf4 = Interface('eth','1','102','1','39')

# Create a port channel and add physical interfaces
pc = PortChannel('pc1')
pc.attach(intf1)
pc.attach(intf2)
pc.attach(intf3)
pc.attach(intf4)

# Create a VLAN interface on the port channel
# This is the L2 interface representing a single VLAN encap
# on this particular interface.
vlan5_on_pc = L2Interface('vlan5_on_pc', 'vlan', '5')
vlan5_on_pc.attach(pc)

# Create a tenant, app profile, and epg
tenant = Tenant('coke')
app = AppProfile('app', tenant)
epg = EPG('epg', app)

# Connect EPG to the VLAN interface
# Remember, this VLAN interface is on the port channel we created
# so the EPG will be attached to the port channel on VLAN 5
epg.attach(vlan5_on_pc)

# Print the resulting JSON
print pc.get_json()
print tenant.get_json()

