Changelog
=========

01-10-2014
    - Use fogbugz token for approval form (bubenkoff)
    - Approved tag setting added on the approval form (bubenkoff)

30-09-2014
    - Publish form - list available tags from the fogbugz (bubenkoff)
    - Publish form - use select2 term for filtering the options (bubenkoff)

29-09-2014
    - Impersonate user for Fogbugz communication (bubenkoff)

18-9-2014
    - Don't send an email when publish comments with case assignment for cleaner case history (bubenkoff)

10-9-2014
    - Use message for fogbugz case assignment for better communication (bubenkoff)
    - Added tags field to publish comments form to set fogbugz case tags (bubenkoff)

14-7-2014
    - Give an option to assign the FB case of an issue when submitting comments.
      (esjee)
    - Fixed an issue where the initial value for the subject when publishing comments could be greater than the
        maximum allowed value.
      (esjee)

12-7-2014
    - Added wheel support (generation and installation)
      (bubenkoff)

11-7-2014
    - Fallback to full directory comparison if repositories are not related
      (bubenkoff)

8-07-2014
    - Use common ancestor revision as target when getting diff
      (bubenkoff)
    - Use vcs-specific approach to get the diff instead of comparing exports
      (bubenkoff)

4-07-2014
    - Line numbers provided by prettifyjs
      (bubenkoff)
    - New commits warning message only shows up on issue view, corrected the time when it appears
      (bubenkoff)

1-07-2014
    - Fixed broken code expansion.
      (bubenkoff)
    - Added revision to the bottom of the page, changed base template to mention paylogic codereview.
      (bubenkoff)

25-06-2014
    - Fix 'delete patchset'.
      (esjee)

16-06-2014
    - Added a question to create patchset when there are commits after latest patchset in the issue.
      (bubenkoff)
    - Improved the logic of choosing the original branch to compare with
      (bubenkoff)

5-06-2014
    - Implemented autocompletion for target branch in the gatekeeper approval form
      (bubenkoff)

23-05-2014
    - Initial public release
      (bubenkoff)
