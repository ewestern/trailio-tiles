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

def update_progress(progress):
    print '\r[{0}] {1}%'.format('#'*(progress/10), progress)

def table_exists(self, connection, table):
  with connection.cursor() as cursor:
    cursor.execute("select * from information_schema.tables where table_name=%s", (table,))
    connection.commit()
    return bool(cursor.rowcount)

class Setup(object):
  def __init__(self, configPath, skip):
    with open(configPath, 'rb') as cfg:
      self.config = json.load(cfg)
    dbconfig = self.config['db']
    try:
      self.connection = connect(database=dbconfig['dbname'], user=dbconfig['user'], password=dbconfig['password'])
    except Exception:
      subprocess.call(["createdb", dbconfig['dbname']])
      self.connection = connect(database=dbconfig['dbname'], user=dbconfig['user'], password=dbconfig['password'])
      with self.connection.cursor() as cursor:
        cursor.execute("create extension postgis")
        self.connection.commit()
    if 'osm' not in skip:
      self.write_osm()
    if 'elevations' not in skip:
      self.write_elevations()
    if 'raster' not in skip:
      self.make_raster()

  def write_elevations(self):
    self.elevations = Elevations(self.config, self.connection)

  def write_osm(self):
    self.osm = Osm(self.config)

  def make_raster(self):
    self.raster = Raster(self.config)
    self.raster.render_all()

class Osm(object):
  def __init__(self, config):
    self.config = config
    self._import_osm()

  def _import_osm(self):
    db = self.config['db']
    geo = self.config['geo']
    # r0 = subprocess.call(["imposm", "--proj=" + "EPSG:" + geo['srid'], "--write", "--optimize", "-m", "mapping.py", "-d", db['dbname'],  "-U", db['user'], geo['path']])
    r0 = subprocess.call(["imposm", "--proj=" + "EPSG:" + geo['srid'], "--read", "--write", "--optimize", "-m", "mapping.py", "-d", db['dbname'],  "-U", db['user'], geo['path']])
    if r0:
      raise Exception("Imposm not successful.")

class Elevations(object):
  def __init__(self, config, connection, domain=None):
    self.config = config
    self.connection = connection
    if not domain:
      domain = self._get_domain()
    # self._get_elevations(domain)
    self._write_contours()
    # self._write_raster()

  def _get_domain(self):
    sample = self.config['elevations']['sample']
    with self.connection.cursor() as cur:
      # cur.execute("select ST_AsGeoJson(ST_ConvexHull(ST_Collect(%s))) as shape from %s" % (sample['column'], sample['table']))
      cur.execute("select distinct on (floor(ST_X(geometry)),floor(ST_Y(geometry))) floor(ST_X(geometry)),floor(ST_Y(geometry)) from %s" % (sample['table']))
      return [item for item in cur.fetchall()]
      # geoj = cur.fetchone()
      # return [(int(floor(c[1])), int(floor(c[0]))) for c in json.loads(geoj[0])['coordinates'][0]
      # ]
  def _get_elevations(self, coords):
    print "Downloading elevation binaries:"
    # self.elevation_names = [('N' if ln > 0 else 'S') + str(abs(int(ln))) + ('W' if la  < 0 else 'E') + str(abs(int(la))) for (la, ln) in coords]
    self.elevation_names = ["N36W119"]
    for i, name in enumerate(self.elevation_names):
      if not os.path.isfile(os.path.join(CURRENT, self.config['elevations']['directory'], name + ".hgt")):
        url = self.config['elevations']['url'] + name + ".hgt.zip"
        print url
        r = requests.get(url, stream=True)
