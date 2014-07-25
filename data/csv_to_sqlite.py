#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import re
import sys, csv
import datetime, time

db_file = "ports.db"

#vslRecID_n,vsl_m,vslTrgtPosnLat_q,vslTrgtPosnLong_q,vslCourse_q,vslTy_c,vslLen_q,vslGT_q,vslBre_q,vslSpeed_q, timeStamp_dt
#52589,,          1.308571696,     103.7263107,      0,          TU,     54,      1373,   0,       0,          Mar 31 2014 12:01:46:270AM
#68346,,          1.289833188,     104.0870514,      84.72840881,TU,     19,      89,     0,       2.988201141,Mar 31 2014 12:14:02:826AM

structure_ais = dict(
  table="AIS",
  skip_first=True,
  ignore_zero_vid=True,
  fields=[
    "vslRecID=vid INT",           # - vessel ID. 0 means we're missing the vessel receiver ID
    "vsl_m=0 CHAR(1)",            # - vessel manager but unused
    "vslTrgtPosnLat_q=lat REAL",  # - vessel latitude
    "vslTrgtPosnLong_q=lon REAL", # - vessel longitude
    "vslCourse_q=course REAL",    # - vessel direction
    "vslTy_c=country CHAR(2)",    # - vessel country of registration
    "vslLen_q=l INT",             # - vessel length
    "vslGT_q=gt INT",             # - gross tonnage (e.g. 6000 means volume in cubic feet)
    "vslBre_q=beam INT",          # - vessel beam
    "vslSpeed_q=speed REAL",      # - vessel speed in knots at the time of measurement
    "timeStamp_dt=ts TS_AIS"      # - timestamp when this record was made
  ],
  structure_csv=[],
  fields_sql=[],
  create_sql="",
)

# more PTMS_vslMvmts_v2.csv 
#vslRecID_n,vslMvId_n,vslMv_n,mvAdvSrc_c,mvToa_dt,           mvStm_dt,           mvEtm_dt,           mvSt_i,mvTy_c,mvOpnl_i,locnRespFr_c,locnRespTo_c,locnFr_c,locnTo_c,locnGridFr_c,mvDft_q,timeStamp_dt
#56062,     4380232,       40,         V,Jun 30 2014 11:57PM,Jun 30 2014 10:47PM,Jun 30 2014 11:57PM,C,     I,     I,       J,           J,           DG1,     APSPT,               ,40,     Jun 30 2014 11:57PM
#362051,    115655,        21,         V,Jun 30 2014 11:57PM,Jun 30 2014 10:47PM,Jun 30 2014 11:57PM,C,     I,     I,       J,           J,           DG1,     APSPT,               ,30,     Jun 30 2014 11:57PM
#53061,     4164024,       54,         V,Jun 30 2014 10:43PM,Jun 30 2014 10:43PM,Jun 30 2014 11:35PM,C,     I,     I,       E,           E,           AEPA,    AEPBB,               ,40,     Jun 30 2014 11:55PM

structure_mv = dict(
  table="mv",
  skip_first=True,
  ignore_zero_vid=True,
  fields=[
	"vslRecID_n=vid INT", # - Unique identifier of vessel
	"vslMvId_n=mvid INT", # - Movement id of vessel movement
	"vslMv_n=mvnum INT",  # - movement number ???
	"mvAdvSrc_c=advice_source CHAR(1)",  # - Source of Advice
	"mvToa_dt=advice_ts TS_MV", #- Movement Time of Advice
	"mvStm_dt=start_ts TS_MV",  #- Start date/time of vessel movement
	"mvEtm_dt=end_ts TS_MV",    #- End date/time of vessel movement
	"mvSt_i=status CHAR(1)",   #- Movement Status (Where 'X' = Cancelled, 'C' = Closed &'O' = Open)
	"mvTy_c=mv_type CHAR(1)",  #- Movement Type code (Where A' = Arrival, 'T' = Transit, 'I' = Intraport & 'D' = Departed)
	"mvOpnl_i=mv_open CHAR(1)", # ??? - (Where A' = Arrival, 'T' = Transit, 'I' = Intraport & 'D' = Departed)
	"locnRespFr_c=resp_from CHAR(1)", #- Location From Responsibility (Where J' = Jurong, 'W' = West, 'E' = East, 'K' = Keppel, 'B' = Brani & ‘C’ = Changi)
	"locnRespTo_c=resp_to CHAR(1)",   #- Location To Responsibility   (Where J' = Jurong, 'W' = West, 'E' = East, 'K' = Keppel, 'B' = Brani & ‘C’ = Changi)
	"locnFr_c=loc_from CHAR(5)", #- Location from
	"locnTo_c=loc_to CHAR(5)",   #- Location to
	"locnGridFr_c=0 INT",     #- Location Grid Reference
	"mvDft_q=draft INT",      #- Draft
	"timeStamp_dt=ts TS_MV",  #- TimeStamp
  ],
  structure_csv=[],
  fields_sql=[],
  create_sql="",
)

