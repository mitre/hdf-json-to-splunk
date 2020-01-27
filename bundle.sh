#!/bin/sh
# Run this prior to releasing any new versions

# Update readme
python build_readme.py

# Pack up
PLUGIN_DIR='hdf_pickup'
cp -r splunk_plugin/ $PLUGIN_DIR
# rm $PLUGIN_DIR/pickup/*
tar -cz $PLUGIN_DIR/* > hdf_splunk_plugin.tar.gz
rm -rf $PLUGIN_DIR