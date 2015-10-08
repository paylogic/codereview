"""Paylogic codereview custom views."""
import os
import re
import shutil
import uuid

import fogbugz

from django import db as django_db
from django.conf import settings
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.contrib.messages import api as messages_api
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseServerError, HttpResponseRedirect, HttpResponse

from google.appengine.api import users
from google.appengine.ext import db

from codereview import models, views
from codereview.engine import ParsePatchSet

from paylogic import measurements
from paylogic.vcs import GuessVCS, GitVCS
from paylogic.forms import GatekeeperApprove, PublishForm

import logging
import logging.handlers
logging.root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
handler = logging.handlers.SysLogHandler(
    facility=logging.handlers.SysLogHandler.LOG_LOCAL5, address='/dev/log')
handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT, None))
logging.root.addHandler(handler)

BINARY_FILES_PATH = os.path.join(settings.MEDIA_ROOT, 'binary_files')


def token_required(func):
    """Decorator that returns an error unless correct api token is passed.

    :param func: `function` object to decorate.

    :return: new decorated `function` object.
    """
    def token_wrapper(request, *args, **kwds):
        if request.POST.get('token') != settings.API_TOKEN:
            raise PermissionDenied('`API token` is missing or wrong.')
        return func(request, *args, **kwds)

    return token_wrapper


def user_has_fogbugz_token(user):
    """Return `True` if user has valid fogbugz token stored in the profile."""
    try:
        return bool(user.fogbugzprofile.token)
    except Exception:
        return False


fogbugz_token_required = user_passes_test(user_has_fogbugz_token, '/accounts/login')
"""Decorator that redirects to a special fogbugz login page to get and store fogbugz token in the user's profile."""


def log(msg, *args):
    """Logging helper to record memory usage.

    :param msg: `str` message.
    """
    msg %= args
    mem_use = get_memory_usage() / 1024 / 1024
    logging.root.debug('%s (memory usage: %s KB)' % (msg, mem_use))

_units = {'KB': 1024, 'MB': 1024 ** 2, 'GB': 1024 ** 3}
_handle = _handle = open('/proc/%d/status' % os.getpid())


def get_memory_usage():
    """Get current process memory usage.

    :return: `str` human readable amount of memory used.
    """
    global _units, _handle
    try:
        for line in _handle:
            if line.startswith('VmSize:'):
                label, count, unit = line.split()
                return int(count) * _units[unit.upper()]
    except:
        return 0
    finally:
        _handle.seek(0)


class attrdict(dict):

    """Simple item-to-attribute mapping."""

    def __getattr__(self, key):
        """Map all items to attributes."""
        return self[key]


def parse_branch_vcs_info(branch, default_prefix):
    """Parse vcs information.

    :param branch: full branch string including repo url.

    :return: `tuple` in form: (vcs, path, revision, is_local, supports_simple_cloning)
    """
    for prefix in ['', default_prefix]:
        prefixed_branch = prefix + branch
        for vcs, definition in settings.VCS.items():
            regex = definition['regex']
            if regex.match(prefixed_branch):
                try:
                    path = regex.search(
                        prefixed_branch).groups()[-1]
                    revision = definition['default_branch']
                except ValueError:
                    continue
                if '#' in path:
                    parts = path.split('#')
                    if len(parts) == 2:
                        path, revision = path.split('#')
                    else:
                        continue
                if not os.path.isdir(path):
                    try_path = os.path.join(definition['base_dir'], path)
                    if os.path.isdir(try_path):
                        path = try_path
                return (
                    vcs, path, revision, definition['supports_direct_export'] and os.path.exists(path),
                    definition['supports_simple_cloning'])

    raise ValueError('Invalid branch format: {0}'.format(branch))