# head -5 ../data/MPA_GEOGRAPHY.csv 
#MKT_ID,NAME,                               SHAPE,                                                                                                                                                                                             TYPE,     LOCN_C, STATUS_I
#  1.37,VERY LARGE CRUDE CARRIER ANCHORAGE,"MDSYS.SDO_GEOMETRY(2003,8307,NULLMDSYS.SDO_ELEM_INFO_ARRAY(1,1003,1)MDSYS.SDO_ORDINATE_ARRAY(103.641333,1.221483,103.65835,1.229667,103.657967,1.216117,103.646667,1.210683,103.641333,1.221483))",ANCHORAGE,AVLCC,  null
#  1.36,LNG/LPG ANCHORAGE,                 "MDSYS.SDO_GEOMETRY(2003,8307,NULLMDSYS.SDO_ELEM_INFO_ARRAY(1,1003,1)MDSYS.SDO_ORDINATE_ARRAY(103.627683,1.230117,103.652583,1.24175,103.65835,1.229667,103.63355,1.217733,103.627683,1.230117))",  ANCHORAGE,ALGAS,  null
#  1.35,WEST JURONG ANCHORAGE,             "MDSYS.SDO_GEOMETRY(2003,8307,NULLMDSYS.SDO_ELEM_INFO_ARRAY(1,1003,1)MDSYS.SDO_ORDINATE_ARRAY(103.62375,1.238417,103.648633,1.250033,103.652583,1.24175,103.627683,1.230117,103.62375,1.238417))",  ANCHORAGE,AWJ,    null
#  1.34,SUDONG HOLDING ANCHORAGE,          "MDSYS.SDO_GEOMETRY(2003,8307,NULLMDSYS.SDO_ELEM_INFO_ARRAY(1,1003,1)MDSYS.SDO_ORDINATE_ARRAY(103.671283,1.204617,103.672867,1.2039,103.671217,1.19705,103.66375,1.198967,103.671283,1.204617))",   ANCHORAGE,ASH,    null


structure_geog = dict(
  table="geog",
  skip_first=True,
  ignore_zero_vid=True,
  fields=[
	"MKT_ID=loc_id REAL", # - Unique identifier of geography
	"NAME=name TEXT",     # - Name of location
	"SHAPE=shape TEXT",   # - Shape of geometry
	"TYPE=loc_type TEXT", # - Type of location i.e. anchorage or Berth
	"LOCN_C=loc CHAR(5)", # - Location code
  ],
  structure_csv=[],
  fields_sql=[],
  create_sql="",
)

