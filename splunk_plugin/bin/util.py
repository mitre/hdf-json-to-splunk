def compute_status(control):
    '''
    Returns the status for the control
    See https://github.com/mitre/inspecjs/blob/master/src/compat_wrappers.ts for origin of this output spec
    '''
    try:
        # Get results
        results = control["results"]

        # Get statuses
        status_list = [r["status"] for r in results]

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
    Returns whether this control has been waived.
    That is, whether it has a defined "waiver_data" field and said field has a value of True in "skipped_due_to_waiver"
    '''
    try:
        return bool(control["waiver_data"]["skipped_due_to_waiver"])
    except KeyError:
        return False
