from acitoolkit.acitoolkit import *
import pygraphviz as pgv
import sys
import argparse

parser = argparse.ArgumentParser(description="Generate logical diagrams of a running Cisco ACI Application Policy Infrastructure Controller")

parser.add_argument('-l', '--login', help='Login for authenticating to APIC', required=True)
parser.add_argument('-p', '--password', help='Password for authenticating to APIC', required=True)
parser.add_argument('-u', '--url', help='URL for connecting to APIC', required=True)
parser.add_argument('-o', '--output', help='Output file for diagram - e.g. out.png, out.jpeg', required=True)
parser.add_argument('-t', '--tenants', help='Tenants to include when generating diagrams', nargs='*')
parser.add_argument('-v', '--verbose', help='show verbose logging information', action='store_true')

args = parser.parse_args()

session = Session(args.url, args.login, args.password)
try:
    assert(session.login().ok)
except:
    print "Connection to APIC failed"
    sys.exit()

graph=pgv.AGraph(directed=True, rankdir="LR")

if args.tenants:
    tenants=Tenant.get_deep(session, args.tenants)
else:
    tenants=Tenant.get_deep(session)

def tn_node(tn):
    return "cluster-tn-"+tn.name

def ctx_node(tn,ctx):
    return tn_node(tn)+"/ctx-"+ctx.name
    
def bd_node(tn, bd):
    return tn_node(tn)+"/bd-"+bd.name
    
def sn_node(tn, bd, sn):
    return bd_node(tn, bd)+"/sn-"+sn.get_addr()

for tenant in tenants:
    print "Processing tenant "+tenant.name
    
    tncluster = graph.add_subgraph(name=tn_node(tenant), label="Tenant: "+tenant.name, color="blue")
    
    for context in tenant.get_children(only_class=Context):
        tncluster.add_node(ctx_node(tenant, context), label="Private Network\n"+context.name, shape='circle')
        
    for bd in tenant.get_children(only_class=BridgeDomain):
        tncluster.add_node(bd_node(tenant, bd), label="Bridge Domain\n"+bd.name, shape='box')
        
        if bd.get_context():
            tncluster.add_edge(ctx_node(tenant,bd.get_context()), bd_node(tenant,bd))
            
        for sn in bd.get_children(only_class=Subnet):
            tncluster.add_node(sn_node(tenant, bd, sn), label = "Subnet\n"+sn.get_addr(), shape='box', style='filled', color='lightgray')
            tncluster.add_edge(bd_node(tenant, bd), sn_node(tenant, bd, sn))

if args.verbose:
    print "Finished loading the structure from APIC, here is the graph source (GraphViz DOT format):"
    print "================================================================================"
    print graph.string()    
    print "================================================================================"
    
print "\n\nDrawing graph to %s"%args.output
graph.draw(args.output, prog='dot')