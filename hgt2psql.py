import argparse
import json
import db
import subprocess 
from os import listdir
import os.path

# INTERVAL="10"
# COLUMN = "elevation"

parser = argparse.ArgumentParser(description='Hgt2Psql.')
parser.add_argument('config', help='the path to a config file.')
parser.add_argument('path', help="the path to elevation data.")
args = parser.parse_args()


def make_contour(hgtPath, shpPath, table, interval):
  
  subprocess.call(["gdal_contour", "-i", interval, "-a", "-snodata", "32767", table, hgtPath, shpPath])

def to_postgres(dbName, user, table, column, path):
  proc = subprocess.Popen(["shp2pgsql", "-a", "-s", "4326", "-g", column, path, table], stdout=subprocess.PIPE)
  sql = proc.communicate()[0]
  fn = "%s.sql" % table
  with open(fn, 'w') as file:
    file.write(sql)
  subprocess.call(["psql", "-q", "-d", dbName, "-f", fn])

def make_postgres_table(dbName, user, table, column, path):
  proc = subprocess.Popen(["shp2pgsql", "-p", "-s", "4326", "-I", "-g", column, path, table], stdout=subprocess.PIPE)
  sql = proc.communicate()[0]

  subprocess.call(["psql", "-q", "-d", dbName, "-c", sql])

def migrate_elevations(configPath, path):
  with open(configPath, 'rb') as cfg:
    config = json.load(cfg)
    user = config["db"]["user"]
    table = config['db']['table']
    dbName = config['db']['dbname']
    database = db.Database(database = dbName, user=user, password=config["db"]["password"])
    initialized = database.check_table(table)
    for name in listdir(path):
      coord = name.split('.')[0]
      filepath = os.path.join(path, "%s.shp" % coord)
      if name.split('.')[1] == "hgt":
        if not os.path.isfile(filepath):
          hgtPath = os.path.join(path, "%s.hgt" % coord)
          make_contour(hgtPath, filepath, table, config['contours']['interval'])
        if not initialized:
          make_postgres_table(dbName, user, table, config['contours']['geo_column'], filepath)
          initialized = True
        to_postgres(dbName, user, table, config['contours']['geo_column'], filepath)  
    # todo: cleanup
if __name__ == "__main__":
  migrate_elevations(args.config, args.path)

