#!/usr/bin/env python3

'''
A script to copy azure snapshots to a specified region and automatically delete them upon expiration.
'''

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta, timezone, UTC
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient

__author__ = "veerendra2"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logging.getLogger("azure").setLevel(logging.CRITICAL)

class EnvDefault(argparse.Action):
  def __init__(self, envvar, required=False, default=None, **kwargs):
    if not default and envvar:
      if envvar in os.environ:
        default = os.environ[envvar]
    if required and default:
      required = False
    super(EnvDefault, self).__init__(default=default, required=required,
                                    **kwargs)

  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, values)

class AzureSnapshotManager:
  def __init__(self, credentials, subscription_id, resource_group,
              destination_resource_group, destination_region,
              expire_days, snapshot_name_prefix):
    self.subscription_id = subscription_id
    self.resource_group = resource_group
    self.destination_resource_group = destination_resource_group
    self.destination_region = destination_region
    self.destination_snapshot_name_prefix = snapshot_name_prefix
    self.expire_days = expire_days

    self.compute_client = ComputeManagementClient(credentials, self.subscription_id)
    self.default_source_snapshot_tags = {
      "CopiedRegion": self.destination_region,
      "CrossRegionCopy": "Success"
    }

  def copy_snapshots(self):
    """Copies snaptshots to destination region

    :return: None
    """

    logger.info(f"Fetching disk snapshots in resource group '{self.resource_group}' to copy...")
    snapshots = list(self.compute_client.snapshots.list_by_resource_group(self.resource_group))

    if not snapshots:
      logger.info(f"No snapshots found in resource group '{self.resource_group}'")
      return None

    for snapshot in snapshots:
      try:
        if snapshot.tags["CrossRegionCopy"] == self.default_source_snapshot_tags["CrossRegionCopy"]:
          logger.info(f"Snapshot '{snapshot.name}' already copied to {snapshot.tags['CopiedRegion']}")
          continue
      except (KeyError, TypeError):
        pass

      dst_snapshot_name = self.destination_snapshot_name_prefix + snapshot.name

      logger.info(f"Begin incremental copy '{snapshot.name}' to resource group " +
                  f"'{self.destination_resource_group}' in region '{self.destination_region}'")
      poll_result = self.compute_client.snapshots.begin_create_or_update(
          resource_group_name = self.destination_resource_group,
          snapshot_name = dst_snapshot_name,
          snapshot = {
              "location": self.destination_region,
              "creation_data": {
                  "create_option": "CopyStart",
                  "source_resource_id": snapshot.id
              },
              "sku": {
                # Germany North only support Standard_LRS or set 'snapshot.sku.name'
                "name": "Standard_LRS",
                "tier": snapshot.sku.tier
            },
              "incremental": True
          }
      ).result()

      # add tags if provisioning status is Succeeded
      if poll_result.provisioning_state == "Succeeded":
        logger.info(f"Provisioned snapshot '{poll_result.name}' in region '{poll_result.location}'")
        self._add_tags(snapshot.name)
      else:
        logger.warn(f"Provisioning state for copy snapshot '{poll_result.name}' is "+
                    f"'{poll_result.provisioning_state}'")

  def delete_snapshots(self):
    """Delete snapshots in destination source group

    :return: None
    """
    past_time = (datetime.now(UTC) - timedelta(self.expire_days))

    logger.info(f"Fetching disk snapshots in resource group '{self.destination_resource_group}' to delete...")
    snapshots = self.compute_client.snapshots.list_by_resource_group(self.destination_resource_group)

    for snapshot in snapshots:
      if snapshot.time_created <= past_time:
        logger.info(f"Begin delete snapshot '{snapshot.name}' in " +
                    f"'{self.destination_resource_group}' resource" +
                    f" group, was created on {snapshot.time_created}")
        self.compute_client.snapshots.begin_delete(self.destination_resource_group, snapshot.name)
      else:
        logger.info(f"Snapshot '{snapshot.name}' is not expired, created on " +
                    f"{snapshot.time_created}")

  def _add_tags(self, snapshot_name):
    """Add tags to snapshots

    :param snapshot_name: name of the snapshot
    :return: None
    """
    # fetch existing snapshot info
    snapshot = self.compute_client.snapshots.get(self.resource_group, snapshot_name)

    # append/add tags
    try:
      snapshot.tags.update(self.default_source_snapshot_tags)
    except AttributeError:
      snapshot.tags = self.default_source_snapshot_tags

    poll_result = self.compute_client.snapshots.begin_update(
        resource_group_name = self.resource_group,
        snapshot_name=snapshot_name,
        snapshot=snapshot
      ).result()

    if poll_result.provisioning_state == "Succeeded":
      logger.info(f"Tags added to snapshot '{snapshot_name}'")
    else:
      logger.warn(f"Provisioning stage for update tags on snapshot '{snapshot_name}' is" +
                  f" {poll_result.result().provisioning_state}")

