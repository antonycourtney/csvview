#!/usr/bin/python
import csv

with open("bart-salaries/salaries_w_names.csv") as csvfile:
	rd = csv.reader( csvfile )
	for i in range(20):
		row = rd.next()
		print ', '.join( row )
		