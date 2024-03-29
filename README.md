# <u>[DEPRECATED]</u>

This package is deprecated and no longer supported or actively developed by MITRE. Use is NOT RECOMMENDED.

This plugin's features are now natively available in [Heimdall2](https://github.com/mitre/heimdall2) and the [SAF CLI](https://github.com/mitre/saf). 

---

# hdf-json-to-splunk
Splunk plugin to upload Inspec output, Heimdall Tools output, and any other HDF format files to Splunk, for consumption by Heimdall Lite.
The format in which these are uploaded guarantees that they will not be truncated, that they are relatively easy to search, and that they can be easily reconstructed into the original JSON (with filters applied, if one so desires).

Credit to Dan Mirsky and Yarick Tsagoyko of DigitalInfuzion for the initial framework for the plugin, including the S3 integration and the automated file scanning python input, as well as for their assistance and advising on how best to develop the event schema.

## Supported data formats

This plugin supports all data that is able to be read by Heimdall Lite, found here: http://heimdall-lite.mitre.org 

More generally, it will support any data in the broader category of Heimdall Data Format (HDF) data, which is a superset of the Inspec JSON output produced by

`inspec exec <profile> --reporter json`

We recommend uploading data from inspec with as little modification as possible.

## Installation

These steps require you to be an admin.

### To setup the splunk plugin:
 1. First, download the latest release .tar.gz of the plugin from the releases tab of this github project.

 2. Then, open your splunk web dashboard and go to your splunk app settings from the left sidebar.
    ![](readme_data/goto_app_settings.png)

 3. Then, click the "Install app from file" button in the top right.
    ![](readme_data/goto_install_app.png)

 4. Finally, click "Browse" and select the .tar.gz file you downloaded in step one. Only check Upgrade App if you are reinstalling or upgrading this app to a new version. Press "Upload" and the app should be active!
    ![](readme_data/install_app.png)

### Feeding the plugin new data:
 * The plugin will consume and *and delete* any json file put into its `pickup` directory.
 * This directory, if installed via the method above, will be at `/opt/splunk/etc/apps/hdf_splunk_plugin/pickup/` on your splunk server instance.
 * Essentially any method of putting files into that folder - scp, ftp, etc - will work.
 * As a simple not-build-for-production example, we have included the file `s3_sync_cron.sh`, which if enabled via a cron job will fetch all files from that bucket and feed them into the splunk pickup directory.

### Reading this data back out in Heimdall Lite:
 * To actually read the data from Heimdall Lite, some small further changes must be made. CORS protocols will block Heimdall Lite's attempts to connect to the Splunk Server management port, found at https://mysplunkserver.com:8089.
 * To resolve this networking error, you must add the following to your global `server.conf` on the Splunk instance.
    ```
    [httpServer]
    crossOriginSharingPolicy = *
    ```
 * Further information on configuring this, including details on how to set more specific filters than the `*` in the example, can be found here:
    https://docs.splunk.com/Documentation/Splunk/latest/Admin/Serverconf

## More info

### Data Structure produced by the converter

#### Execution Report Header Event structure

```jsonc
{
    "meta": {
        // The Globally Unique Identifier string tying all events in this file together. Keying on this is the best way to get all events in a single execution.",
        "guid": "bXZNMQ3mNOs2PvHFv6Ze48RCdxI2FM",
        // The name of the file that was consumed to produce this event.
        "filename": "E.g. my_profile_results.json",
        // Whether this was the result of inspec exec <profile> or inspec json <profile>, respectively.
        "filetype": "evaluation | profile",
        // This identifies this event as a header event. Note the matching meta field in other event types.
        "subtype": "header",
        // When it was parsed/ingested into the splunk app, in ISO time format. NOT when the profile was started!
        "parse_time": "2020-01-23T01:07:18.795438",
        // The start time of the profile in ISO format, as given by Inspec. Not guaranteed to be present (if no results)
        "start_time": "2020-01-23T01:07:18.795438",
        // the version of the schema used to produce this event.
        "hdf_splunk_schema": "1.0"
    },
    "statistics": {
        // How long this evaluation run took, in seconds
        "duration": 0.501324
    },
    "platform": {
        // The platform release version
        "release": "18.2.0",
        // The platform name
        "name": "mac_os_x"
    },
    // The version of inspec that generated this file
    "version": "3.0.52"
}
```

#### Profile Event structure