def get_complete_diff(target, target_revision, source, source_revision, is_related):
    """Get the complete diff string given 2 repositories and revisions.

    :param target: `VersionControlSystem` object of the target repo
    :param target_revision: `str` revision of the target repo to compare
    :param source: `VersionControlSystem` object of the source repo
    :param source_revision: `str` revision of the target repo to compare
    :param is_related: `bool` if repositories are related between each other (cloned)

    :return: `tuple` in form ('diff string', 'target export path', 'source export path')
    """
    target_export_path = source_export_path = None
    try:
        target_export_path = os.path.join(
            settings.TEMP_FOLDER, uuid.uuid4().hex)
        log("Exporting target copy to {0}".format(target_export_path))
        target.Export(target_revision, target_export_path)
        log("Exported target copy")

        source_export_path = os.path.join(
            settings.TEMP_FOLDER, uuid.uuid4().hex)
        log("Exporting source to {0}".format(source_export_path))
        source.Export(source_revision, source_export_path)
        log("Exported source")
        log("Generating diff with target_revision={target_revision}, source_revision={source_revision}".format(
            target_revision=target_revision, source_revision=source_revision))
        if is_related:
            complete_diff = source.GenerateDiff(
                target_revision,
                source_revision,
                files_to_skip=settings.CODEREVIEW_IGNORED_FILES)
        else:
            complete_diff = (GitVCS(
                attrdict({'revision': target_revision}),
                target_export_path)
                .GenerateDiff(
                    target_revision,
                    source_path=source_export_path,
                    files_to_skip=settings.CODEREVIEW_IGNORED_FILES))
        log("Finished generating diff!")
        return complete_diff, target_export_path, source_export_path
    except Exception:
        # on any error, clean up temporary export folders
        for path in target_export_path, source_export_path:
            if path and not settings.DEBUG:
                log("Cleaning up temporary export {0}".format(path))
                shutil.rmtree(path, ignore_errors=True)
                log("Finished cleaning up temporary export {0}".format(path))
        raise


def check_repositories_related(source, target, target_revision):
    """Check if repositories are related in given revisions.

    :param source: `VersionControlSystem` object of the source repo
    :param target: `VersionControlSystem` object of the target repo
    :param target_revision: `string` target repository revision, can be branch name, or hash, or bookmark

    :return: `True` if repositories are realted, `False` otherwise
    """
    try:
        source_target_revision = source.CheckRevision(revision=target_revision).strip()
        target_common_ancestor = target.GetCommonAncestor(source_target_revision)
        if target_common_ancestor == source_target_revision:
            raise RuntimeError('target and source revisions are same')
    except RuntimeError:
        return False
    return True


def get_source_target_revisions(source, source_revision, target, target_revision, supports_simple_cloning):
    """Get source and target revisions.

    :param source: `VersionControlSystem` object of the source repo
    :param source_revision: `string` source repository revision, can be branch name, or hash, or bookmark
    :param target: `VersionControlSystem` object of the target repo
    :param target_revision: `string` target repository revision, can be branch name, or hash, or bookmark
    :param supports_simple_cloning: `bool` True if source repo support simple cloning,
        so we can use it to get target revision (hash) from target branch
    :return: `tuple` in form ('source_revision_hash', 'target_revision_hash', 'is_related')
    """
    source_revision = source.CheckRevision().strip()
    original_target_revision = target.CheckRevision().strip()
    is_related = check_repositories_related(source, target, target_revision)
    try:
        target_revision = source.GetCommonAncestor(target_revision)
        if target_revision == source_revision:
            raise RuntimeError('target and source revisions are same')
    except RuntimeError:
        target_revision = original_target_revision
        is_related = False

    return source_revision, target_revision, is_related


