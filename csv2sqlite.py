#!/usr/bin/python
"""

Create a sqllite db table from a CSV file.
Assume every column is a string for now.

"""

import csv
import os
import sqlite3
import string
import re

def guessColumnType( vs ):
    # for now: drop all $ and , chars:
    cs = vs.translate( None, "$," ).strip()
    # strip out .:
    nds = cs.translate( None, ".")
    if nds.isdigit():
        if len(nds)==len(cs):
            return "integer"
        else:
            return "real"
    return "text"


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

filename="salaries_w_names.csv"
tableName="salaries_w_names"
# dbName = ":memory:"
dbName = "testdb.db"

dbConn = sqlite3.connect(dbName)
with open(filename) as csvfile:
    rd = csv.reader( csvfile )
    headerRow = rd.next()

    colIdInfo = genColumnIds( headerRow )

    print "Column ids: ", colIdInfo

    createColumnTable( dbConn, tableName, colIdInfo )

    dataRow0 = rd.next()
    colNames = map( lambda (cn, _) : cn, colIdInfo )
    colTypes = map( guessColumnType, dataRow0 )

    # build up Schema string:
    typedCols = map( lambda cn, ct: "'" + cn + "' " + ct, colNames, colTypes )
    schemaStr = string.join( typedCols, ", " )
    dropStr = "DROP TABLE IF EXISTS " + tableName
    print dropStr
    dbConn.execute( dropStr )    
    createStr = "CREATE TABLE " + tableName + " ( " + schemaStr + " )"
    print createStr
    dbConn.execute( createStr )
    qs = ['?'] * len(colNames)
    insertStmt = "INSERT INTO " + tableName + " VALUES ( " + string.join( qs, ", " ) + " ) "
    valsRow0 = map(parseType, colTypes, dataRow0 )
    dbConn.execute( insertStmt, valsRow0 )

    for row in rd:
        rowVals = map( parseType, colTypes, row )
        dbConn.execute( insertStmt, rowVals )

    # dbConn.executemany( insertStmt, rd )
    dbConn.commit()

query = "select * from " + tableName + "  order by 'Total Compensation' desc limit 5"
print "Executing ", query, ":" 
c = dbConn.execute( query )
for r in c:
    print r

