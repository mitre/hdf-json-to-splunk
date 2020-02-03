# ${project-name} Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## 1.2.0

This change adds some new meta fields, some tests, and some minor fixes to the previous set of changes
 - "hdf_parser.py" can now be run on the command line against tests in the "tests" directory to verify status counts are accurate to HDF standards
 - Fixed "status" field for controls to be accurate to HDF standards
 - Fixed "is_baseline" in both profiles and controls to be more tolerant to strange dependency structures
 - Added "overlay_depth" meta field to controls events as a more granular way of determining how many levels of overlaying that event represents
 - Added "full_code" meta field to controls that provides a record of all code - from baseline AND from each overlay - relevant to that event
 - Changed "status" and "full_code" to be shared across all events of that control ID, so that regardless of whether you're looking at baseline or final, you'll get good data.
   - This will likely be the case for any new meta fields that aren't directly relevant to overlay layering
   

## 1.1.0

This set of additions was aimed at improving the experience of working with HDF data directly.

- Added schemas (see README) to give a rough overview of what data one can expect to find in each type of event.
- Added more meta tags to aid in creating pure splunk dashboards.
  - The "status" field for controls gives the Heimdall "Passed" | "Failed" | "Not Applicable" | "Not Reviewed" | "Profile Error" status of each control
  - The "waived" field for controls specified whether or not they were waived
  - The "is_baseline" field for profiles demarcates profiles which are not themselves overlays.
  - The "is_baseline" field for controls is similar, except it specifies whether that specific control is overlaying another control, regardless of whether or not its parent is an overlay.

## 1.0.1

- Added missing conf files to actually make the app run on other peoples machines (oops)

## 1.0.0

- Initial commit