def generate_diff(original_branch, feature_branch):
    """Get full diff between given original and feature branches.

    :param original_branch: branch definition string, deferred by settings
    :param feature_branch:  branch definition string, deferred by settings

    :return: string diff in svn format
    """
    source_vcs, source_url, source_revision, source_branch_is_local, supports_simple_cloning = parse_branch_vcs_info(
        feature_branch, settings.FEATURE_BRANCH_DEFAULT_PREFIX)

    target_vcs, target_url, target_revision, target_branch_is_local, _ = parse_branch_vcs_info(
        original_branch, settings.ORIGINAL_BRANCH_DEFAULT_PREFIX)

    log('source revision: %s' % source_revision)
    log('target revision: %s' % target_revision)

    target = GuessVCS(
        attrdict({'revision': target_revision, 'vcs': target_vcs}), target_url)
    source = GuessVCS(
        attrdict({'revision': source_revision, 'vcs': source_vcs}), source_url)
    target_path = source_path = None
    try:
        if not target_branch_is_local:
            target_path = os.path.join(settings.TEMP_FOLDER, uuid.uuid4().hex)
            if not os.path.exists(target_path):
                os.makedirs(target_path)
            target = target.Clone(target_path)
            target.Checkout()

        if not source_branch_is_local:
            source_path = os.path.join(settings.TEMP_FOLDER, uuid.uuid4().hex)
            if not os.path.exists(source_path):
                os.makedirs(source_path)
            source = source.Clone(source_path)
            source.Checkout()

        source_revision, target_revision, is_related = get_source_target_revisions(
            source, source_revision, target, target_revision, supports_simple_cloning)
        complete_diff, target_export_path, source_export_path = get_complete_diff(
            target, target_revision, source, source_revision, is_related)
        return (
            source_url, target_url, complete_diff, target, target_export_path,
            source_revision, source_export_path)
    finally:
        for path in target_path, source_path:
            if path and not settings.DEBUG:
                log("Cleaning up temporary clone {0}".format(path))
                shutil.rmtree(path, ignore_errors=True)
                log("Finished cleaning up temporary clone {0}".format(path))


def get_fogbugz_case_info(request, case_number):
    """Get Fogbugz case information.

    :param: case_number: `int` Fogbugz case number.

    :return: `tuple` in form
        ('case_number', 'case_title', 'original_branch', 'feature_branch', 'ci_project', 'target_branch')
    """
    try:
        token = request.user.fogbugzprofile.token
    except Exception:
        return (None, None, None, None, None, None)
    fogbugz_instance = fogbugz.FogBugz(settings.FOGBUGZ_URL, token=token)
    resp = fogbugz_instance.search(
        q='ixBug:"{0}"'.format(case_number),
        cols=','.join([
            'sTitle',
            settings.FOGBUGZ_ORIGINAL_BRANCH_FIELD_ID,
            settings.FOGBUGZ_FEATURE_BRANCH_FIELD_ID,
            settings.FOGBUGZ_CI_PROJECT_FIELD_ID,
            settings.FOGBUGZ_TARGET_BRANCH_FIELD_ID]))

    def get_field(field):
        value = getattr(resp, field)
        if value is not None:
            return value.text or value.string
        else:
            return ''

    return (
        case_number,
        get_field('stitle'),
        get_field(settings.FOGBUGZ_ORIGINAL_BRANCH_FIELD_ID),
        get_field(settings.FOGBUGZ_FEATURE_BRANCH_FIELD_ID),
        get_field(settings.FOGBUGZ_CI_PROJECT_FIELD_ID),
        get_field(settings.FOGBUGZ_TARGET_BRANCH_FIELD_ID),
    )


def get_fogbugz_assignees(request, case_number):
    """Get a list of people that a given case has been assigned to."""
    fogbugz_instance = fogbugz.FogBugz(settings.FOGBUGZ_URL, token=request.user.fogbugzprofile.token)
    resp = fogbugz_instance.search(q=case_number, cols='events')
    possible_assignees = []
    fetched_person_ids = set()
    events = resp.findAll('event')
    events.reverse()
    for event in events:
        try:
            person_id = int(event.find('ixpersonassignedto').text)
            if person_id == 0:  # Special id signifying invalid user.
                raise ValueError
        except ValueError:
            continue

        if person_id in fetched_person_ids:
            # Already added this person.
            continue

        person_name = fogbugz_instance.viewPerson(ixPerson=person_id).find('sfullname').text
        fetched_person_ids.add(person_id)
        if request.REQUEST.get('term', '').lower() in person_name.lower():
            possible_assignees.append((person_id, person_name))

    if len(possible_assignees) >= 2:
        return (
            # Person who assigned review
            [possible_assignees[1]] +
            # Reviewer
            [possible_assignees[0]] +
            # Everybody else
            possible_assignees[2:]
        )
    else:
        return possible_assignees


