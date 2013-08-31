# libraries for loading a CSV file into a sqlite database

import atexit
import csv
import os
import os.path
import re
import sqlite3
import string
import sys
import tempfile

class ColType:
    INT = 0
    REAL = 1
    TEXT = 2
    strMap = { INT: 'integer', REAL: 'real', TEXT: 'text' }

# compiled regex to match a float or int:
# Also allows commas and leading $
intRE = re.compile('[-+]?[$]?[0-9,]+')
realRE = re.compile('[-+]?[$]?[0-9,]*\.?[0-9]+([eE][-+]?[0-9]+)?')

def guessColumnType( cg, cs ):
    """Given the current guess (or None) for a column type and cell value string cs
    make a conservative guess at column type.
    We use the order int <: real <: text, and a guess will only become more general.
    TODO: support various date formats....
"""
    if cg==ColType.TEXT:
        return ColType.TEXT
    if len( cs ) == 0:
        return cg   # empty cells don't affect current guess
    if cg==None or cg==ColType.INT:
        match = intRE.match( cs )
        if match and match.start()==0 and match.end()==len( cs ):
            return ColType.INT
    if cg!=ColType.TEXT:
        match = realRE.match( cs )
        if match and match.start()==0 and match.end()==len( cs ):
            return ColType.REAL
    return ColType.TEXT

def genColumnIds( colHeaders ):
    """Use descriptive strings from first (header) row of CSV to generate column identifiers for database.
    Tries to use the first word of each description to generate a human-friendly column name, but falls back 
    to simpler 'col'N if that fails.
    Will fail in an unlikely edge case.
"""
 # try to generate a reasonable field name from the given columnName:
    colNames = []
    colNameMap = {}
    for i, cdesc in enumerate(colHeaders):
        words =  re.findall( '\w+', cdesc )
        if len(words)==0 or words[0] in colNameMap:
            cid = "col" + str(i)
        else:
            cid = words[0]
        colNames.append( ( cid, cdesc ) )
        colNameMap[ cid ] = True
    return colNames

def parseType( ct, vs): 
    """parse string vs to a Python value based on SQL type named ct
"""
    if len(vs)==0 and ct!="text":
        return None
    if ct=="integer":
        # for now: drop all $ and , chars:
        cs = vs.strip().translate( None, "$," )
        ret = int( cs )
    elif ct=="real":
        # for now: drop all $ and , chars:
        cs = vs.strip().translate( None, "$," )
        ret = float( cs )
    else:
        ret = vs
    return ret

def createColumnTable( dbConn, tableName, colIdInfo ):
    """Create a metadata table to retain descriptive column names
"""
    schemaStr = "('id' integer, 'colName' text, 'description' text)"
    colTableName = tableName + "_columnInfo"
    dropStr = "DROP TABLE IF EXISTS " + colTableName
    dbConn.execute( dropStr )
    createStr = "CREATE TABLE " + colTableName + " " + schemaStr
    dbConn.execute( createStr )
    insertStmt = "INSERT INTO " + colTableName + " VALUES ( ?, ?, ? )"
    for id,(colName,colDesc) in enumerate( colIdInfo ):
        rowVals = [ id, colName, colDesc ]
        dbConn.execute( insertStmt, rowVals )

def guessColumnTypes( csvfile, rd, nCols  ):
    """Given a CSV file positioned after header, take a full pass and make a
conservative guess at column types."""
    colTypes = [ None ] * nCols 
    for row in rd:
        colTypes = map( guessColumnType, colTypes, row )
    # now lift the column types:
    def liftCT( ct ):
        if ct==None:
            return ColType.TEXT
        return ct
    colTypes = map( liftCT, colTypes )
    colTypes = map( lambda ct: ColType.strMap[ ct ], colTypes )
    return colTypes


def loadCSVFile( dbName, csvFilePath ):
    """Attempt to open and parse the specified CSV file and load it in to an in-memory sqlite table.
    Returns:  name of sqllite table
"""
    bnm = os.path.basename( csvFilePath )
    (tableName,_)= os.path.splitext( bnm )
    dbConn = sqlite3.connect(dbName)
    with open(csvFilePath) as csvfile:
        rd = csv.reader( csvfile )
        headerRow = rd.next()
        colIdInfo = genColumnIds( headerRow )
        createColumnTable( dbConn, tableName, colIdInfo )
        colNames = map( lambda (cn, _) : cn, colIdInfo )
        colTypes = guessColumnTypes( csvfile, rd, len( colIdInfo ) )
        # now rewind to beginning of file:
        csvfile.seek( 0 )
        rd = csv.reader( csvfile )
        rd.next()   # skip header

        # build up Schema string:
        typedCols = map( lambda cn, ct: "'" + cn + "' " + ct, colNames, colTypes )
        schemaStr = string.join( typedCols, ", " )
        dropStr = "DROP TABLE IF EXISTS " + tableName
        dbConn.execute( dropStr )    
        createStr = "CREATE TABLE " + tableName + " ( " + schemaStr + " )"
        print createStr
        dbConn.execute( createStr )
        qs = ['?'] * len(colNames)
        insertStmt = "INSERT INTO " + tableName + " VALUES ( " + string.join( qs, ", " ) + " ) "
        for row in rd:
            rowVals = map( parseType, colTypes, row )
            dbConn.execute( insertStmt, rowVals )
        dbConn.commit()
    return tableName

def createTempDb():
    """Create a sqlite database backed by a file in /tmp.  Attempts to remove db on exit."""
    tf = tempfile.NamedTemporaryFile(prefix='csvview',suffix='.db',dir='/tmp')
    dbName = tf.name
    atexit.register( lambda f: f.close(), tf )
    return dbName

if __name__ == "main":
    dbName = createTempDb()
    tableName = loadCSVFile( dbName, sys.argv[1] )

