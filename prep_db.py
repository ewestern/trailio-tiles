from psycopg2 import connect
from math import floor
import requests
import os.path
import os
import subprocess
import glob
import json
import argparse
import zipfile
# import psycopg2.Error

CURRENT = os.getcwd()


def table_exists(connection, table):
  with connection.cursor() as cursor:
    cursor.execute("select * from information_schema.tables where table_name=%s", (table,))
    connection.commit()
    return bool(cursor.rowcount)

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

class Setup(object):
  def __init__(self, configPath, skip):
    with open(configPath, 'rb') as cfg:
      self.config = json.load(cfg)
    dbconfig = self.config['db']
    try:
      self.connection = connect(dbconfig['connection'])
    except Exception:
      subprocess.call(["createdb", dbconfig['dbname']])
      self.connection = connect(dbconfig['connection'])
      with self.connection.cursor() as cursor:
        cursor.execute("create extension postgis")
        self.connection.commit()
    if 'countries' not in skip:
      self.write_countries()
    if 'osm' not in skip:
      self.write_osm()
    if 'elevations' not in skip:
      self.write_elevations()
    # if 'raster' not in skip:
    #   self.make_raster()

  def write_countries(self):
    self.countries = Countries(self.config)

  def write_elevations(self):
    self.elevations = Elevations(self.config, self.connection)

  def write_osm(self):
    self.osm = Osm(self.config)

  # def make_raster(self):
  #   self.raster = Raster(self.config)
  #   self.raster.render_all()


class Countries(object):
  def __init__(self, config):
    db = config['db']
    countries = config['countries']
    path = os.path.join(CURRENT, countries['countries_shp'])
    make_postgres_table(db['dbname'], db['user'], countries['table'], countries['geo_column'], path)
    to_postgres(db['dbname'], db['user'], countries['table'], countries['geo_column'], path)

class Osm(object):
  def __init__(self, config):
    self.config = config
    self._import_osm()

  def _import_osm(self):
    db = self.config['db']
    geo = self.config['geo']
    #r0 = subprocess.call(["imposm", "--proj=" + "EPSG:" + geo['srid'], "--write", "--optimize", "-m", "mapping.py", "-d", db['dbname'],  "-U", db['user'], geo['path']])
    r0 = subprocess.call(["imposm", "--proj=" + "EPSG:" + geo['srid'], "--read", "--write", "--optimize", "-m", "mapping.py", "-d", db['dbname'],  "-U", db['user'], geo['path']])
    if r0:
      raise Exception("Imposm not successful.")

