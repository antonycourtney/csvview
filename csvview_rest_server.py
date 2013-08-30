"""

Simple AJAX server for csvview using cherrpy, this time done in the REST style

"""
import cherrypy
import webbrowser
import os
import simplejson
import sys
import csv
import sqlite3
import threading
from mako.template import Template
from mako.lookup import TemplateLookup

lookup = TemplateLookup(directories=['html'])
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
    if columnType=="integer" or columnType=="float" and cellVal!=None:
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
        # extract human-friendly descriptions from columnInfo companion table
        cinfoTable = dbTableName + "_columnInfo"
        c = dbConn.execute( "select description from " + cinfoTable)
        rows = c.fetchall()
        self.columnDescs = map( lambda r:r[0], rows )
        self.columnInfo = []
        for (cn,cd) in zip(self.columnNames,self.columnDescs):
            cmap = { 'id': cn, 'field': cn, 'name': cd }
            self.columnInfo.append( cmap )

    def getColumnInfo( self ):
        return self.columnInfo

    def getDataPage( self, startRow, rowLimit ):
        dbConn = getDbConn( dbName )
        query = self.baseQuery + " limit " + str( startRow ) + ", " + str( rowLimit )
        # print query
        c = dbConn.execute( query )
        rows = c.fetchall()
        # print " ==> ", len( rows ), " rows"
        
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

#
# N.B.:  We're still using a REST-ful (stateless) approach here, but doing so via the default() method.
# We do this because it appears that CherryPy's MethodDispatcher() doesn't allow default() or index()
# methods, which in turn would force us to reify the table hierarchy from the sqllite database as a
# tree of Python objects, which we don't want to do.
# So we just stick with the standard Dispatcher() but this means using default() to provide RESTful
# URIs. 

# Provide RESTful paged access to named table
class TableResource(object):
    def __init__(self):
        pass

    @cherrypy.expose
    def default( self, tableName, startRow = 0, rowLimit = 10 ):
        dbTable = PagedDbTable( dbName, tableName )     
        # print "startRow = ", startRow, ", rowLimit = ", rowLimit
        startRow = int( startRow )
        rowLimit = int( rowLimit )
        cherrypy.response.headers['Content-Type'] = 'application/json'
        # rowData = self.dataFile['data'][ startRow : startRow + rowLimit ]
        columnInfo = dbTable.getColumnInfo()
        rowData = dbTable.getDataPage( startRow, rowLimit )
        request = { 'startRow': startRow, 'rowLimit': rowLimit }
        response = { 'request': request, 'columnInfo': columnInfo, 
                     'totalRowCount': dbTable.totalRowCount, 'results': rowData }                                                          
        return simplejson.dumps( response )

        

# Use simple templating to inject table name extracted from request params back in to HTML on client side: 
class TableViewerResource(object):
    def __init__(self):
        pass

    @cherrypy.expose
    def default(self, table_name=''):
        return self.to_html( table_name )

    def to_html(self, table_name):
        tmpl = lookup.get_template("table_viewer.html")
        return tmpl.render(table_name=table_name)

class TableIndexResource(object):
    def __init__(self):
        self.tables = [ 'salaries_w_names', 'fizzle', 'bazzle' ]

    exposed = True

    def GET(self):
        return self.to_json()

    def to_json(self):
        response = { 'tables': self.tables }
        return simplejson.dumps( response )

config = {'/':
                {'tools.staticdir.on': True,
                 'tools.staticdir.dir': APP_DIR,
#                 'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                },
        }

def open_page():
    webbrowser.open("http://127.0.0.1:8080/table_viewer?table_name=salaries_w_names")

# DATA_FILE = "bart-salaries/salaries_w_names.csv"
# csvFileData = readCSVFile( DATA_FILE )

class Root(object):
    pass

root = Root()
root.tables = TableResource()
root.table_viewer = TableViewerResource()
root.table_index = TableIndexResource()

dbName = "testdb.db"
tableName = "salaries_w_names"
dbTable = PagedDbTable( dbName, tableName )

cherrypy.engine.subscribe('start', open_page)
# cherrypy.tree.mount( AjaxApp( dbTable ), '/', config=config)
# cherrypy.engine.start()
cherrypy.quickstart( root, '/', config)