# 
        zippath = os.path.join(CURRENT, self.config['elevations']['directory'], name + ".hgt.zip")
        with open(zippath, 'w') as f:
          f.write(r.raw.read())
        with zipfile.ZipFile(zippath, 'r') as zip:
          for item in zip.infolist():
            zip.extract(item, os.path.join(CURRENT, self.config['elevations']['directory']))
          # print [z.filename for z in zip.infolist()]
        os.remove(zippath)
      # update_progress(i / len(self.elevation_names * 100))

  def _write_contours(self):
    db = self.config['db']
    elConfig = self.config['elevations']
    # setupPath = os.path.join(CURRENT, elConfig['directory'], self.elevation_names[0] + ".hgt")
    names = glob.glob(os.path.join(CURRENT, elConfig['directory'], '*.hgt'))
    print "Write elevation contours."
    # with self.connection.cursor() as cursor:
    #   cursor.execute("")
    for i, hgtPath in enumerate(names):
      # coord = fn.split('/')[-1].split('.')[0]
      # hgtPath = os.path.join(CURRENT, elConfig['directory'], fn)
      # shpPath = os.path.join(CURRENT, self.config['temp_dir'])
      # shpPath = os.path.join(CURRENT, self.config['temp_dir'], coord + ".shp")
      self._make_contour(db['dbname'], db['user'], db['password'], hgtPath, elConfig['contours']['elevation_column'], elConfig['contours']['interval'])
      # if not self._table_exists(elConfig['contours']['table']):
      #   self._make_contour_table(db['dbname'], db['user'], elConfig['contours']['table'], elConfig['contours']['geo_column'], setupPath)
      # self._to_postgres(db['dbname'], db['user'], elConfig['contours']['table'], elConfig['contours']['geo_column'], shpPath)
    # self._cleanup()

  def _make_contour(self, dbname, user, password, hgtPath, el_column, interval):
    subprocess.call(["gdal_contour", "-i", interval, "-snodata", "32767", "-a", el_column, "-f", "PostgreSQL", hgtPath, "PG:dbname=%s user=%s password=%s" % (dbname, user, password)])
    # subprocess.call(["gdal_contour", "-i", interval, "-a", el_column, "-snodata", "32767", hgtPath, shpPath])
  # def _make_contour(self, hgtPath, shpPath, el_column, interval):
  #   subprocess.call(["gdal_contour", "-i", interval, "-a", el_column, "-snodata", "32767", hgtPath, shpPath])



  # def _to_postgres(self, dbName, user, table, column, path):
  #   proc = subprocess.Popen(["shp2pgsql", "-a", "-s", "4326", "-g", column, path, table], stdout=subprocess.PIPE)
  #   sql = proc.communicate()[0]
  #   fn = "%s.sql" % table
  #   with open(fn, 'w') as file:
  #     file.write(sql)
  #   subprocess.call(["psql", "-q", "-d", dbName, "-f", fn])

  # def _make_contour_table(self, dbName, user, table, column, path):
  #   proc = subprocess.Popen(["shp2pgsql", "-p", "-s", "4326", "-I", "-g", column, path, table], stdout=subprocess.PIPE)
  #   sql = proc.communicate()[0]
  #   subprocess.call(["psql", "-q", "-d", dbName, "-c", sql])
  #   with self.connection.cursor() as cursor:
  #     cursor.execute("alter table contours add column elevation_ft integer")
  #     self.connection.commit()
  # def _add_elevation_feet()

# todo:
  # def _cleanup(self):
  #   os.remove(os.path.join(CURRENT, self.config['temp_dir'], "*"))