def fogbugz_assign_case(request, case_number, target, message, tags):
    """Assign a fogbugz case."""
    fogbugz_instance = fogbugz.FogBugz(settings.FOGBUGZ_URL, token=request.user.fogbugzprofile.token)
    fogbugz_instance.assign(ixBug=case_number, ixPersonAssignedTo=target, sEvent=message, sTags=','.join(tags))


def get_fogbugz_tags(request, case_number=None):
    """Get a list of all available or just case's tags."""
    fogbugz_instance = fogbugz.FogBugz(settings.FOGBUGZ_URL, token=request.user.fogbugzprofile.token)
    if case_number:
        resp = fogbugz_instance.search(q=case_number, cols='tags')
    else:
        resp = fogbugz_instance.listTags()
    return [
        tag.string.strip() for tag in resp.findAll('tag')
        if request.REQUEST.get('term', '').lower() in tag.string.lower()]


def get_issue(request, case_number, case_title):
    """Get/create codereview issue based on fogbugz case information.

    :param case_number: `str` Fogbugz case number
    :param case_title:  `str` Fogbugz case title

    :return: `Issue` object which corresponds to a given case_number.
    """
    log("process_codereview_from_fogbugz(): Querying issues")
    issue_desc_id = '(Case {0}) Review: '.format(case_number)
    issue_desc_complete = issue_desc_id + case_title
    try:
        issue = models.Issue.objects.raw(
            'select * from codereview_issue where subject like "{subject}%%" {options}'.format(
                subject=issue_desc_id,
                options='for update' if 'sqlite' not in django_db.connection.settings_dict['ENGINE'] else ''))[0]
    except IndexError:
        issue = None
    log("Querying users for admin")
    user = request.user or users.User.objects.filter(username='admin')[0]
    if issue:
        if issue.closed:
            raise RuntimeError(
                'Issue already closed, cannot be edited anymore.')
        if issue.processing:
            raise RuntimeError('Cannot handle multiple submit requests for the same Fogbugz case.')

        if issue.subject != issue_desc_complete:
            issue.subject = issue_desc_complete

        if issue.description != issue_desc_complete:
            issue.description = issue_desc_complete
    else:
        log("Creating issue instance")
        issue = models.Issue(subject=issue_desc_complete,
                             description=issue_desc_complete,
                             private=False,
                             owner=user,
                             n_comments=0)
        log("Putting instance")

    issue.processing = True
    issue.save()

    return issue


def create_file_content(patch, exp_path, filename):
    """Create file content of the patch.

    :param patch: `Patch` object to create content for
    :param exp_path: `str` base export folder path to use for file reading
    :param filename: `str` filename for file reading

    :return: `Patch` object with the content read from given filename.
    """
    file_path = os.path.join(exp_path, filename).encode('utf-8')
    args = {'text': ''}

    if os.path.exists(file_path):
        if patch.is_binary:
            storage_name = uuid.uuid4().hex
            if not os.path.exists(BINARY_FILES_PATH):
                os.makedirs(BINARY_FILES_PATH)
            shutil.copy2(
                file_path, os.path.join(BINARY_FILES_PATH, storage_name))
            args['data'] = storage_name
        else:
            try:
                with open(file_path) as fd:
                    text = fd.read()
            except IOError:
                text = ''
            args['text'] = text
    content = models.Content(is_uploaded=True, **args)
    content.put()
    return content


