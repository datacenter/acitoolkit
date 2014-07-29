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

# Create a virtual port on the port channel
vp = L2Interface('vp', 'vlan', '5')
vp.attach(pc)

# Create a tenant, app profile, and epg
tenant = Tenant('coke')
app = AppProfile('app', tenant)
epg = EPG('epg', app)

# Connect EPG to the virtual port
epg.attach(vp)

# Print the resulting JSON
print pc.get_json()
print tenant.get_json()

