"""

Simple AJAX server for csvview using cherrpy

"""
import cherrypy
import webbrowser
import os
import simplejson
import sys
import csv

def readCSVFile(filename):
    with open(filename) as csvfile:
        rd = csv.reader( csvfile )
        colNames = rd.next()
        data = []
        for row in rd:
            rowData = dict( zip( colNames, row ) )
            data.append( rowData )
    ret = { 'columnNames': colNames, 'data': data }
    return ret

APP_DIR = os.path.abspath(".")

class AjaxApp(object):
    def __init__( self, dataFile):
        self.dataFile = dataFile

    @cherrypy.expose
    def index(self):
        return open(os.path.join( APP_DIR, u'sg-ant-ajax-loading.html') )

    @cherrypy.expose
    def getCSVData(self, startRow, rowLimit):
        print "getCSVData: startRow = ", startRow, ", rowLimit = ", rowLimit
        startRow = int( startRow )
        rowLimit = int( rowLimit )
        cherrypy.response.headers['Content-Type'] = 'application/json'
        rowData = self.dataFile['data'][ startRow : startRow + rowLimit ]
        request = { 'startRow': startRow, 'rowLimit': rowLimit }
        response = { 'request': request, 'totalRowCount': len( self.dataFile['data'] ), 'results': rowData }                                                          
        return simplejson.dumps( response )

config = {'/':
                {'tools.staticdir.on': True,
                 'tools.staticdir.dir': APP_DIR,
                }
        }

def open_page():
    webbrowser.open("http://127.0.0.1:8080/")

DATA_FILE = "bart-salaries/salaries_w_names.csv"
csvFileData = readCSVFile( DATA_FILE )
cherrypy.engine.subscribe('start', open_page)
cherrypy.tree.mount(AjaxApp( csvFileData ), '/', config=config)
cherrypy.engine.start()
