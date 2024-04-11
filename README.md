# Azure Snapshots Copy (CronJob Script)
A script to copy azure snapshots to a specified region and automatically delete them upon expiration.

You can run this tools in cronjob to copy snapshots to specified region periodically

## Run
```bash
$ pip3 install -r requirements.txt

# For test, create rg-test (in azure UI) serves as destination resources group

$ export SUBSCRIPTION_ID=[SUB_ID]
$ export RESOURCE_GROUP=my-nodepool
$ export DESTINATION_REGION="Germany North"
$ export DESTINATION_RESOURCE_GROUP=rg-test

$ az login

# for help
$ python3 azure-snapshots-copy.py -h
usage: azure-snapshots-copy.py [-h] [-s SUBSCRIPTION_ID] [-g RESOURCE_GROUP] [-d DESTINATION_RESOURCE_GROUP] [-r DESTINATION_REGION] [-c CLIENT_ID] [-e CLIENT_SECRET] [-t TENANT_ID] [-i]
                         [-x EXPIRE_DAYS] [-p SNAPSHOT_NAME_PREFIX]

Azure Snapshot Manager

options:
 -h, --help            show this help message and exit
 -s SUBSCRIPTION_ID, --subscription-id SUBSCRIPTION_ID
                       Azure Subscription ID
 -g RESOURCE_GROUP, --resource-group RESOURCE_GROUP
                       Azure Resource Group
 -d DESTINATION_RESOURCE_GROUP, --destination-resource-group DESTINATION_RESOURCE_GROUP
                       Destination Azure Resource Group for copy operation
 -r DESTINATION_REGION, --destination-region DESTINATION_REGION
                       Destination Azure region for copy operation
 -c CLIENT_ID, --client-id CLIENT_ID
                       Azure AD Client ID [Service Principal] (default: None)
 -e CLIENT_SECRET, --client-secret CLIENT_SECRET
                       Azure AD Client Secret [Service Principal] (default: None)
 -t TENANT_ID, --tenant-id TENANT_ID
                       Azure AD Tenant ID [Service Principal] (default: None)
 -i, --skip-snapshots-deletion
                       Skip deletion of expired snapshots (default: False)
 -x EXPIRE_DAYS, --expire-days EXPIRE_DAYS
                       Set expire days to delete snapshots (default: 30)
 -p SNAPSHOT_NAME_PREFIX, --snapshot-name-prefix SNAPSHOT_NAME_PREFIX
                       Prefix name for newly copied snasphots (default: copy-)

# once all environmental vars are set
$ ./azure-snapshots-copy.py

# build docker image
$ docker build -t azure-snapshot-copy:latest .
```

## How it works?

This script primarily utilizes the `SnapshotsOperations` class from the official Azure Python SDK.
https://learn.microsoft.com/en-us/python/api/azure-mgmt-compute/azure.mgmt.compute.v2023_10_02.operations.snapshotsoperations?view=azure-python

* `begin_create_or_update` (Creates or updates a snapshot): Works asynchronously.Once the
  snapshot creation/copy process "begins", the newly created snapshots appear immediately.
  However, Azure internally copies the snapshots, which takes some time depending on the
  snapshot size. You can monitor this copy status by checking the "Completion Percent."

  NOTE: This script does not poll the "Completion Percent" but only checks the
    "Provisioning Status" before moving to the next snapshot copy.
