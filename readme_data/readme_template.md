# hdf-json-to-splunk
Splunk plugin to upload Inspec output, Heimdall Tools output, and any other HDF format files to Splunk, for consumption by Heimdall Lite.
The format in which these are uploaded guarantees that they will not be truncated, that they are relatively easy to search, and that they can be easily reconstructed into the original JSON (with filters applied, if one so desires).

Credit to Dan Mirsky and Yarick Tsagoyko of DigitalInfuzion for the initial framework for the plugin, including the S3 integration and the automated file scanning python input, as well as for their assistance and advising on how best to develop the event schema.

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
{report_schema}
```

#### Profile Event structure

```jsonc
{profile_schema}
```

#### Control Event structure

```jsonc
{control_schema}
```

### NOTICE

© 2019 The MITRE Corporation.

Approved for Public Release; Distribution Unlimited. Case Number 18-3678.

### NOTICE

MITRE hereby grants express written permission to use, reproduce, distribute, modify, and otherwise leverage this software to the extent permitted by the licensed terms provided in the LICENSE.md file included with this project.

### NOTICE

This software was produced for the U. S. Government under Contract Number HHSM-500-2012-00008I, and is subject to Federal Acquisition Regulation Clause 52.227-14, Rights in Data-General.

No other use other than that granted to the U. S. Government, or to those acting on behalf of the U. S. Government under that Clause is authorized without the express written permission of The MITRE Corporation.

For further information, please contact The MITRE Corporation, Contracts Management Office, 7515 Colshire Drive, McLean, VA 22102-7539, (703) 983-6000.
