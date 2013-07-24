"""

Simple AJAX server for csvview using cherrpy

"""
import cherrypy
import webbrowser
import os
import simplejson
import sys
import csv
import sqlite3
import threading

threadLocal = threading.local()


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

def getDbConn( dbName ):
    """Get a thread-local database connection.
    """
    varName = "sqlite3-dbConn-" + dbName
    v = getattr( threadLocal, varName, None )
    if v is None:
        v = sqlite3.connect( dbName )
        setattr( threadLocal, varName, v )
    return v

def getTableInfo( dbConn, tableName ):
    """Use sqlite tableinfo pragma to retrieve metadata on the given table
    """
    query = "pragma table_info(%s)" % tableName
    c = dbConn.execute( query )
    r = c.fetchall()
    return r

def viewFormat( columnType, cellVal ):
    """ format cellVal suitable for client-side rendering
    """
    numFormatStr = "{:,}"
    if columnType=="integer" or columnType=="float":
        ret = numFormatStr.format( cellVal )
    else:
        ret = cellVal
    return ret

class PagedDbTable(object):
    def __init__( self, dbName, dbTableName):
        self.dbName = dbName
        self.dbTableName = dbTableName
        query = "select count(*) from " + dbTableName
        dbConn = getDbConn( dbName )
        c = dbConn.execute( query );
        self.totalRowCount = c.fetchone()[0]
        self.baseQuery = "select * from " + dbTableName
        self.tableInfo = getTableInfo( dbConn, dbTableName )
        self.columnNames = map( lambda ti: ti[1], self.tableInfo )
        self.columnTypes = map( lambda ti: ti[2], self.tableInfo )

    def getDataPage( self, startRow, rowLimit ):
        dbConn = getDbConn( dbName )
        query = self.baseQuery + " limit " + str( startRow ) + ", " + str( rowLimit )
        print query
        c = dbConn.execute( query )
        rows = c.fetchall()
        print " ==> ", len( rows ), " rows"
        
        # now prepare rows for sending to view:
        viewRows = []
        for row in rows:
            mappedRow = {}
            for (columnName,columnType,cellVal) in zip( self.columnNames, self.columnTypes, row ):
                mappedRow[columnName] = viewFormat( columnType, cellVal )
            viewRows.append( mappedRow )
#        namedRows = map( lambda r: dict( zip( self.columnNames, r)), rows )
        return viewRows

APP_DIR = os.path.abspath(".")

class AjaxApp(object):
    def __init__( self, dbTable):
        self.dbTable = dbTable

    @cherrypy.expose
    def index(self):
        return open(os.path.join( APP_DIR, u'sg-ant-ajax-loading.html') )

    @cherrypy.expose
    def getCSVData(self, startRow, rowLimit):
        print "getCSVData: startRow = ", startRow, ", rowLimit = ", rowLimit
        startRow = int( startRow )
        rowLimit = int( rowLimit )
        cherrypy.response.headers['Content-Type'] = 'application/json'
        # rowData = self.dataFile['data'][ startRow : startRow + rowLimit ]
        rowData = self.dbTable.getDataPage( startRow, rowLimit )
        request = { 'startRow': startRow, 'rowLimit': rowLimit }
        response = { 'request': request, 'totalRowCount': self.dbTable.totalRowCount, 'results': rowData }                                                          
        return simplejson.dumps( response )

config = {'/':
                {'tools.staticdir.on': True,
                 'tools.staticdir.dir': APP_DIR,
                }
        }

def open_page():
    webbrowser.open("http://127.0.0.1:8080/")

# DATA_FILE = "bart-salaries/salaries_w_names.csv"
# csvFileData = readCSVFile( DATA_FILE )

dbName = "testdb.db"
tableName = "salaries_w_names"
dbTable = PagedDbTable( dbName, tableName )

cherrypy.engine.subscribe('start', open_page)
cherrypy.tree.mount( AjaxApp( dbTable ), '/', config=config)
cherrypy.engine.start()
