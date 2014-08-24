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

CURRENT = os.getcwd()
#
class Raster(object):
  def __init__(self, config):
    self.config = config
    self.elevation_names = [path.split("/")[-1].split('.')[0] for path in glob.glob(os.path.join(CURRENT, self.config['elevations']['directory'], '*.hgt'))]
    hillshade_path = os.path.join(CURRENT, config['raster']['hillshade_dir'])
    if not os.path.isdir(hillshade_path):
      os.mkdir(hillshade_path)

  def render_all(self):
    self._render_hillshade()
    self._render_final()

  def _render_hillshade(self):
    print "Rendering hillshade:"
    elev = self.config['elevations']
    hillshade_dir = self.config['raster']['hillshade_dir']
    for i, el in enumerate(self.elevation_names):
      print "Rendering file %s of %s" % (i+1, len(self.elevation_names))      
      base = os.path.join(CURRENT, hillshade_dir, el)
      unproj_name = base + ".unproj.tif"
      uncomp_name = base + ".uncomp.tif" 
      subprocess.call(["gdaldem", "hillshade", os.path.join(CURRENT, elev['directory'], el + ".hgt"), unproj_name, "-z", "0.00001"])
      subprocess.call(["gdalwarp", "-r", "cubicspline", "-multi", "-of", "GTiff", unproj_name, uncomp_name])
      tifPath = os.path.join(CURRENT, hillshade_dir, el + ".tif")
      subprocess.call(["gdal_translate", "-of", "GTiff", "-co", "COMPRESS=JPEG", uncomp_name, tifPath])
      subprocess.call(["gdaladdo", "-r", "gauss", tifPath, "2 4 8 16 32"])
      os.remove(unproj_name)
      os.remove(uncomp_name)
 
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
      # os.remove(unProjPath)
      
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
      # os.remove(colormap_path)
      os.remove(hillshade_path)

  def _render_final(self):
    # todo: hmmmm
    print "Build VRT"
    hillshade = self.config['raster']['hillshade_dir']
    os.chdir(os.path.join(CURRENT, hillshade))
    subprocess.call("gdalbuildvrt all.vrt *.tif", shell=True)


  def _cleanup(self):
    pass

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Setup.')
  parser.add_argument('config', help='the path to a config file.')
  args = parser.parse_args()
  with open(args.config, 'rb') as cfg:
    config = json.load(cfg)
  raster = Raster(config)
  raster.render_all()


