#!/usr/bin/env python

import requests
import json
from IPython import embed
from requests import Request, Session


tarball_url = 'https://github.com/kennethreitz/requests/tarball/master'
r = requests.get(tarball_url, stream=False)

print r.content