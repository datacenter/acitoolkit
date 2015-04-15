################################################################################
#                                 _    ____ ___                                #
#                                / \  / ___|_ _|                               #
#                               / _ \| |    | |                                #
#                  _____       / ___ \ |___ | |  _       _                     #
#                 | ____|_ __ /_/_| \_\____|___|(_)_ __ | |_                   #
#                 |  _| | '_ \ / _` | '_ \ / _ \| | '_ \| __|                  #
#                 | |___| | | | (_| | |_) | (_) | | | | | |_                   #
#                 |_____|_|_|_|\__,_| .__/ \___/|_|_| |_|\__|                  #
#                     |_   _| __ __ |_|___| | _____ _ __                       #
#                       | || '__/ _` |/ __| |/ / _ \ '__|                      #
#                       | || | | (_| | (__|   <  __/ |                         #
#                       |_||_|  \__,_|\___|_|\_\___|_|                         #
#                                                                              #
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
from flask import Flask
try:
    import mysql.connector as mysql
except ImportError:
    import pymysql as mysql
from acitoolkit.acitoolkit import Credentials

def populate_data(mysql_ip, mysql_username, mysql_password):
    # Create the MySQL database
    cnx = mysql.connect(user=mysql_username, password=mysql_password,
                        host=mysql_ip,
                        database='acitoolkit')
    c = cnx.cursor()
    c.execute('USE acitoolkit;')
    c.execute('SELECT * FROM endpoints;')

    data = ''
    for (mac, ip, tenant, app, epg, interface, timestart, timestop) in c:
        if timestop is None:
            timestop = '0000-00-00 00:00:00'
        data = data + '<tr> <td>' + mac + '</td> '
        data = data + '<td>' + ip + '</td> '
        data = data + '<td>' + tenant + '</td> '
        data = data + '<td>' + app + '</td> '
        data = data + '<td>' + epg + '</td> '
        data = data + '<td>' + interface + '</td> '
        data = data + '<td>' + str(timestart) + '</td> '
        data = data + '<td>' + str(timestop) + '</td> '
        data = data + '</tr>'
    return data

app = Flask(__name__)

@app.route('/')
def hello_world():
    return """

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
	<head>
		<meta http-equiv="content-type" content="text/html; charset=utf-8" />
		
                <title>ACI Endpoint Tracker</title>
		<link rel="stylesheet" type="text/css" href="//netdna.bootstrapcdn.com/bootstrap/3.0.3/css/bootstrap.min.css">
		<link rel="stylesheet" type="text/css" href="//cdn.datatables.net/plug-ins/3cfcc339e89/integration/bootstrap/3/dataTables.bootstrap.css">

		<script type="text/javascript" language="javascript" src="//code.jquery.com/jquery-1.11.1.min.js"></script>
		<script type="text/javascript" language="javascript" src="//cdn.datatables.net/1.10.4/js/jquery.dataTables.min.js"></script>
		<script type="text/javascript" language="javascript" src="//cdn.datatables.net/plug-ins/3cfcc339e89/integration/bootstrap/3/dataTables.bootstrap.js"></script>
<script type="text/javascript" charset="utf-8">
/* Custom filtering function which will search data in column four between two values */
$.fn.dataTable.ext.search.push(
    function( settings, data, dataIndex ) {
        var time_min = $('#min');
        var time_max = $('#max');
        var date_min = $('#date_min');
        var date_max = $('#date_max');
        var timestart = data[6]

        return true;
    }
);
 
$(document).ready(function() {
    var table = $('#example').DataTable();
     
    // Event listener to the two range filtering inputs to redraw on input
    $('#date_min', '#date_max', '#min, #max').keyup( function() {
        table.draw();
    } );
} );
		</script>
</head>
                <h1 ALIGN=Center>ACI Endpoint Tracker</h1>

	<body>
		<div class="container">

<table border="0" cellspacing="5" cellpadding="5">
        <tbody>
      </tbody></table>
    </table>
<table id="example" class="display" cellspacing="0" width="100%%">
        <thead>
            <tr>
                <th>Mac</th>
                <th>IP</th>
                <th>Tenant</th>
                <th>App</th>
                <th>EPG</th>
		        <th>Interface</th>
	 	        <th>Time Start</th>
		        <th>Time Stop</th>
            </tr>
        </thead>
 
        <tfoot>
            <tr>
                <th>Mac</th>
                <th>IP</th>
                <th>Tenant</th>
                <th>App</th>
                <th>EPG</th>
		<th>Interface</th>
		<th>Time Start</th>
		<th>Time Stop</th>
            </tr>
        </tfoot>
 
        <tbody>
        %s
        </tbody>
    </table>
			
		</div>

<script type="text/javascript">
	// For demo to fit into DataTables site builder...
	$('#example')
		.removeClass( 'display' )
		.addClass('table table-striped table-bordered');
</script>
	</body>
</html>
    """ % populate_data(args.mysqlip, args.mysqllogin, args.mysqlpassword)

if __name__ == '__main__':
    description = ('Simple application that logs on to the APIC '
                   'and displays all of the Endpoints.')
    creds = Credentials(['mysql', 'server'], description)
    args = creds.get()
    
    app.run(debug=True, host=args.ip, port=int(args.port))
