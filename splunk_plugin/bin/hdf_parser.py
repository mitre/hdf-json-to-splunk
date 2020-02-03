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
from util import compute_status, is_waived, is_baseline_profile, find_direct_underlying_profiles, get_descendant_controls
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

        # Our status counts, built as we parse
        self.counts = None

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
        data = copy.deepcopy(self.hdf)
        events = []

        # Reset counts
        self.counts = {}

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
            eval_event_meta = copy.deepcopy(meta)
            eval_event_meta["subtype"] = "header"
            data["meta"] = eval_event_meta
            eval_event = json.dumps(data)
            events.append(eval_event)

            # Then each profile in turn
            for profile in profiles:
                profile_event, profile_control_events = self.construct_profile_events(
                    meta, profile)
                events.append(profile_event)
                events += profile_control_events

        else:
            # It is a profile
            meta["filetype"] = "profile"

            # Decompose the singular profile
            profile_event, control_events = self.construct_profile_events(
                meta, data)
            events.append(profile_event)
            events += control_events

        # Save
        self._events = events

    def print_events(self):
        for event in self.events:
            logger.info('\n' + json.dumps(event, indent=2, sort_keys=True))

    # -> Tuple[str, List[str]]:
    def construct_profile_events(self, meta, profile):
        '''
        Constructs an event string for the profile body,
        as well as a list of control event strings for each control within.
        Returns in the format
        profile_event, control_events[]
        '''
        # Copy our meta, and label it with the sha256
        meta = copy.deepcopy(meta)
        meta["profile_sha256"] = profile["sha256"]

        # Now pluck the controls
        controls = profile["controls"]
        profile["controls"] = []

        # Create yet another meta for the profile, so that we can label
        # labelling its subtype, baseline status
        profile_event_meta = copy.deepcopy(meta)
        profile_event_meta["subtype"] = "profile"

        # Set whether we're baseline
        profile_event_meta["is_baseline"] = is_baseline_profile(
            self.hdf, profile)

        # Set the meta and build the profile event
        profile["meta"] = profile_event_meta
        profile_event = json.dumps(profile)

        # Generate the control events
        control_events = [self.construct_control_event(
            meta, profile, c) for c in controls]

        return profile_event, control_events

    # -> str:
    def construct_control_event(self, meta, profile, control):
        '''
        Constructs an event string for the control body
        '''
        # Copy our meta, and label it with the control id
        meta = copy.deepcopy(meta)
        meta["control_id"] = control["id"]

        # And, though this is not yet strictly necessary
        control_event_meta = copy.deepcopy(meta)
        control_event_meta["subtype"] = "control"

        # Add status / waived
        status = compute_status(control)
        control_event_meta["status"] = status
        control_event_meta["is_waived"] = is_waived(control)

        # Compute descendants
        descendants = get_descendant_controls(self.hdf, profile, control)
        if descendants:
            # We're a baseline if we have no children - if our # descendants is exactly one
            control_event_meta["is_baseline"] = len(descendants) == 1

            # Build up our meta full code
            full_code_segments = []
            for profile, control in descendants:
                name = profile["name"].strip()
                code = (control["code"] or "N/A").strip()
                full_code_segments.append(name + "\n" + code)
            control_event_meta["full_code"] = "\n=====================\n".join(
                full_code_segments)

            # Also set our depth
            control_event_meta["overlay_depth"] = len(descendants) - 1
        else:
            # Ambiguity tells us nothing except that we're definitely not the baseline
            control_event_meta["is_baseline"] = False
            name = profile["name"].strip()
            code = (control["code"] or "N/A").strip()
            control_event_meta["full_code"] = name + "\n" + code

        # Count status iff baseline
        if control_event_meta["is_baseline"]:
            self.counts[status] = self.counts.get(status, 0) + 1

        # Add meta to the control
        control["meta"] = control_event_meta
        return json.dumps(control)


if __name__ == "__main__":
    # We don't care about anything below this, really
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        logger.error(
            'Usage ./hdf_parser.py input_json_file_1 [input_json_file_2] [...]')
        sys.exit(1)

    input_filenames = sys.argv[1:]
    for input_filename in input_filenames:
        logger.info(' >>> Processing File {}'.format(input_filename))
        # Read the file as json
        with open(input_filename, 'r') as f:
            try:
                data = json.load(f)
            except:
                logger.exception('\n !!! Failed to parse file to json !!! \n')
                continue

        # Parse to HDF
        try:
            hdf = HDF(data, input_filename)
            hdf.parse()
        except KeyError as e:
            logger.exception('\n !!! Failed to parse file as HDF !!! \n')
            continue

        # Derive the count filename. This sort of assumes the user is using the count data testing set
        count_filename = input_filename.replace(
            "/raw_data/", "/counts/") + ".info.counts"

        # Try to find a counts file and compare to our results
        try:
            with open(count_filename, 'r') as f:
                count_map = {
                    "failed": "Failed",
                    "passed": "Passed",
                    "no_impact": "Not Applicable",
                    "skipped": "Not Reviewed",
                    "error": "Profile Error",
                }
                count_data = json.load(f)
                failures = []
                for key in count_map:
                    hdf_count = hdf.counts.get(count_map[key], 0)
                    ref_count = count_data[key]["total"]
                    if hdf_count != ref_count:
                        failures.append("{}:{} - Expected {}, got {}".format(
                            input_filename, count_map[key], ref_count, hdf_count))

                if failures:
                    logger.error(
                        "FAILED COUNTING IN {}".format(input_filename))
                    for f in failures:
                        logger.error(f)
        except IOError as e:
            pass
            logger.info(
                "Unable to find counts at path {}".format(count_filename))