def fill_original_files(patches, target_export_path, source_export_path):
    """Fill patches with original files.

    :param patches: `list` of `Patch` objects to fill file content into
    :param target_export_path: `str` path of the exported target repository to get file content from
    :param source_export_path `str` path of the exported source repository to get file content from
    """
    for index, patch in enumerate(patches):
        log("process_codereview_from_fogbugz(): Munging patch set #{0}".format(index))
        for attr, exp_path, filename in [
                ('content', target_export_path, patch.old_filename or patch.filename),
                ('patched_content', source_export_path, patch.filename)]:
            content = getattr(patch, attr)
            if not content and filename:
                content = create_file_content(patch, exp_path, filename)
                setattr(patch, attr, content)
        patch.put()


@fogbugz_token_required
@views.login_required
@permission_required('codereview.add_issue')
def process_codereview_from_fogbugz(request):
    """Create/update codereview issue given the fogbugz case.

    :param request: HTTP request.
    """
    # get information from the fogbugz case
    case_number, case_title, original_branch, feature_branch, _, target_branch = get_fogbugz_case_info(
        request, request.REQUEST['case'])

    # get codereview issue
    issue = get_issue(request, case_number, case_title)

    source_export_path = target_export_path = None
    try:
        # get the diff
        (source_url, target_url, complete_diff, vcs, target_export_path,
            source_revision, source_export_path) = generate_diff(original_branch, feature_branch)

        # validate the diff
        for validator in settings.CODEREVIEW_VALIDATORS:
            validator(complete_diff)

        complete_diff = unicode(complete_diff, 'utf-8', 'replace')

        issue.latest_patch_rev = source_revision
        issue.base = source_url
        issue.put()

        log("Creating patch set instance")
        patchset = models.PatchSet(
            issue=issue, data=complete_diff, parent=issue, revision=source_revision)
        patchset.put()
        log("Created patch set instance!")

        log("Parsing patch set")
        patches = ParsePatchSet(patchset)
        log("Parsed patch set")

        if not patches:
            return HttpResponseServerError('Looks like there is no difference between provided branches.')

        db.put(patches)
        fill_original_files(patches, target_export_path, source_export_path)
        return HttpResponseRedirect('/%s/show' % issue.id)
    finally:
        for path in target_export_path, source_export_path:
            if path and not settings.DEBUG:
                shutil.rmtree(path, ignore_errors=True)
        issue.processing = False
        issue.save()


@views.login_required
@permission_required('codereview.view_issue')
def find_codereview_from_fogbugz(request):
    """Find the codereview issue and redirect to it's show view.

    If found sucesssfully, then redirect to a show view of the issue

    :param request: HTTP request.
    """
    case_number = request.GET.get('case', None)
    try:
        case_number = long(case_number)
    except ValueError:
        case_number = 0

    if case_number <= 0:
        return HttpResponseServerError('Error: please specify a valid case number.')

    issue_desc_id = '(Case ' + str(case_number) + ') Review: '
    try:
        issue = models.Issue.objects.get(subject__startswith=issue_desc_id)
    except models.Issue.DoesNotExist:
        return HttpResponseServerError('Error: please specify a valid case number.')

    return HttpResponseRedirect('/%s/show' % issue.id)


