#
# A simple CherryPy based RESTful web server for paged access to a table in a sqlite database
# Developed for csvview but should work for any sqlite table

import cherrypy
from mako.template import Template
from mako.lookup import TemplateLookup
import os
import os.path
import simplejson
import sqlite3
import string
import sys
import tempfile
import threading
import webbrowser

lookup = TemplateLookup(directories=['html'])
threadLocal = threading.local()

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
    if cellVal==None:
        return None
    intFormatStr = "{:,d}"
    realFormatStr = "{:,.2f}"
    if columnType=="integer":
        ret = intFormatStr.format( cellVal )
    elif columnType=="real":
        ret = realFormatStr.format( cellVal )
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

    def getDataPage( self, sortCol, sortDir, startRow, rowLimit ):
        dbConn = getDbConn( self.dbName )
        if( sortCol != None and sortCol in self.columnNames and sortDir in ['asc','desc']):
            orderStr = ' order by "' + sortCol + '" ' + sortDir
        else:
            orderStr = ""
        query = self.baseQuery + orderStr + " limit " + str( startRow ) + ", " + str( rowLimit )
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

#
# N.B.:  We're still using a REST-ful (stateless) approach here, but doing so via the default() method.
# We do this because it appears that CherryPy's MethodDispatcher() doesn't allow default() or index()
# methods, which in turn would force us to reify the table hierarchy from the sqllite database as a
# tree of Python objects, which we don't want to do.
# So we just stick with the standard Dispatcher() but this means using default() to provide RESTful
# URIs. 

# Provide RESTful paged access to named table
class TableResource(object):
    def __init__(self, dbName):
        self.dbName = dbName

    @cherrypy.expose
    def default( self, tableName, startRow = 0, rowLimit = 10, sortby = '' ):
        dbTable = PagedDbTable( self.dbName, tableName )     
        # print "startRow = ", startRow, ", rowLimit = ", rowLimit, ", sortby = '", sortby, "'"
        startRow = int( startRow )
        rowLimit = int( rowLimit )
        sortstr = sortby.strip();
        if( len(sortstr) > 0 ):
            [ sortcol, sortdir ] = sortstr.split('+')
        else:
            [ sortcol, sortdir ] = [ None, None ] 
        cherrypy.response.headers['Content-Type'] = 'application/json'
        # rowData = self.dataFile['data'][ startRow : startRow + rowLimit ]
        columnInfo = dbTable.getColumnInfo()
        rowData = dbTable.getDataPage( sortcol, sortdir, startRow, rowLimit )
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


APP_DIR = os.path.abspath(".")
config = {'/':
                {'tools.staticdir.on': True,
                 'tools.staticdir.dir': APP_DIR
                },
        }

def open_page(tableName):
    webbrowser.open("http://127.0.0.1:8080/table_viewer?table_name=" + tableName )

class Root(object):
    pass

def startWebServer( dbName, tableName ):
    root = Root()
    root.tables = TableResource( dbName )
    root.table_viewer = TableViewerResource()

    dbTable = PagedDbTable( dbName, tableName )
    cherrypy.config.update( {'log.screen': False })
    cherrypy.engine.subscribe('start', lambda : open_page( tableName ) )
    cherrypy.quickstart( root, '/', config)
