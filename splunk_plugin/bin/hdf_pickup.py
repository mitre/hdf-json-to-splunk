#!/usr/bin/env python
import os
import sys
import glob
import json
import logging

from splunklib.modularinput import *
from hdf_parser import HDF

try:
    import splunk.mining.dcutils
    logger = splunk.mining.dcutils.getLogger()
    logger.setLevel(logging.INFO)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warn("Using python logger, couldn't import Splunk logger")

app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HDF_DIR = 'pickup'


class HDFScript(Script):
    def get_scheme(self):
        """ Returns scheme for input config """
        scheme = Scheme("HDF Parser Input")
        scheme.description = "Monitor a directory for any HDF json files, parse and delete"
        scheme.use_external_validation = True
        # Script will be called for each input separately
        scheme.use_single_instance = False

        folder_name_arg = Argument(
            name="folder",
            description="Which folder should be monitored for HDF .json files?",
            data_type=Argument.data_type_string,
            # Validate to ensure there's no ../ or anything weird
            validation='match(folder, "^[a-zA-Z0-9_.-]+$")',
            required_on_edit=True,
            required_on_create=True
        )
        scheme.add_argument(folder_name_arg)

        return scheme

    def stream_events(self, inputs, ew):
        # Since we're in single instance mode, there should only be one input,
        # but we still have to access them this way
        for input_name, input_item in inputs.inputs.items():
            folder_name = input_item['folder']
            logger.info("Running input {}. folder {}".format(
                input_name, folder_name))
            folder_path = os.path.join(app_path, HDF_DIR, folder_name)
            if folder_name == 'root':
                folder_path = os.path.join(app_path, HDF_DIR)
                logger.info(
                    "Folder name is root, using {}".format(folder_path))

            # Create folder if it doesn't exist
            if not os.path.isdir(folder_path):
                logger.info("Creating folder {}".format(folder_path))
                os.makedirs(folder_path)
                return

            if not os.access(folder_path, os.W_OK) or not os.access(folder_path, os.X_OK):
                raise Exception(
                    "Incorrect permissions on folder {}, need to be able to delete files".format(folder_path))

            files = glob.glob(os.path.join(folder_path, '*.json'))
            logger.debug("Found files {}".format(files))
            for filepath in files:
                logger.info("Version: " + sys.version)
                logger.info("Parsing file {}".format(filepath))
                if not os.access(filepath, os.R_OK):
                    logger.info(
                        "No read access for {}, skipping".format(filepath))
                    continue

                with open(filepath, 'r') as f:
                    try:
                        data = json.load(f)
                    except ValueError as e:
                        logger.error(
                            "Couldn't parse {} as json, skipping".format(filepath))
                        logger.error(e, exc_info=True)
                        continue

                logger.debug("Loaded json, parsing hdf")
                hdf = HDF(data, os.path.basename(filepath))
                try:
                    hdf.parse()
                    logger.debug("Parsed hdf, writting events")
                    self.write_events(
                        hdf.events, hdf.parse_time, input_name, ew)
                except Exception as e:
                    logger.error("Error while parsing:\n{}".format(e))
                logger.info("Parsed file {}, deleting".format(filepath))
                os.remove(filepath)

    def write_events(self, events, time, input_name, ew):
        # What we actually do for each event
        def f(event_data, done):
            e = Event()
            # Use rules based on the input name
            e.stanza = input_name
            # The data has already been jsonified appropriately
            e.data = event_data
            # The time, similarly, has been formatted
            e.time = time
            # Our event is broken up into many
            e.unbroken = False
            # And it's only done when it's all written out
            e.done = done
            ew.write_event(e)

        # Write all, not emitting "Done" until, well, we're done
        for e in events[:-1]:
            f(e, False)
        f(events[-1], True)


if __name__ == "__main__":
    logger.info("Starting hdf modular input script")
    sys.exit(HDFScript().run(sys.argv))
