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


def is_baseline_profile(execution, profile):
    '''
    Returns a boolean declaring whether this profile is a baseline profile in this report.
    '''
    return len(find_direct_underlying_profiles(execution, profile)) == 0


def profile_control_lookup(profile, control_id):
    '''
    Fetches the specified control from profile, or None
    '''
    for ctrl in profile["controls"]:
        if ctrl.get("id") == control_id:
            return ctrl
    return None


def get_descendant_controls(execution, profile, control):
    '''
    Searches the execution for all controls that contribute to this control.
    Returns this as a list of tuples, each representing the (profile, control) pairing of the control and the profile it came from.
    That is, if this control is a level 3 overlay, this would return [Level 3 (the input control), Level 2 (mid-line), Level 1 (baseline)],
    with each level containing both the control and the appropriate profile
    If this control is a baseline, the result will simply be [the input control].

    If an unclear dependency is found (e.g. multiple underlying profiles have controls with the same exact name, somehow),
    then we return None

    @param :execution: The execution to search through
    @param :profile: The profile from whence profile came. Not strictly necessary, but saves some cycles
    @param :control: The control whose lineage we desire
    '''
    # Init
    result = [(profile, control)]
    id = control["id"]

    # Loop through descendants. The range 100 is to prevent us from getting DDOS'd by a malignant profile with circular parentage
    for _ in range(100):
        profiles_to_check = find_direct_underlying_profiles(execution, profile)
        found = 0
        for p in profiles_to_check:
            possible_control = profile_control_lookup(p, id)

            # If found, count, update our control, update our result, and update our profile
            if possible_control:
                found += 1
                control = possible_control
                profile = p
                result.append((profile, control))
                # Don't break - need to make sure we don't have an ambiguous case

        # Verify that we only found one in children with this id. If more, return None
        if found > 1:
            return None
        # If we didn't find any, then this is as far as we go
        elif found == 0:
            return result


def pluck_meaningful_status(controls):
    """
    Given a list of controls (presumably of the same ID), pick the first non-Profile-error status.
    Failing that, just give profile error
    """
    for control in controls:
        status = control["meta"]["status"]
        if status != "Profile Error":
            return status
    return "Profile Error"


def pluck_longest_full_code(controls):
    """
    Given a list of controls (presumably of the same ID), pick the first non-Profile-error status.
    Failing that, just give [] (Should be impossible if any controls are provided!)
    """
    best = []
    for control in controls:
        fc = control["meta"]["full_code"]
        if len(fc) > len(best):
            best = fc
    return best
