"""General tests config."""
import os.path
import re
import sys
import subprocess

import mock

import pytest

import fogbugz

PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

import manage

manage.__name__

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_test'

import django_webtest
from django.core import urlresolvers
from django.contrib.auth import models as auth_models
from django.conf import settings

from paylogic import patches  # NOQA
from codereview import models
from paylogic import views


@pytest.fixture
def app(user, user_name, user_password):
    """Test django app."""
    app = django_webtest.DjangoTestApp()
    form = app.get(urlresolvers.reverse('auth_login')).form
    form['username'] = user_name
    form['password'] = user_password
    form.submit().follow()
    return app


@pytest.fixture(autouse=True)
def django_settings(repo_base_dir, target_repo_name, source_repo_name, vcs):
    """Override django settings for tests purpose."""

    default_branches = {
        'hg': 'default',
        'git': 'master',
        'bzr': 'trunk'
    }

    settings.VCS = {
        vcs: {
            'base_dir': repo_base_dir.strpath,
            'regex': re.compile('^({base_dir}/|{vcs}\+)(.+)$'.format(
                base_dir=repo_base_dir.strpath, vcs=vcs)),
            'supports_direct_export': vcs != 'git',
            'supports_simple_cloning': vcs != 'bzr',
            'default_branch': default_branches[vcs]
        },
    }

    settings.FEATURE_BRANCH_DEFAULT_PREFIX = '{vcs}+{path}#'.format(
        vcs=vcs, path=repo_base_dir.join(source_repo_name).strpath)
    settings.ORIGINAL_BRANCH_DEFAULT_PREFIX = '{vcs}+{path}#'.format(
        vcs=vcs, path=repo_base_dir.join(target_repo_name).strpath)


@pytest.fixture
def target_repo_name(vcs):
    """Name of the target repo."""
    return 'target'


@pytest.fixture
def source_repo_name(vcs):
    """Name of the source repo."""
    return 'source'


@pytest.fixture
def repo_base_dir(tmpdir, vcs):
    """Repository base dir."""
    return tmpdir.join(vcs)


@pytest.fixture
def vcs_commands(vcs):
    """Version control system commands to use for testing."""
    return {
        'git': {
            'init': ['git', 'init'],
            'config': [
                ('git', 'config', 'user.name', 'testuser'),
                ('git', 'config', 'user.email', 'travis@localhost.localdomain')],
            'add': ['git', 'add', '.'],
            'clone': ['git', 'clone'],
            'branch': ['git', 'checkout', '-b'],
            'commit': ['git', 'commit', '-am', '"test commit"'],
            'bare': ['git', 'config', 'core.bare', 'true']
        },
        'hg': {
            'init': ['hg', 'init'],
            'add': ['hg', 'add', '.'],
            'branch': ['hg', 'branch'],
            'clone': ['hg', 'clone'],
            'commit': ['hg', 'commit', '-m', '"test commit"', '--user', 'testuser']
        },
        'bzr': {
            'init': ['bzr', 'init-repo'],
            'config': [('bzr', 'whoami', '"testuser <test@u.ser>"')],
            'init-branch': ['bzr', 'init'],
            'add': ['bzr', 'add', '.'],
            'branch': ['bzr', 'branch'],
            'clone': ['bzr', 'clone'],
            'commit': ['bzr', 'commit', '-m', '"test commit"']
        },
    }[vcs]


@pytest.fixture
def target_test_file_name():
    """Target test file name."""
    return 'test'


@pytest.fixture
def target_test_file_content():
    """Target test file content."""
    return 'initial content'


@pytest.fixture
def target_repo(
        vcs, vcs_commands, repo_base_dir, target_repo_name, target_repo_branch, target_test_file_name,
        target_test_file_content):
    """Target repo. Means the base branch of the codereview."""
    path = repo_base_dir.join(target_repo_name)
    os.makedirs(path.strpath)
    subprocess.check_call(vcs_commands['init'] + [path.strpath])
    if 'config' in vcs_commands:
        for commands in vcs_commands['config']:
            subprocess.check_call(commands, cwd=path.strpath)
    if vcs == 'bzr':
        path = path.join(target_repo_branch)
        subprocess.check_call(vcs_commands['init-branch'] + [path.strpath])
    path.join(target_test_file_name).open('w').write(target_test_file_content)
    subprocess.check_call(vcs_commands['add'], cwd=path.strpath)
    subprocess.check_call(vcs_commands['commit'], cwd=path.strpath)
    if vcs == 'git':
        subprocess.check_call(vcs_commands['bare'], cwd=path.strpath)
    return path


@pytest.fixture
def target_repo_branch(vcs):
    """Target repo branch."""
    return {
        'hg': 'default',
        'git': 'master',
        'bzr': 'trunk',
    }[vcs]


@pytest.fixture
def target_repo_url(branch_url_mode, vcs, target_repo, target_repo_branch):
    """Url of the target repo."""
    return {
        'short': target_repo_branch,
        'medium': '{target_repo.strpath}#{target_repo_branch}'.format(**locals()),
        'long': '{vcs}+{target_repo.strpath}#{target_repo_branch}'.format(**locals())
    }[branch_url_mode]


@pytest.fixture
def source_test_file_name():
    """Target test file name."""
    return 'feature'


