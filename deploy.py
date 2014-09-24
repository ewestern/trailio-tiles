from boto import ec2
from boto.vpc import VPCConnection
from argparse import ArgumentParser


class Setup(object):
  def __init__(self, region, security_group):
    self.connection = ec2.connect_to_region(region)
    self.vpc_connection = VPCConnection() 
    groups = {x.name: x for x in self.connection.get_all_security_groups()} 
    self.security_group = group[security_group]
    subnets = {x.name: x for x in self.vpc_connection.get_all_subnets() } 
    
     
class EC2(object):
  def __init__(self, connection, security_group, image_name, instance_type):
    self.connection = connection
    images = {x.name : x for x in self.connection.get_all_images(owners=["self"])}
    img = images[image_name]
    inst = self.connection.run_instances(
      image_id=img.id,
      security_groups = [security_group],
      instance_type = instance_type 
if __name__ == "__main__":
  parser = ArgumentParser(description = "Deploy Trailio-Tiles")
  parser.add_argument("--region", default = "us-east-1")
  parser.add_argument("--security", default="trailio-tiles")
  parser.add_argument("--image", default="trailio-tiles")
  parser.add_argument("--instance_type", default="t1.small")
  args = parser.parse_args()
  su = Setup(args.region, args.security)