class CSVtoSQLite():
  #db_create_real = re.sub(r"\#.*?\n", "\n", """
  DB_HINTS_PARSE = r"^(.*?)\=(.*?)\s+(.*)"
  
  def __init__(self, db_structure):
    sql_create=[]
    sql_fields=[]
    sql_places=[]
    structure=[]
    for c in db_structure['fields']:
      m = re.match(self.DB_HINTS_PARSE, c)
      if m is not None:
        (csv_field, sql_field, typ) = (m.group(1), m.group(2), m.group(3) )
        structure.append( dict(csv = csv_field, sql = sql_field, typ = typ) )
        
        if sql_field == "0": continue
        if typ == "TS_AIS": typ = "INT" # Conversion will happen below
        if typ == "TS_MV":  typ = "INT" # Conversion will happen below
        print "%s - %s - %s" % (csv_field, sql_field, typ)
        sql_create.append("%s %s" % (sql_field, typ))
        sql_fields.append(sql_field)
        sql_places.append('?')
        
    db_structure['structure_csv'] = structure
    db_structure['create_sql'] = ("CREATE TABLE %s (" % (db_structure['table'])) + ", \n".join(sql_create) + (");")
    db_structure['fields_sql'] = sql_fields
    db_structure['places_sql'] = sql_places
    self.db_structure = db_structure

  def create_if_not_there(self):
    r = connection.execute("SELECT * FROM sqlite_master WHERE type = 'table' AND name = ?", (self.db_structure['table'],))
    if r.fetchone() is None:
      connection.execute(self.db_structure['create_sql'])

  def load_csv(self, filename):
    #reader = csv.DictReader(open(filename))
    reader = csv.reader(open(filename))
    if self.db_structure['skip_first']: 
      throwaway = reader.next()
      
    cols   = ','.join(self.db_structure['fields_sql'])
    places = ','.join(self.db_structure['places_sql'])
    insert = "INSERT INTO %s (%s) VALUES (%s)" % (self.db_structure['table'], cols, places)
    #print insert
    for row in reader:
      entry = []
      skip_row = False
      for (c,v) in zip(self.db_structure['structure_csv'], row):
        if c['sql'] == "0": continue
        if c['sql'] == "vid" and v=="0" and self.db_structure['ignore_zero_vid']: skip_row=True
        
        #print "%s = %s" % (c['sql'], v)
        
        # https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
        if c['typ'] == "TS_AIS": 
          #print "DATE:" + v
          ts = datetime.datetime.strptime(v, "%b %d %Y %I:%M:%S:%f%p")  # 'Apr 30 2014 12:00:42:240AM'
          #v = "datetime(%s, 'unixepoch')" % (time.mktime(ts.timetuple()),)
          v = time.mktime(ts.timetuple())
          
        if c['typ'] == "TS_MV" and len(v)>0: 
          #print "DATE:" + v
          ts = datetime.datetime.strptime(v, "%b %d %Y %I:%M%p")  # Jun 30 2014 11:57PM  
          v = time.mktime(ts.timetuple())
          
        entry.append(v)
        
      if not skip_row:
        #print insert
        #print entry
        connection.execute(insert, entry)
      if reader.line_num % 10000 == 0 :
        print "%30s : %6dk" % (filename, reader.line_num/1000)  
    connection.commit()

# http://www.tutorialspoint.com/sqlite/sqlite_python.htm
connection = sqlite3.connect(db_file)

dataset = ''
if len(sys.argv)<2:
  print """Usage:
python csv_to_sqlite.py {ais,mv,geog}

Layout:
./db/csv_to_sqlite.py    # This script
./db/ports.db            # The sqlite database populated
./data/AIS/YYYY-MM/*.csv # AIS data
"""
else:
  dataset = sys.argv[1]

if dataset.lower() == 'ais':
  table=CSVtoSQLite(structure_ais)

  table.create_if_not_there()
  
  import os

  for d in ['2014-01', '2014-02', '2014-03', '2014-04', '2014-05', '2014-06', ]:
	p="../data/AIS/%s/" % (d,)
	l = []
	for (dirpath, dirnames, filenames) in os.walk(p):
		l.extend(sorted(filenames))
		break

	for f in l:
		print p+f
		table.load_csv(p+f)
	
  #table.load_csv("../data/AIS/2014-05/PTMS_curTrgtP3History_03-May-2014.csv")

if dataset.lower() == 'mv':
  table=CSVtoSQLite(structure_mv)
  table.create_if_not_there()
  table.load_csv("../data/PTMS_vslMvmts_v2.csv")

if dataset.lower() == 'geog':
  table=CSVtoSQLite(structure_geog)
  table.create_if_not_there()
  table.load_csv("../data/MPA_GEOGRAPHY.csv")


connection.close()

#system("""echo -e ".mode csv\n.import ../data/AIS/2014-05/PTMS_curTrgtP3History_01-May-2014.csv AIS_RAW" | sqlite3 ports.db""")
#system("""echo -e ".import ../data/AIS/2014-05/PTMS_curTrgtP3History_01-May-2014.csv AIS_RAW" | sqlite3 -csv ports.db""")

"""
## https://gist.github.com/rgrp/5199059

# ID INT PRIMARY KEY     NOT NULL,
# NAME           TEXT    NOT NULL,
# AGE            INT     NOT NULL,
# ADDRESS        CHAR(50),
# SALARY         REAL

## http://www.tutorialspoint.com/sqlite/sqlite_indexes.htm
#CREATE INDEX index_name
#on table_name (column1, column2);
"""
