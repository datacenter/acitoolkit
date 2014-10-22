from cable import CABLEPLAN
from acisession import Session
from credentials import *
from acitoolkit import *
from aciphysobject import *
#import sys

session  = Session(URL, LOGIN, PASSWORD)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    
cp = CABLEPLAN.get(session)

fname = 'cable_plan.xml'

f = open(fname, 'w')
cp.export(f)
f.close()









