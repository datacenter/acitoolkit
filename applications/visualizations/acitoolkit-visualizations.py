import flask
import mysql.connector
from acitoolkitvisualizationslib import *

MYSQL_USERID = 'root'
MYSQL_PASSWORD = 'insieme'

app = flask.Flask(__name__)


@app.route('/')
def index():
    """ Displays the index page accessible at '/'
    """
    return flask.render_template('index.html')


@app.route('/pie')
def endpoint_tracker_pie():
    regenerate_pie_data(MYSQL_USERID, MYSQL_PASSWORD, '127.0.0.1')
    return flask.render_template('endpoint-tracker-pie.html',
                                 filename='endpoint_tracker_pie.csv')


@app.route('/force')
def endpoint_location_force():
    return flask.render_template('endpoint-force.html')


@app.route('/hierarchical')
def endpoint_hierarchical():
    return flask.render_template('endpoint-hierarchical-edge-bundling.html')


@app.route('/radial')
def endpoint_radial():
    regenerate_radial_data(MYSQL_USERID, MYSQL_PASSWORD, '127.0.0.1')
    return flask.render_template('endpoint-radial.html')


@app.route('/sunburst')
def endpoint_sunburst():
    regenerate_sunburst_data(MYSQL_USERID, MYSQL_PASSWORD, '127.0.0.1')
    return flask.render_template('endpoint-sunburst.html')


@app.route('/tree')
def endpoint_epg_tree():
    data = regenerate_endpoint_epg_tree(MYSQL_USERID, MYSQL_PASSWORD,
                                        '127.0.0.1')
    return flask.render_template('endpoint-tree.html', data=data)


if __name__ == '__main__':
    app.run(debug=True)
