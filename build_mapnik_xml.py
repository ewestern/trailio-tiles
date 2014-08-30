#! /usr/bin/env python
import argparse
import xml.etree.ElementTree as ET

def make_xml(args):
  tree = ET.parse(args.xml)
  root = tree.getroot()
  datasources = root.findall(".//Datasource")
  items = dict([(k, v) for (k, v) in vars(args).items() if k != "xml"])
  for source in datasources:
    missing = []
    for key, val in items.items():
      s = '*/[@name="%s"]' % key 
      t = source.find('*/[@name="type"]').text
      if t == 'postgis':
        p = source.find(s)
        if p is not None:
          p.text = val
        else:
          missing.append((key, val))
    for key, val in missing:
      p = ET.SubElement(source, 'Parameter')
      p.set('name', key)
      p.text = val
  tree.write(args.xml + '.prod')
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Setup.')
  parser.add_argument('xml', help='the path to an xml file.')
  parser.add_argument('--host', default=None)
  parser.add_argument('--user', default=None)
  parser.add_argument('--password', default=None)
  parser.add_argument('--dbname', default=None)
  parser.add_argument('--port', default=None)
  args = parser.parse_args()
  make_xml(args)
