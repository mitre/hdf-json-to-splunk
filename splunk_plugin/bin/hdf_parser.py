#!/usr/bin/env python
import os
import re
import sys
import pwd
import json
import socket
import logging
import traceback
import time
import copy
# from typing import List, Tuple
from datetime import datetime
import random

try:
    import splunk.mining.dcutils
    logger = splunk.mining.dcutils.getLogger()
except ImportError:
    logger = logging.getLogger(__name__)
    logger.info("Using python logger, couldn't import Splunk logger")


class HDF:
    def __init__(self, hdf, filename):
        self.hdf = hdf
        self.filename = filename
        self._events = None

        # Both of the below times are in ISO format
        self.parse_time = None
        self.start_time = None

    @property
    def events(self):  # -> List[str]:
        if self._events is None:
            raise RuntimeError("You must call parse() before getting events")
        return self._events

    def parse(self):
        """
        Parses hdf data into a list of events, and stores them into this objects events property
        """
        # Get copy and init list. This is done so accidentally parsing twice won't break everything
        data = copy.copy(self.hdf)
        events = []

        # Set the parse time
        self.parse_time = datetime.now().isoformat()

        # Init meta
        meta = {
            "filename": self.filename,
            "parse_time": self.parse_time,
            "hdf_splunk_schema": "1.0"
        }

        # There is a change (albeit infintesimally low) that our parse time EXACTLY matches a different executions parse time
        # which, if the filenames are also the same, makes distinguishing them very different!
        # As an added mitigation to this, we tack on a line that effectively reduces this risk by a ton
        # It also works as a unique id, if that interests you
        alphanum = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        # Generate a random 30-char string
        discriminator = "".join(
            [str(random.sample(alphanum, 1)[0]) for _ in range(30)])
        meta["guid"] = discriminator

        # Determine whether its an evaluation or a profile
        if 'profiles' in data:
            # It is an evaluation. Mark as such
            meta["filetype"] = "evaluation"

            # Remove the profiles from the top level
            profiles = data['profiles']
            data["profiles"] = []

            # Scrobble through control results until we find one with a start time, and save it
            # Also add it to the header
            try:
                for profile in profiles:
                    for control in profile["controls"]:
                        for result in control["results"]:
                            # Parse out timestamp
                            try:
                                timestamp = result["start_time"]
                                self.start_time = timestamp
                                meta["start_time"] = timestamp
                                raise StopIteration()
                            except KeyError:
                                # We didn't find a timestamp here. In theory one could be found elsewhere.
                                # This is unlikely, but the performance cost is minimal to keep looking so we'll try anyways
                                pass
            except (TypeError, KeyError, StopIteration):
                # Aside from stopiteration, these other two probably just mean the results are weirdly formatted.
                # Should we keep parsing? Probably not, but best to upload the data regardless
                pass

            # Make an event from the body
            # Copy the meta for local modification
            eval_event_meta = copy.copy(meta)
            eval_event_meta["subtype"] = "header"
            data["meta"] = eval_event_meta
            eval_event = json.dumps(data)
            events.append(eval_event)

            # Then each profile in turn
            for profile in profiles:
                profile_event, profile_control_events = construct_profile_events(
                    meta, profile)
                events.append(profile_event)
                events += profile_control_events

        else:
            # It is a profile
            meta["filetype"] = "profile"

            # Decompose the singular profile
            profile_event, control_events = construct_profile_events(
                meta, data)
            events.append(profile_event)
            events += control_events

        # Save
        self._events = events

    def print_events(self):
        for event in self.events:
            logger.info('\n' + json.dumps(event, indent=2, sort_keys=True))


def construct_profile_events(meta, profile):  # -> Tuple[str, List[str]]:
    '''
    Constructs an event string for the profile body, 
    as well as a list of control event strings for each control within.
    Returns in the format
    profile_event, control_events[]
    '''
    # Copy our meta, and label it with the sha256
    meta = copy.copy(meta)
    meta["profile_sha256"] = profile["sha256"]

    # Now pluck the controls
    controls = profile["controls"]
    profile["controls"] = []

    # Create yet another meta for the profile, so that we can label
    # labelling its subtype (and potentially more attributes later down the line)
    profile_event_meta = copy.copy(meta)
    profile_event_meta["subtype"] = "profile"

    # Set the meta and build the profile event
    profile["meta"] = profile_event_meta
    profile_event = json.dumps(profile)

    # Generate the control events
    control_events = [construct_control_event(meta, c) for c in controls]

    return profile_event, control_events


def construct_control_event(meta, control):  # -> str:
    '''
    Constructs an event string for the control body
    '''
    # Copy our meta, and label it with the control id
    meta = copy.copy(meta)
    meta["control_id"] = control["id"]

    # And, though this is not yet strictly necessary
    control_event_meta = copy.copy(meta)
    control_event_meta["subtype"] = "control"

    # Add meta to the control
    control["meta"] = control_event_meta
    return json.dumps(control)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) != 2:
        logger.error('Usage ./hdf_parser.py input_json_file')
        sys.exit(1)

    input_filename = sys.argv[1]
    logger.info('\nProcessing File {}'.format(input_filename))
    with open(input_filename, 'r') as f:
        data = json.load(f)

    hdf = HDF(data, input_filename)
    hdf.parse()
    logger.info('Extracted events:')
    hdf.print_events()