class Elevations(object):
  def __init__(self, config, connection, domain=None):
    self.config = config
    self.connection = connection
    if not domain:
      domain = self._get_domain()
    self._get_elevations(domain)
    self._write_contours()
    self._add_elevation_feet()

  def _get_domain(self):
    sample = self.config['elevations']['sample']
    with self.connection.cursor() as cur:
      # list of all unique x, y integers
      cur.execute("select distinct on (floor(ST_X(geometry)),floor(ST_Y(geometry))) floor(ST_X(geometry)),floor(ST_Y(geometry)) from %s" % (sample['table']))
      return [item for item in cur.fetchall()]

  def _get_elevations(self, coords):
    print "Downloading elevation binaries:"
    self.elevation_names = [('N' if ln > 0 else 'S') + str(abs(int(ln))) + ('W' if la  < 0 else 'E') + str(abs(int(la))) for (la, ln) in coords]
    for i, name in enumerate(self.elevation_names):
       if not os.path.isfile(os.path.join(CURRENT, self.config['elevations']['directory'], name + ".hgt")):
         url = self.config['elevations']['url'] + name + ".hgt.zip"
         r = requests.get(url, stream=True)
         zippath = os.path.join(CURRENT, self.config['elevations']['directory'], name + ".hgt.zip")
         with open(zippath, 'w') as f:
           f.write(r.raw.read())
         with zipfile.ZipFile(zippath, 'r') as zip:
           for item in zip.infolist():
             zip.extract(item, os.path.join(CURRENT, self.config['elevations']['directory']))
         os.remove(zippath)

  def _write_contours(self):
    db = self.config['db']
    elConfig = self.config['elevations']
    setupPath = os.path.join(CURRENT, elConfig['directory'], self.elevation_names[0] + ".hgt")
    names = glob.glob(os.path.join(CURRENT, elConfig['directory'], '*.hgt'))
    print "Write elevation contours."
    for i, hgtPath in enumerate(names):
      coord = hgtPath.split('/')[-1].split('.')[0]
      shpPath = os.path.join(CURRENT, self.config['temp_dir'], coord + ".shp")
      self._make_contour(hgtPath, shpPath, elConfig['contours']['elevation_column'], elConfig['contours']['interval'])
      if i == 0:
      #if not table_exists(self.connection, elConfig['contours']['table']):
        self._make_contour_table(db['dbname'], db['user'], elConfig['contours']['table'], elConfig['contours']['geo_column'], shpPath)
      self._to_postgres(db['dbname'], db['user'], elConfig['contours']['table'], elConfig['contours']['geo_column'], shpPath)
      os.remove(shpPath)
    # self._cleanup()

  def _make_contour(self, hgtPath, shpPath, el_column, interval):
    subprocess.call(['gdal_fillnodata.py', hgtPath])
    subprocess.check_call(["gdal_contour", "-i", interval, "-a", el_column, "-snodata", "-32768", "-q", hgtPath, shpPath])
    #print "gdal contour done %s" % shpPath
    # subprocess.call(["gdal_contour", "-i", interval, "-snodata", "-32768", "-a", el_column, "-f", "PostgreSQL", hgtPath, "PG:dbname=%s user=%s password=%s" % (dbname, user, password)])

  def _to_postgres(self, dbName, user, table, column, path):
    proc = subprocess.Popen(["shp2pgsql", "-a", "-s", "4326", "-g", column, path, table], stdout=subprocess.PIPE)
    sql = proc.communicate()[0]
    fn = "%s.sql" % table
    with open(fn, 'w') as file:
      file.write(sql)
    subprocess.call(["psql", "-q", "-d", dbName, "-f", fn])

  def _make_contour_table(self, dbName, user, table, column, path):
    proc = subprocess.Popen(["shp2pgsql", "-p", "-s", "4326", "-I", "-g", column, path, table], stdout=subprocess.PIPE)
    sql = proc.communicate()[0]
    subprocess.call(["psql", "-q", "-d", dbName, "-c", sql])

  def _add_elevation_feet(self):
    elConfig = self.config['elevations']['contours']
    with self.connection.cursor() as cursor:
      cursor.execute("alter table %s add column %s integer" % (elConfig["table"], elConfig['elevation_column_imperial']))
      cursor.execute("update %s set %s = integer(%s * 3.28084)" % (elConfig["table"], elConfig["elevation_column_imperial"], elConfig["elevation_column"]) )
      self.connection.commit()

# todo:
  # def _cleanup(self):
  #   os.remove(os.path.join(CURRENT, self.config['temp_dir'], "*"))




if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Setup.')
  parser.add_argument('config', help='the path to a config file.')
  parser.add_argument('--skip', nargs= "*", default=[])
  args = parser.parse_args()
  Setup(args.config, args.skip)


# SELECT ST_AsText(geometry), elevation_ft, CASE WHEN (elevation_ft % 1000::integer) = 0 THEN 3 WHEN (elevation_ft % 200::integer) = 0 THEN 2 ELSE 1 END AS class FROM contours
# subprocess.call(["gdal_contour", "-i", interval, "-snodata", "32767", "-a", el_column, "-f", "PostgreSQL", hgtPath, "PG:dbname=%s user=%s password=%s" % (dbname, user, password)])
#   gdal_contour -i 12.192 -snodata -32768 -a elevation -f PostgreSQL "PG:dbname=tiles" 
# update contours set elevation_ft = integer(elevation * 3.28084) 
# "shp2pgsql", "-a", "-s", "4326", "-g", column, path, table
# "shp2pgsql", "-p", "-s", "4326", "-I", "-g", column, path, table
# shp2pgsql -p -s 4326 -I -g geometry  

# reproject NLCD data, add overviews, and copy VRT file (with
# the custom color table).
# gdalwarp -multi -of GTiff \
#     -co ZLEVEL=9 -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BIGTIFF=YES \
#     -t_srs EPSG:900913 $NLCD_DIR/nlcd2006_landcover_2-14-11.img \
#     $NLCD_DIR/nlcd2006.tif
# gdaladdo $NLCD_DIR/nlcd2006.tif 2 4 8 16 32 64
# cp nlcd2006.vrt $NLCD_DIR
# 
