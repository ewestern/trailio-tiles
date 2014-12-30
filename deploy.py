from boto.vpc import VPCConnection
from argparse import ArgumentParser
from boto import rds2


class Setup(object):
  def __init__(self, region, security_group):

    self.region = region
    self.vpc_connection = VPCConnection() 
    groups = {x.name: x for x in self.connection.get_all_security_groups()} 
    self.security_group = group[security_group]
    #subnets = {x.name: x for x in self.vpc_connection.get_all_subnets() } 

  def launch_ec2(self, image_name, instance_type):
    ec2 = EC2(image_name, instance_type)
    # get endpoint

  def launch_rds(self, region 
    rds = RDS(region) 
     
class EC2(object):
  def __init__(self, region, image_name, instance_type):

    self.connection = ec2.connect_to_region(region)
    images = {x.name : x for x in self.connection.get_all_images(owners=["self"])}
    img = images[image_name]
    inst = self.connection.run_instances(
      image_id=img.id,
      instance_type = instance_type,
      subnet_id = sid
    )
    self.id = inst.id
  
class RDS(object):
  def __init__(self, region, instance_class):
    connection = rds2.connect_to_region(region)
    self.endpoints = []
    ss = rconn.describe_db_snapshots()['DescribeDBSnapshotsResponse']['DescribeDBSnapshotsResult']['DBSnapshots'] 
    #groups = rconn.describe_db_subnet_groups()['DescribeDBSubnetGroupsResponse']['DescribeDBSubnetGroupsResult']['DBSubnetGroups']
    #sgroup = {x['DBSubnetGroupName'] : x for x in groups}
    snapshot = max(ss, key=lambda x: x["SnapshotCreateTime"])
    inst = connection.restore_db_instance_from_db_snapshot(
      db_snapsnot_identifier = snapshot['DBSnapshotIdentifier'],
      db_instance_class = 'db.t2.small',
      db_instance_identifier = 'trail-tiles',
      db_subnet_group_name = 'trailio-tiles'
    )
    
    ## when loaded
    instances = connection.describe_db_instances()['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']
    self.endpoints = [x['Endpoint'] for x in instances]
    #endpoints = [x.public_dns_name for x in inst.instances]
     

class Cache(object):
  def __init__(self, region):
    conn = elasticache.connect_to_region(region)
    
 
if __name__ == "__main__":
  parser = ArgumentParser(description = "Deploy Trailio-Tiles")
  parser.add_argument("--region", default = "us-east-1")
  #parser.add_argument("--security", default="trailio-tiles")
  parser.add_argument("--image", default="trailio-tiles")
  parser.add_argument("--instance_type", default="t2.small")
  args = parser.parse_args()
  su = Setup(args.region, args.security)

