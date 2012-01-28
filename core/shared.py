import appdirs
import contextlib
import datetime
import errno
import os
import subprocess
import yaml

BUILD_REPO_NAME = 'build-repo'
DEPLOY_DIR = 'cotton-deploy'
ENV_VARS_FILE = 'env-vars'


dirs = appdirs.AppDirs(
    appname='cotton',
    appauthor='cottonproj'
)


@contextlib.contextmanager
def chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def run_cmd(command):
    subprocess.call(command, shell=True)


def read_config(repo_aliasing=True):
    with open('cotton-config.yml') as config_file:
        proj_config = yaml.load(config_file)
    if repo_aliasing:
        _apply_repo_aliasing(proj_config)
    return proj_config


def shell_escape(text):
    for c in ('\\', '\'', '"'):
        text = text.replace(c, r'\{0}'.format(c))
    return r"$'{0}'".format(text)


class BuildRepo(object):
    """Provide operations against a local clone of the build repository."""

    def __init__(self, app_name, repo_url):
        """Create a new BuildRepo.

        - app_name: app name
        - repo_url: URL of build repo

        """

        workspace_dir = os.path.join(dirs.user_cache_dir, app_name)
        self._workspace_dir = workspace_dir
        self._repo_url = repo_url

    def commit(self):
        build_dir = os.path.join(self._workspace_dir, BUILD_REPO_NAME)
        with chdir(build_dir):
            run_cmd('git add -A')
            now = datetime.datetime.utcnow()
            timestamp = now.strftime('%Y-%m-%dT%H:%M:%SZ')
            commit_message = '{0} build'.format(timestamp)
            run_cmd('git commit -m "{0}"'.format(commit_message))

            # Include 'origin master' to avoid an error when trying to push to
            # a brand-new build repo that does not yet have a master branch.
            run_cmd('git push origin master')

    def ensure(self):
        workspace_dir = self._workspace_dir
        build_dir = os.path.join(workspace_dir, BUILD_REPO_NAME)

        run_cmd('mkdir -p ' + workspace_dir)
        with chdir(workspace_dir):
            if not os.path.exists(BUILD_REPO_NAME):
                run_cmd('git clone {url} {dir_name}'.format(
                    url=self._repo_url,
                    dir_name=BUILD_REPO_NAME
                ))
            with chdir(BUILD_REPO_NAME):
                run_cmd('git reset --hard')
                run_cmd('git clean -dfx')
                run_cmd('git pull')
        return build_dir

    def get_config_vars(self):
        PREFIX_LEN = len('export ')
        env_exports = self._get_env_exports()
        lines = env_exports.split('\n')
        return [line[PREFIX_LEN:].strip().split('=', 1) for line in lines if line]

    def set_config_vars(self, config_vars):
        def export_line(pair):
            return u'export {0}={1}'.format(*pair)

        env_exports = u'\n'.join([export_line(v) for v in config_vars])
        self._set_env_exports(env_exports)

    def _ensure_deploy_dir(self):
        self.ensure()
        deploy_dir = os.path.join(self._workspace_dir, BUILD_REPO_NAME, DEPLOY_DIR)
        run_cmd('mkdir -p {0}'.format(deploy_dir))
        return deploy_dir

    def _get_env_exports(self):
        deploy_dir = self._ensure_deploy_dir()
        with chdir(deploy_dir):
            try:
                with open(ENV_VARS_FILE) as env_file:
                    return env_file.read().decode('utf-8')
            except IOError:
                # File does not exist.
                return u''

    def _set_env_exports(self, env_exports):
        deploy_dir = self._ensure_deploy_dir()
        with chdir(deploy_dir):
            with open(ENV_VARS_FILE, 'wb') as env_file:
                env_file.write(env_exports.encode('utf-8'))
        self.commit()


def get_user_build_repo(app_name, app_config):
    return BuildRepo(app_name, app_config['build_repo'])


def _apply_repo_aliasing(proj_config):
    user_config_path = os.path.join(dirs.user_data_dir, 'config.yml')
    try:
        with open(user_config_path) as config_file:
            user_config = yaml.load(config_file)
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
    else:
        if user_config:
            repo_aliases = user_config.get('repo_aliases')
            if repo_aliases:
                for app_config in proj_config.values():
                    # Use repo alias if one has been provided.
                    build_repo = app_config['build_repo']
                    repo_alias = repo_aliases.get(build_repo)
                    if repo_alias:
                        app_config['build_repo'] = repo_alias
                        print 'Aliasing {0} => {1}'.format(build_repo, repo_alias)
