#!/usr/bin/python
"""

Create a sqllite db table from a CSV file.
Assume every column is a string for now.

"""

import csv
import os
import sqlite3
import string

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

def parseType( ct, vs): 
    """parse string vs to a Python value based on SQL type named ct
"""
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

filename="bart-salaries/salaries_w_names.csv"
tableName="salaries_w_names"
# dbName = ":memory:"
dbName = "testdb.db"

dbConn = sqlite3.connect(dbName)

with open(filename) as csvfile:
    rd = csv.reader( csvfile )
    colNames = rd.next()
    dataRow0 = rd.next()
    colTypes = map( guessColumnType, dataRow0 )
    # build up Schema string:
    typedCols = map( lambda cn, ct: "'" + cn + "' " + ct, colNames, colTypes )
    schemaStr = string.join( typedCols, ", " )
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

