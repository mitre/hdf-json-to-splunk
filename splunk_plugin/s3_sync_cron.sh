#!/bin/bash
# This cron job uses the aws CLI to copy from $S3_BUCKET_ADDRESS to a temporary directory, which is then fed into Splunk
# NOTE!!! This keeps copies of the remaining files, and will not re-copy a file with a duplicate filename. 
# For ongoing uploads to Splunk, this will eventually fill up the disk drive. Consider devising a more nuanced way of fetching S3 files without
# duplication
set -e

date -R
cd /opt/splunk/etc/apps/splunk_hdf_ta/
mkdir -p sync sync.ref 
aws s3 sync --no-progress $S3_BUCKET_ADDRESS sync/
comm -23 <(ls sync/) <(ls sync.ref/) | xargs -d $'\n' sh -c 'for arg do srcPath="$(pwd -P)/sync/$arg"; ln -s "$srcPath" sync.ref/; ln -s "$srcPath" pickup/; done' _