def parse_arguments():
  """Argument parser
  """
  parser = argparse.ArgumentParser(description="Azure Snapshot Manager",
                                  formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("-s", "--subscription-id", envvar='SUBSCRIPTION_ID', action=EnvDefault,
                      required=True, help="Azure Subscription ID")
  parser.add_argument("-g" ,"--resource-group", envvar='RESOURCE_GROUP', action=EnvDefault,
                      required=True, help="Azure Resource Group")
  parser.add_argument("-d", "--destination-resource-group", envvar='DESTINATION_RESOURCE_GROUP',
                      required=True, action=EnvDefault,
                      help="Destination Azure Resource Group for copy operation")
  parser.add_argument("-r", "--destination-region", envvar='DESTINATION_REGION', action=EnvDefault,
                      required=True, help="Destination Azure region for copy operation")

  # Service Principal Authentication
  parser.add_argument("-c", "--client-id", action=EnvDefault, envvar="CLIENT_ID",
                      help="Azure AD Client ID [Service Principal]")
  parser.add_argument("-e", "--client-secret", action=EnvDefault, envvar="CLIENT_SECRET",
                      help="Azure AD Client Secret [Service Principal]")
  parser.add_argument("-t", "--tenant-id", action=EnvDefault, envvar="TENANT_ID",
                      help="Azure AD Tenant ID [Service Principal]")

  parser.add_argument("-i", "--skip-snapshots-deletion", action="store_true",
                      help="Skip deletion of expired snapshots")
  parser.add_argument("-x", "--expire-days", type=int, default=30,
                      help="Set expire days to delete snapshots")
  parser.add_argument("-p", "--snapshot-name-prefix", type=str, default="copy-",
                      help="Prefix name for newly copied snasphots")

  return parser.parse_args()

def authenticate_azure(client_id, client_secret, tenant_id):
  """Azure authentication. If serice principal credentails are not passed, it uses
  default authentication(az login)

  :param client_id: service pricipal client id
  :param client_secret: service pricipal client password
  :param tenant_id: service pricipal tenant id
  :return: azure credentaial object
  """
  try:
    if client_id and client_secret and tenant_id:
      logger.info("Authenticating with service principal")
      return ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    else:
      logger.info("Authenticating with default azure credentials")
      return DefaultAzureCredential()
  except Exception as e:
    logger.error(f"Authentication failed: {e}")
    sys.exit()

if __name__ == "__main__":
  args = parse_arguments()

  az_snapshot_mgmt = AzureSnapshotManager(
    credentials=authenticate_azure(args.client_id, args.client_secret, args.tenant_id),
    subscription_id=args.subscription_id,
    resource_group=args.resource_group,
    destination_resource_group=args.destination_resource_group,
    destination_region=args.destination_region,
    snapshot_name_prefix=args.snapshot_name_prefix,
    expire_days=args.expire_days
  )

  az_snapshot_mgmt.copy_snapshots()

  if not args.skip_snapshots_deletion:
    az_snapshot_mgmt.delete_snapshots()