```jsonc
{
    "meta": {
        // See Report schema for description,
        "guid": "bXZNMQ3mNOs2PvHFv6Ze48RCdxI2FM",
        // See Report schema for description
        "filetype": "evaluation | profile",
        // See Report schema for description
        "filename": "",
        // This identifies this event as a control event. Note the matching meta field in other event types
        "subtype": "profile",
        // The SHA256 Hash of this profile, as generated by inspec
        "profile_sha256": "4bd9e49391dfd78bec6feeafbe8d212581daac43fcb734473d8eff86c863e219",
        // See Report schema for description
        "parse_time": "",
        // See Report schema for description
        "start_time": "",
        // See Report schema for description
        "hdf_splunk_schema": "",
        // Whether this profile is a baseline - IE, is it being overlayed in this report?
        "is_baseline": true // or false
    },
    "summary": "The profile summary",
    "sha256": "The profile sha hash",
    // What platforms this profile supports. TODO: Document the particular fields
    "supports": [],
    "name": "the-name-of-the-profile",
    "copyright": "The Authors",
    "maintainer": "The Authors",
    "copyright_email": "you@example.com",
    "version": "0.1.0",
    "license": "License. E.g. Apache-2.0",
    "title": "InSpec Profile Title",
    // The name of the parent profile, as would be found in its "name" field. In the case of JSON output, this is the name of the "parent" profile that loaded this "child" profile as a dependency (see below), typically to overlay controls
    "parent_profile": "cms-ars-3.1-moderate-mongodb-enterprise-advanced-3-stig-overlay",
    // List of profiles this profile depends on, either overlaying or combining them (or both). Note that none of these fields are specifically required - all depends on how the dependency is expressed in the profile
    "depends": [
        {
            // The name of the profile this depends on
            "name": "Profile name",
            // A url from which the profile is fetched
            "url": "http://where-the-profile-comes-from.com/data.zip",
            // The git url/uri, if this profile is from a git repository
            "git": "http://github.com/myuser/myprofilerepo.git",
            // The branch that, if this is from github, the build should be cloned from
            "branch": "master",
            // The local path to a profile
            "path": "~/profiles/other_profile",
            // If the profile could not be loaded, why not?
            "skip_message": "We skipped because we could not download!",
            // Whether the profile was "skipped" or "loaded" TODO: verify no other states possible
            "status": "skipped | loaded",
            // The profile supermarket from which this will be fetched
            "supermarket": "Market Name",
            // This field is not well documented in Inspec.
            "compliance": "?"
        }
    ],
    // "Inputs" in modern Inspec parlance, Attributes are the parameters specified at runtime for the profile.
    "attributes": [
        {
            "name": "param_name",
            "options": {
                "default": "default_value",
                // Whether or not it is required
                "required": true,
                // Can be string, number, or boolean.
                "type": "string"
            }
        }
        // Repeat as necessary
    ],
    "groups": [
        {
            // The control ids in the group
            "controls": ["contol_id_1", "control_id_2", "etc."],
            "id": "the id of the group"
        }
    ],
    // Whether the profile was "skipped" or "loaded" TODO: verify no other states possible - possibly "error"?
    "status": "skipped | loaded"
}
```

#### Control Event structure

