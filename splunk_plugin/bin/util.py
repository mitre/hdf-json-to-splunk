def compute_status(control):
    '''
    Returns the status for the control, as a str
    See https://github.com/mitre/inspecjs/blob/master/src/compat_wrappers.ts for origin of this output spec
    '''
    try:
        # Get results
        results = control["results"]

        # Get statuses
        status_list = []
        for r in results:
            if r.get("backtrace"):
                status_list.append("error")
            else:
                status_list.append(r.get("status") or "no_status")

        # Determine fate based on statuses
        if "error" in status_list:
            return "Profile Error"
        elif is_waived(control) or control["impact"] == 0:
            # We interject this between profile error conditions because an empty-result waived control is still NA
            return "Not Applicable"
        elif len(status_list) == 0:
            return "Profile Error"
        elif "failed" in status_list:
            return "Failed"
        elif "passed" in status_list:
            return "Passed"
        elif "skipped" in status_list:
            return "Not Reviewed"
        else:
            return "Profile Error"  # Shouldn't get here, but might as well have fallback
    except KeyError:
        return "Profile Error"


def is_waived(control):
    '''
    Returns whether this control has been waived, as a bool
    That is, whether it has a defined "waiver_data" field and said field has a value of True in "skipped_due_to_waiver"
    '''
    try:
        return bool(control["waiver_data"]["skipped_due_to_waiver"])
    except KeyError:
        return False


def is_baseline_profile(profile):
    '''
    Returns a boolean declaring whether this profile is a baseline profile in this report.
    '''
    return "depends" not in profile or profile["depends"] == []


def find_direct_underlying_profiles(execution, profile):
    '''
    Searches execution to find all profiles that are directly depended on by the specified profile.
    Returns them as they are in the parsed json object.
    '''
    if "profiles" not in execution:
        return []

    result = []
    profile_name = profile["name"]
    for profile in execution["profiles"]:
        if profile.get("parent_profile") == profile_name:
            result.append(profile)
    return result