def mark_issue_approved(request, issue, case_id, target_branch):
    """Mark issue's latest revision as approved.

    :param issue: `Issue` object to mark it's latest revision as approved
    :param case_id: `str` id of the Fogbugz case to assign the case to Mergekeepers user
    :param target_branch: `str` target branch to merge approved revision into.
    """
    fogbugz_instance = fogbugz.FogBugz(settings.FOGBUGZ_URL, token=request.user.fogbugzprofile.token)

    # get information from the fogbugz case
    _, _, _, _, ci_project, _ = get_fogbugz_case_info(request, case_id)

    if not ci_project or ci_project == '--':
        raise RuntimeError(
            'You need to set CI Project field in the Fogbugz case '
            '<a href="{settings.FOGBUGZ_URL}default.asp?{case_id}" target="_blank">{case_id}</a>. '
            'Please do so and try again.'.format(
                case_id=case_id, settings=settings))

    latest_patchset = issue.latest_patchset
    if not latest_patchset or issue.latest_reviewed_rev == issue.latest_patch_rev:
        raise RuntimeError('No patchset found to approve.')

    issue.latest_reviewed_rev = issue.latest_patch_rev
    issue.save()
    latest_patchset.revision = issue.latest_patch_rev
    latest_patchset.save()

    tags = set(get_fogbugz_tags(request, case_id))
    tags.add(settings.FOGBUGZ_APPROVED_TAG)

    fogbugz_instance.edit(**{
        "ixBug": str(case_id),
        "ixPersonAssignedTo": str(settings.FOGBUGZ_MERGEKEEPER_USER_ID),
        settings.FOGBUGZ_APPROVED_REVISION_FIELD_ID: issue.latest_reviewed_rev,
        settings.FOGBUGZ_TARGET_BRANCH_FIELD_ID: target_branch,
        'sTags': ','.join(sorted(tags))
    })


def get_case_id(issue):
    """Get Fogbugz case id from given issue.

    :param issue: `Issue` object

    :return: `int` Fogbugz case id.
    """
    match = re.search(
        r'\(Case (\d+)\) Review: .+', issue.subject)

    if not match:
        raise RuntimeError('Case id cannot be found in the issue subject')

    return match.group(1)


@fogbugz_token_required
@views.login_required
@permission_required('codereview.approve_patchset')
@views.post_required
def gatekeeper_mark_ok(request, issue_id):
    """Set the reviewed revision on a case to latest.

    This will tell us the issue has been reviewed.

    :param request: HTTP request.
    :param: issue_id: `str` id of the `Issue` to approve
    """
    try:
        try:
            issue = models.Issue.objects.get(id=issue_id)
        except models.Issue.DoesNotExist:
            raise RuntimeError('Issue does not exist!')

        case_id = get_case_id(issue)

        form = GatekeeperApprove(case_id, request.POST)
        if not form.is_valid():
            raise RuntimeError(
                'You need to pass a target_branch parameter when approving a review. '
                'Please do so and try again.')
        target_branch = form.cleaned_data['target_branch']

        mark_issue_approved(request, issue, case_id, target_branch)
        messages_api.success(
            request, 'Revision {issue.latest_reviewed_rev} was sucesssfully approved '
            'on issue {issue.id} '
            'for Fogbugz case <a href="{settings.FOGBUGZ_URL}default.asp?{case_id}" '
            'target="_blank">{case_id}</a>, '
            'target branch: {target_branch}.'
            .format(issue=issue, settings=settings, case_id=case_id, target_branch=target_branch))
    except Exception as exc:
        messages_api.error(
            request,
            unicode(exc))
    finally:
        return HttpResponseRedirect('/{0}/show'.format(issue_id))


@views.post_required
@token_required
def mergekeeper_close(request, case_id):
    """Close a case.

    :param request: HTTP request.
    :param case_id: Fogbugz case ID.

    :return: HTTP 200 if the request was successful.
    :return: HTTP 403 if the the wrong `mergekeeper_close_token` is passed to the request.
    :return: HTTP 409 if the issue is already closed.
    """
    issue_desc_id = '(Case ' + str(case_id) + ') Review: '
    try:
        issue = models.Issue.objects.get(subject__startswith=issue_desc_id)
    except models.Issue.DoesNotExist:
        return HttpResponseServerError('Error: please specify a valid case number.')

    if issue.closed:
        return HttpResponse('Issue is already closed.', status=409)
    issue.closed = True
    issue.put()
    return HttpResponse('Closed', content_type='text/plain')


