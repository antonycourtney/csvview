#!/usr/bin/python
import csv
import json
import sys

with open("bart-salaries/salaries_w_names.csv") as csvfile:
	rd = csv.reader( csvfile )

	colNames = rd.next()
	print "var columns = ["
	firstLine = True
	for c in colNames:
		if ( not firstLine ):
			print ","
		cmap = { 'id': c, 'name': c, 'field': c }
		sys.stdout.write("  ")
		sys.stdout.write( json.dumps( cmap ) )
		firstLine = False;
	print "\n];\n"

	print "var data = [ "
	firstLine = True
	for row in rd:
		if( not firstLine ):
			print ","
		sys.stdout.write( "  " )
		rowMap = dict( zip( colNames, row ) )
		sys.stdout.write( json.dumps( rowMap ) )
		firstLine = False
print "\n];"
		