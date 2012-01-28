#!/usr/bin/env python
import detection
import jinja2
import os
import shared

COTTON_BUILD_FILE = 'cotton-build'
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')


def _apply_template1(src_path, dest_path, context, mode):
    dirname, basename = os.path.split(src_path)
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(dirname))
    text = jinja_env.get_template(basename).render(**context)
    with open(dest_path, 'w') as f:
        f.write(text.encode('utf-8'))
    os.chmod(dest_path, mode)


def _apply_template2(template_name, dest_path, context, mode):
    _apply_template1(os.path.join(TEMPLATE_DIR, template_name), dest_path, context, mode)


def _parse_procfile():

    def build_proc_type_map(procfile):
        proc_type_map = {}
        for line in procfile:
            proc_type, command = line.split(':', 1)
            proc_type_map[proc_type.strip()] = command.strip()
        return proc_type_map

    with open('Procfile') as f:
        return build_proc_type_map(f)


class Builder(object):

    def __init__(self):
        app_name = os.path.basename(os.path.dirname(os.getcwd()))
        app_config = shared.read_config()[app_name]
        self._name = app_name
        self._ports = app_config['ports']
        self._remote_user = app_config['remote_user']

        # Absolute path to the home directory of the remote user account being
        # used to deploy the app.
        self._remote_home = app_config['remote_home']

        self._build_repo = shared.BuildRepo(app_name, app_config['build_repo'])

    @property
    def app_name(self):
        return self._name

    def build(self):
        """Generate support scripts.

        Should be run from within the root of the snapshot repo.

        """

        self._ensure_cotton_submodule()

        if os.path.exists(COTTON_BUILD_FILE):
            shared.run_cmd('./' + COTTON_BUILD_FILE)

        self._generate_deploy_files()
        build_repo_dir = self._build_repo.ensure()

        # rsync from snapshot repo to build repo
        rsync_command = 'rsync -av --delete . {0} --exclude=.git --exclude=env-vars'.format(
            build_repo_dir
        )
        shared.run_cmd(rsync_command)

        self._build_repo.commit()

    # Create a Supervisor config file for the given process type, inside
    # the current working directory.
    def _create_supervisor_config(self, process_type):
        program_name = self._name + '-' + process_type
        app_dir = os.path.join(self._remote_home, self._name)
        run_path = '{0}/run-{1}'.format(
            shared.DEPLOY_DIR,
            process_type
        )
        _apply_template2(
            'supervisor-program.conf',
            program_name + '.conf',
            {
                'program_name': program_name,
                'command': os.path.join(app_dir, run_path),
                'directory': app_dir,
                'user': self._remote_user
            },
            mode=0600
        )

    # Create Supervisor configs in the 'supervisor' directory of the
    # current working directory.
    def _create_supervisor_configs(self, process_types):
        SUPERVISOR_DIR = 'supervisor'
        shared.run_cmd('mkdir -p {0}'.format(SUPERVISOR_DIR))
        with shared.chdir(SUPERVISOR_DIR):
            for process_type in process_types:
                self._create_supervisor_config(process_type)

    # Create process-types-specific run scripts in the working directory.
    def _create_process_type_run_scripts(self, procfile):
        for process_type, command in procfile.items():
            _apply_template2(
                'run-process',
                'run-{0}'.format(process_type),
                {
                    'port': self._ports.get(process_type),
                    'program_command': shared.shell_escape(command)
                },
                mode=0700
            )

    def _ensure_cotton_submodule(self):
        if not os.path.exists('cotton/deploy'):
            shared.run_cmd('git submodule init')
        shared.run_cmd('git submodule update')

    def _generate_deploy_files(self):
        app_type = detection.detect_app_type(self)
        procfile = _parse_procfile()
        shared.run_cmd('mkdir -p {0}'.format(shared.DEPLOY_DIR))
        with shared.chdir(shared.DEPLOY_DIR):
            _apply_template2(
                app_type.init_template,
                'initialize',
                app_type.init_template_context,
                mode=0700
            )
            _apply_template2(
                'update',
                'update',
                {
                    'update_command': app_type.update_command
                },
                mode=0700
            )
            _apply_template2(
                'run-command',
                'run-command',
                {
                    'env_vars_file': shared.ENV_VARS_FILE
                },
                mode=0700
            )

            self._create_process_type_run_scripts(procfile)
            self._create_supervisor_configs(procfile.keys())


if __name__ == '__main__':
    Builder().build()