@permission_required('codereview.add_comment')
@fogbugz_token_required
@views.issue_required
@views.xsrf_required
def publish(request):
    """/<issue>/publish - Publish draft comments and send mail."""
    issue = request.issue
    case_id = get_case_id(request.issue)
    form_class = PublishForm
    draft_message = None
    if not request.POST.get('message_only', None):
        query = models.Message.gql(('WHERE issue = :1 AND sender = :2 '
                                    'AND draft = TRUE'), issue,
                                   request.user.email())
        draft_message = query.get()
    if request.method != 'POST':
        reviewers = issue.reviewers[:]
        cc = issue.cc[:] + [settings.DEFAULT_MAIL_CC]
        if request.user != issue.owner and (request.user.email()
                                            not in issue.reviewers):
            reviewers.append(request.user.email())
            if request.user.email() in cc:
                cc.remove(request.user.email())
        reviewers = [models.Account.get_nickname_for_email(reviewer,
                                                           default=reviewer)
                     for reviewer in reviewers]
        ccs = set([models.Account.get_nickname_for_email(email, default=email) for email in cc])
        tbd, comments = views._get_draft_comments(request, issue, True)
        preview = views._get_draft_details(request, comments)
        if draft_message is None:
            msg = ''
        else:
            msg = draft_message.text

        form = form_class(case_id, initial={
            'subject': issue.subject[:views.MAX_SUBJECT],
            'reviewers': ', '.join(reviewers),
            'cc': ', '.join(ccs),
            'send_mail': True,
            'tags': ['peer-reviewed'],
            'message': msg,
        })
        return views.respond(
            request, 'publish.html', {
                'form': form,
                'issue': issue,
                'preview': preview,
                'draft_message': draft_message,
                'case_id': case_id
            })

    form = form_class(case_id, request.POST)
    if not form.is_valid():
        return views.respond(request, 'publish.html', {'form': form, 'issue': issue})
    issue.subject = form.cleaned_data['subject']
    if form.is_valid() and not form.cleaned_data.get('message_only', False):
        reviewers = views._get_emails(form, 'reviewers')
    else:
        reviewers = issue.reviewers
        if request.user != issue.owner and request.user.email() not in reviewers:
            reviewers.append(db.Email(request.user.email()))
    if form.is_valid() and not form.cleaned_data.get('message_only', False):
        cc = views._get_emails(form, 'cc')
    else:
        cc = issue.cc
        # The user is in the reviewer list, remove them from CC if they're
        # there.
        if request.user.email() in cc:
            cc.remove(request.user.email())
    if not form.is_valid():
        return views.respond(request, 'publish.html', {'form': form, 'issue': issue})
    issue.reviewers = reviewers
    issue.cc = cc
    if not form.cleaned_data.get('message_only', False):
        tbd, comments = views._get_draft_comments(request, issue)
    else:
        tbd = []
        comments = []
    issue.update_comment_count(len(comments))
    tbd.append(issue)

    if comments:
        logging.warn('Publishing %d comments', len(comments))

    assign_to = form.cleaned_data.get('assign_to', None)

    msg = views._make_message(
        request, issue,
        form.cleaned_data['message'],
        comments,
        not assign_to and form.cleaned_data['send_mail'],
        draft=draft_message
    )
    tbd.append(msg)

    for obj in tbd:
        db.put(obj)
    measurements.measure_comments_per_user(request, issue)

    views._notify_issue(request, issue, 'Comments published')

    if assign_to:
        fogbugz_assign_case(request, case_id, assign_to, msg.text, form.cleaned_data['tags'])

    # There are now no comments here (modulo race conditions)
    models.Account.current_user_account.update_drafts(issue, 0)
    if form.cleaned_data.get('no_redirect', False):
        return HttpResponse('OK', content_type='text/plain')
    return HttpResponseRedirect(reverse(views.show, args=[issue.key().id()]))