class Raster(object):
  def __init__(self, config):
    self.config = config
    self.elevation_names = [path.split("/")[-1].split('.')[0] for path in glob.glob(os.path.join(CURRENT, self.config['elevations']['directory'], '*.hgt'))]
    hillshade_path = os.path.join(CURRENT, config['raster']['hillshade_dir'])
    if not os.path.isdir(hillshade_path):
      os.mkdir(hillshade_path)
    colormap_path = os.path.join(CURRENT, config['raster']['colormap_dir'])
    if not os.path.isdir(colormap_path):
      os.mkdir(colormap_path)
    relief_path = os.path.join(CURRENT, config['raster']['relief_dir'])
    if not os.path.isdir(relief_path):
      os.mkdir(relief_path)

  def render_all(self):
    self._render_hillshade()
    self._render_colormap()
    self._render_relief()
    self._render_final()

  def _render_hillshade(self):
    print "Rendering hillshade:"
    elev = self.config['elevations']
    hillshade_dir = self.config['raster']['hillshade_dir']
    print self.config['raster']
    for i, el in enumerate(self.elevation_names):

      print "Rendering file %s of %s" % (i+1, len(self.elevation_names))      
      base = os.path.join(CURRENT, hillshade_dir, el)
      print base
      unproj_name = base + ".unproj.tif"
      # make unprojected tif in hillshade_dir
      subprocess.call(["gdaldem", "hillshade", os.path.join(CURRENT, elev['directory'], el + ".hgt"), unproj_name, "-z", "0.00001"])
      uncomp_name = base + ".uncomp.tif" 
      subprocess.call(["gdalwarp", "-t_srs", self.config['geo']['proj4'], "-r", "cubicspline", "-multi", "-of", "GTiff", unproj_name, uncomp_name])
      os.remove(unproj_name)
      # keep uncompressed tif
      tifPath = os.path.join(CURRENT, hillshade_dir, el + ".tif")
      subprocess.call(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=JPEG", uncomp_name, tifPath])
      subprocess.call(["gdaladdo", "-r", "gauss", tifPath, "2 4 8 16 32"])

  def _render_colormap(self):
    print "Rendering colormap"
    elConfig = self.config['elevations']
    rasterConfig = self.config['raster']
    colormap_dir = rasterConfig['colormap_dir']
    for i, el in enumerate(self.elevation_names):
      print "Rendering file %s of %s" % (i+1, len(self.elevation_names))
      input = os.path.join(CURRENT, elConfig['directory'], el + ".hgt")
      unProjPath = os.path.join(CURRENT, colormap_dir, el + ".unproj.tif")
      subprocess.call(["gdaldem", "color-relief", input, rasterConfig['color_file'], unProjPath])
      unCompPath = os.path.join(CURRENT, colormap_dir, el + ".uncomp.tif")
      subprocess.call(["gdalwarp", "-t_srs", self.config['geo']['proj4'], "-r", "cubicspline", "-multi", "-of", "GTiff", unProjPath, unCompPath])
      os.remove(unProjPath)
      
  def _render_relief(self):
    print "Rendering relief"
    for i, name in enumerate(self.elevation_names):      
      print "Rendering file %s of %s" % (i + 1, len(self.elevation_names))
      relief_dir = self.config['raster']['relief_dir']
      colormap_path = os.path.join(CURRENT, self.config['raster']['colormap_dir'], name + ".uncomp.tif")
      hillshade_path = os.path.join(CURRENT, self.config['raster']['hillshade_dir'], name + ".uncomp.tif")
      base = os.path.join(CURRENT, relief_dir, name)
      png_out = base + ".png"
      # creates wld file
      subprocess.call(["gdal_translate", "-of", "PNG", "-co", "WORLDFILE=YES", colormap_path, png_out])

      subprocess.call(["convert", colormap_path, "-modulate", "120", "\(", hillshade_path, "-level", "70,95%", "+level", "0%,80%", "\)", "-compose", "screen", "composite", "\(",hillshade_path, "-level", "0,75%", "+level", "40%,100%", "\)","-compose", "multiply", "-composite", "-modulate", "92", "-define", "png:color-type=2", png_out])
      tiff_out = base + ".tif"
      subprocess.call(["gdal_translate", "-a_srs", self.config['geo']['proj4'], "-of", "GTiff", "-co", "COMPRESS=JPEG", png_out, tiff_out])
      subprocess.call(["gdaladdo", "-r", "gauss", tiff_out, "2 4 8 16 32"])
      os.remove(png_out)
      os.remove(base + ".png.aux.xml")
      os.remove(base + ".wld")
      os.remove(colormap_path)
      os.remove(hillshade_path)

  def _render_final(self):
    # todo: hmmmm
    print "Build VRT"
    hillshade = self.config['raster']['hillshade_dir']
    relief = self.config['raster']['relief_dir']    
    os.chdir(os.path.join(CURRENT, hillshade))
    subprocess.call("gdalbuildvrt all.vrt *.tif", shell=True)
    os.chdir(os.path.join(CURRENT, relief))
    subprocess.call("gdalbuildvrt all.vrt *.tif", shell=True)
    # convert vrt into geotiff
    # gdal_translate -of GTiff  /data/aeronav/sec/master.virt /data/aeronav/sec/master.tif


  def _cleanup(self):
    pass


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Setup.')
  parser.add_argument('config', help='the path to a config file.')
  parser.add_argument('--skip', nargs= "*", default=[])
  args = parser.parse_args()
  Setup(args.config, args.skip)


# SELECT ST_AsText(geometry), elevation_ft, CASE WHEN (elevation_ft % 1000::integer) = 0 THEN 3 WHEN (elevation_ft % 200::integer) = 0 THEN 2 ELSE 1 END AS class FROM contours

# alter table contours add column elevation_ft integer;
# update contours set elevation_ft = integer(elevation * 3.28084) 


# reproject NLCD data, add overviews, and copy VRT file (with
# the custom color table).
# gdalwarp -multi -of GTiff \
#     -co ZLEVEL=9 -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BIGTIFF=YES \
#     -t_srs EPSG:900913 $NLCD_DIR/nlcd2006_landcover_2-14-11.img \
#     $NLCD_DIR/nlcd2006.tif
# gdaladdo $NLCD_DIR/nlcd2006.tif 2 4 8 16 32 64
# cp nlcd2006.vrt $NLCD_DIR