@pytest.fixture
def source_test_file_content():
    """Target test file content."""
    return 'feature content'


@pytest.fixture
def target_test_file_source_content():
    """Changed content of the target source file."""
    return 'changed'


@pytest.fixture
def source_repo(
        vcs, vcs_commands, repo_base_dir, target_repo, source_repo_branch, source_test_file_content,
        target_test_file_name, target_test_file_source_content, source_test_file_name, target_repo_branch,
        source_repo_name):
    """Source repo. Means the feature branch of the codereview."""
    path = repo_base_dir.join(source_repo_name)
    if vcs == 'bzr':
        subprocess.check_call(vcs_commands['init'] + [path.strpath])
        subprocess.check_call(vcs_commands['branch'] + [
            target_repo.strpath, source_repo_branch], cwd=path.strpath)
        path = path.join(source_repo_branch)
    else:
        subprocess.check_call(
            vcs_commands['clone'] + [target_repo.strpath, path.strpath])
        subprocess.check_call(
            vcs_commands['branch'] + [source_repo_branch], cwd=path.strpath)
    if 'config' in vcs_commands:
        for commands in vcs_commands['config']:
            subprocess.check_call(commands, cwd=path.strpath)
    path.join(source_test_file_name).open('w').write(source_test_file_content)
    path.join(target_test_file_name).open(
        'w').write(target_test_file_source_content)
    subprocess.check_call(vcs_commands['add'], cwd=path.strpath)
    subprocess.check_call(vcs_commands['commit'], cwd=path.strpath)
    if vcs == 'git':
        subprocess.check_call(vcs_commands['bare'], cwd=path.strpath)

    return path


@pytest.fixture
def source_repo_branch():
    """Source repo branch."""
    return 'feature'


@pytest.fixture
def source_repo_url(branch_url_mode, vcs, source_repo, source_repo_branch):
    """Url of the source repo."""
    return {
        'short': source_repo_branch,
        'medium': '{source_repo.strpath}#{source_repo_branch}'.format(**locals()),
        'long': '{vcs}+{source_repo.strpath}#{source_repo_branch}'.format(**locals())
    }[branch_url_mode]


@pytest.fixture
def user_name():
    """User name."""
    return 'dumb_user'


@pytest.fixture
def user_password():
    """User password."""
    return 'password'


@pytest.fixture
def user_email():
    """User email."""
    return 'dumb@example.com'


@pytest.fixture
def user_permissions():
    """User permissions."""
    return [
        'view_issue', 'change_issue', 'add_issue',
        'add_comment', 'change_comment', 'delete_comment',
        'approve_patchset']


@pytest.fixture
def user(db, user_name, user_email, user_password, user_permissions):
    """User."""
    user = auth_models.User.objects.create_user(user_name, user_email, user_password)
    for permission in user_permissions:
        user.user_permissions.add(auth_models.Permission.objects.get(codename=permission))
    user.save()
    return user


@pytest.fixture
def case_id():
    """Test fogbugz case id."""
    return 3000


@pytest.fixture
def ci_project():
    """Test ci project."""
    return 'ci-project'


@pytest.fixture(autouse=True)
def mocked_fogbugz_info(monkeypatch, case_id, source_repo_url, target_repo_url, target_repo_branch, ci_project):
    """Mock mocked_fogbugz_case_info function using given fixtures."""
    def mocked_fogbugz_case_info(request):
        return (
            case_id,
            'Some title',
            target_repo_url,
            source_repo_url,
            ci_project)

    monkeypatch.setattr(views, 'get_fogbugz_case_info',
                        mocked_fogbugz_case_info)


@pytest.fixture(autouse=True)
def mocked_fogbugz(monkeypatch):
    """Mock Fogbugz class to avoid external connections."""
    monkeypatch.setattr(fogbugz, 'FogBugz', mock.Mock())


@pytest.fixture
def issue_subject(case_id):
    """Issue subject."""
    return '(Case {case_id}) Review: test'.format(case_id=case_id)


@pytest.fixture
def patchset_revision():
    """Patchset revision."""
    return '12345678'


@pytest.fixture
def issue(user, issue_subject, patchset_revision):
    """Test issue."""
    issue = models.Issue(owner=user, subject=issue_subject, latest_patch_rev=patchset_revision)
    issue.put()
    return issue


@pytest.fixture
def patchset(issue, patchset_revision):
    """Test patchset."""
    patchset = models.PatchSet(issue=issue, revision=patchset_revision)
    patchset.put()
    return patchset


@pytest.fixture
def patch_filename():
    """Test patch filename."""
    return 'filename'


@pytest.fixture
def patch_text():
    """Test patch text."""
    return """Index: filename
diff --git a/filename b/filename
new file mode 100644
index 0000000000000000000000000000000000000000..968c807856a172723c04e232ea7e1e476d1abf18
--- /dev/null
+++ b/dev/null
@@ -0,0 +1,1 @@
+Some text
"""


@pytest.fixture
def patch_content():
    """Test patch content."""
    return 'Some text'


@pytest.fixture
def patch(patchset, patch_text, patch_filename):
    """Test patch."""
    patch = models.Patch(patchset=patchset, filename=patch_filename, text=patch_text)
    patch.put()
    return patch