```jsonc
{
    "meta": {
        // See Report schema for description,
        "guid": "bXZNMQ3mNOs2PvHFv6Ze48RCdxI2FM",
        // See Report schema for description
        "filename": "evaluation | profile",
        // See Report schema for description
        "filetype": "",
        // This identifies this event as a control event. Note the matching meta field in other event types
        "subtype": "control",
        // See Profile for description. Included here so that this control can be associated with its parent profile
        "profile_sha256": "4bd9e49391dfd78bec6feeafbe8d212581daac43fcb734473d8eff86c863e219",
        // The ID of the control. Copied from the main structurem similar to how profile meta includes sha256
        "control_id": "E.g. control_12",
        // See Report schema for description
        "parse_time": "",
        // See Report schema for description
        "start_time": "",
        // See Report schema for description
        "hdf_splunk_schema": "",
        // The controls computed status, based on result statuses. See https://github.com/mitre/inspecjs/blob/master/src/compat_wrappers.ts for explanation
        // Note that overlays will inherit the baseline status, instead of the "proper" result which would always just be Profile Error
        "status": "Passed | Failed | Not Applicable | Not Reviewed | Profile Error",
        // Whether or not this control was waived
        "is_waived": true, // or false
        // Whether this control is the baseline - IE, is it an overlay of a different control in this file?. Can differ from its containing profiles is_baseline
        "is_baseline": true, // or false!
        // How much of an overlay this control is. 0 <==> is_baseline, 1 implies direct overlay to baseline, etc. Will be null if ambiguous
        "overlay_depth": 0, // or 1, 2, 3, ...
        // The full code of this control, created by consolidating overlay code sections all the way down to baseline
        // Note that the baseline will include overlaying code here as well - in generall, all controls with the same id will have
        // the same data here.
        // Do not expect this to have a reliable structure / attempt to parse it directly. Purely for convenience
        "full_code": ["overlay2_name: code", "overlay1_name: code", "baseline_name: code"]
    },
    "code": "The code for the control, not including over/underlays!",
    "desc": "The description of the control",
    "descriptions": [
        {
            "label": "<The description label>",
            "data": "<The description entry>"
        }
        // Repeated for as many specific descriptions are desired
    ],
    "id": "Control id",
    // Control impact, from 0.0 to 1.0
    "impact": 0.0,
    "refs": [
        // Inspec refs, as defined in profile.
    ],
    "results": [
        {
            // Optional: The inspec provided description of this result. Not reliably formatted
            "code_desc": "Auditd Rules with file == \"a.txt\" permissions should not cmp == []",
            // Optional: How many seconds it took to run this result segment
            "run_time": 0.001234, 
            // Required: The start time of this control, in ISO format
            "start_time": "2018-11-21T11:34:45-05:00",
            // Required: The result of the control - did the test pass, fail, or was it ignored?
            "status": "passed | failed | skipped",
            // Optional: The inspec resource that generated this result. See https://www.inspec.io/docs/reference/resources/
            // E.g. if describe(<resource>)
            "resource": "res",
            // Optional: Message describing the result of the test, in words.
            "message": "\nexpected it not to be == []\n     got: []\n\n(compared using `cmp` matcher)\n",
            // Optional: If skipped, a description of why
            "skip_message": "LDAP not enabled using any known mechanisms, this control is Not Applicable.",
            // Optional: If an exception occurred, the content of that exception message
            "exception": "RSpec::Core::MultipleExceptionError",
            // Optional / Nullable: If an exception occurred, the backtrace to that exception
            "backtrace": null // Or an array of strings  ["line1", "line2", ...]

            // There will be as many result objects in this array as there are inspec test blocks
        }
    ],
    "source_location": {
        // The line number at which it was found in the given file
        "line": 0,
        "ref": "The filepath to the .rb file that contains the control"
    },
    "tags": {
        // The check text. Usually present but not guaranteed.
        "check": "Is there \"problem\"?",
        //The fix text. Usually present but again, not guaranteed.
        "fix": "Delete \"problem\"",
        "nist": [
            // The actual nist tag (s). AC-1 provided as an example
            "AC-1",
            // Note that there can be multiple, and they can contain enhancements
            "AT-1 (c)",
            // Typically, the last tag is the revision
            "Rev_4"
        ],
        "other_tag_0": "There can be as many or as few tags as the profile developer wishes",
        "my_tag": "e.x. 1",
        "my_tag_3": "e.x. 2"
        // ... etc.
    }
}
```

### Contributors  

- Charles Hu [Charles Hu](https://github.com/charleshu-8)
- Jacob Henry [Jacob Henry](https://github.com/Mitriol)
- Aaron Lippold [Aaron Lippold](https://github.com/aaronlippold)
- Will Dower [Will Dower](https://github.com/wdower)
- Yarick Tsagoyko [Yarick Tsagoyko](https://github.com/yarick)
- Dan Mirskiy [Dan Mirskiy](https://github.com/mirskiy)

### NOTICE

© 2023 The MITRE Corporation.

Approved for Public Release; Distribution Unlimited. Case Number 18-3678.

### NOTICE

MITRE hereby grants express written permission to use, reproduce, distribute, modify, and otherwise leverage this software to the extent permitted by the licensed terms provided in the LICENSE.md file included with this project.

### NOTICE

This software was produced for the U. S. Government under Contract Number HHSM-500-2012-00008I, and is subject to Federal Acquisition Regulation Clause 52.227-14, Rights in Data-General.

No other use other than that granted to the U. S. Government, or to those acting on behalf of the U. S. Government under that Clause is authorized without the express written permission of The MITRE Corporation.

For further information, please contact The MITRE Corporation, Contracts Management Office, 7515 Colshire Drive, McLean, VA 22102-7539, (703) 983-6000.
