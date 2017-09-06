#!/usr/bin/env python

from acitoolkit.acitoolkit import *
import pygraphviz as pgv
import sys
import logging

creds = Credentials('apic',
                    "Generate logical diagrams of a running Cisco ACI Application Policy Infrastructure Controller")

creds.add_argument('-o', '--output',
                   help='Output file for diagram - e.g. out.png, out.jpeg',
                   required=True)
creds.add_argument('-t', '--tenants',
                   help='Tenants to include when generating diagrams',
                   nargs='*')
creds.add_argument('-v', '--verbose', help='show verbose logging information',
                   action='store_true')
creds.add_argument('-d', '--debug', help='enable acitoolkit debug loggin information',
                   action='store_true')

args = creds.get()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

session = Session(args.url, args.login, args.password)
try:
    assert (session.login().ok)
except:
    print("Connection to APIC failed")
    sys.exit()

graph = pgv.AGraph(directed=True, rankdir="LR")

if args.tenants:
    tenants = Tenant.get_deep(session, args.tenants)
else:
    tenants = Tenant.get_deep(session)


def tn_node(tn):
    return "cluster-tn-" + tn.name


def ctx_node(tn, ctx):
    return tn_node(tn) + "/ctx-" + ctx.name


def bd_node(tn, bd):
    return tn_node(tn) + "/bd-" + bd.name


def sn_node(tn, bd, sn):
    return bd_node(tn, bd) + "/sn-" + sn.get_addr()


def app_node(tn, app):
    return tn_node(tn) + "/app-" + app.name


def epg_node(tn, app, epg):
    return app_node(tn, app) + "/epg-" + epg.name


def ctrct_node(tn, ctrct):
    return tn_node(tn) + "/ctrct-" + ctrct.name


for tenant in tenants:
    print("Processing tenant " + tenant.name)

    tncluster = graph.add_subgraph(name=tn_node(tenant),
                                   label="Tenant: " + tenant.name, color="blue")

    for context in tenant.get_children(only_class=Context):
        tncluster.add_node(ctx_node(tenant, context),
                           label="Private Network\n" + context.name,
                           shape='circle')

    for bd in tenant.get_children(only_class=BridgeDomain):
        tncluster.add_node(bd_node(tenant, bd),
                           label="Bridge Domain\n" + bd.name, shape='box')

        if bd.get_context():
            tncluster.add_edge(ctx_node(tenant, bd.get_context()),
                               bd_node(tenant, bd))
        else:
            tncluster.add_node("_ctx-dummy-" + bd_node(tenant, bd),
                               style="invis", label='Private Network',
                               shape='circle')
            tncluster.add_edge("_ctx-dummy-" + bd_node(tenant, bd),
                               bd_node(tenant, bd), style="invis")

        for sn in bd.get_children(only_class=Subnet):
            tncluster.add_node(sn_node(tenant, bd, sn),
                               label="Subnet\n" + sn.get_addr(), shape='box',
                               style='dotted')
            tncluster.add_edge(bd_node(tenant, bd), sn_node(tenant, bd, sn))
    for app in tenant.get_children(only_class=AppProfile):

        appcluster = tncluster.add_subgraph(name=app_node(tenant, app),
                                            label="Application Profile\n" + app.name)

        for epg in app.get_children(only_class=EPG):
            appcluster.add_node(epg_node(tenant, app, epg),
                                label="EPG\n" + epg.name)
            if epg.has_bd():
                tncluster.add_edge(bd_node(tenant, epg.get_bd()),
                                   epg_node(tenant, app, epg), style='dotted')

            for pc in epg.get_all_provided():
                appcluster.add_node(ctrct_node(tenant, pc),
                                    label="Contract\n" + pc.name, shape='box',
                                    style='filled', color='lightgray')
                appcluster.add_edge(epg_node(tenant, app, epg),
                                    ctrct_node(tenant, pc))

            for cc in epg.get_all_consumed():
                appcluster.add_node(ctrct_node(tenant, cc),
                                    label="Contract\n" + cc.name, shape='box',
                                    style='filled', color='lightgray')
                appcluster.add_edge(ctrct_node(tenant, cc),
                                    epg_node(tenant, app, epg))

if args.verbose:
    print("Finished loading the structure from APIC, here is the graph source (GraphViz DOT format):")
    print("================================================================================")
    print(graph.string())
    print("================================================================================")

print("\n\nDrawing graph to %s" % args.output)
graph.draw(args.output, prog='dot')
