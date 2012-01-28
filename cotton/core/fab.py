import contextlib
import time

from fabric.api import *
from fabric.contrib.files import exists

import fabtunnel
import shared

SERVERS = None
RUN_SERVER = None


@contextlib.contextmanager
def fake_tunneler():
    yield self


def prepare_app(app_name, app_config):
    env.user = app_config['remote_user']
    env.key_filename = app_config['key_path']
    bastion = app_config.get('bastion')
    if bastion:
        tunneler = fabtunnel.Tunneler(
            bastion_username=bastion['user'],
            bastion_host=bastion['host'],
            bastion_key_path=bastion['key_path']
        )
    else:
        tunneler = fake_tunneler
    return (app_config, tunneler)


def set_supervisor_configs(app_name, process_names):
    # Remove all existing configs.
    sudo('rm -f /etc/supervisor/conf.d/{0}-*.conf'.format(app_name))

    # Add desired process configs.
    for process_name in process_names:
        program_name = app_name + '-' + process_name
        sudo('cp cotton-deploy/supervisor/{0}.conf /etc/supervisor/conf.d'.format(program_name))

    sudo('service supervisor stop')

    # Need sleep for supervisor.
    time.sleep(5)
    sudo('service supervisor start')


def deploy(app_name, app_config):
    (app_config, tunneler) = prepare_app(app_name, app_config)

    build_repo = app_config['build_repo']
    servers = app_config['servers']
    for server_ip, process_names in servers.items():
        env.host_string = server_ip
        with tunneler():
            if not exists(app_name):
                run('git clone {0} {1}'.format(build_repo, app_name))
                with cd(app_name):
                    run('cotton-deploy/initialize')

            with cd(app_name):
                run('git pull')
                run('cotton-deploy/update')
                set_supervisor_configs(app_name, process_names)


def run_command(app_name, app_config, command):
    (app_config, tunneler) = prepare_app(app_name, app_config)

    env.host_string = app_config['run_server']
    with tunneler():
        with cd(app_name):
            command = shared.shell_escape(command)
            run('cotton-deploy/run-command {0}'.format(command))
