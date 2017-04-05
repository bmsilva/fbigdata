import re
import json
import requests

from invoke import Collection, task
from invoke.config import DataProxy


class DataProxyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DataProxy):
            return dict(obj)
        return json.JSONEncoder.default(self, obj)


def _get_env_str(env_vars):
    if len(env_vars) == 0:
        return ''
    return ' '.join(['{}={}'.format(k, v) for k, v in env_vars.items()])


def _get_cmd(command, ctx, xvars=None, tags=None, verbose=False, flavor=None):
    cmd = [_get_env_str(ctx.ENV_VARS)]
    if flavor == 'ec2':
        cmd.append('ansible-playbook {}.yml -i ec2.py '.format(command))
    else:
        cmd.append('ansible-playbook {}.yml'.format(command))

    if xvars is not None:
        cmd.extend(['--extra-vars',
                    "'{}'".format(json.dumps(xvars, cls=DataProxyEncoder))])

    if verbose:
        cmd.append('-vvv')
    if tags and tags is not None:
        cmd.append('--tags')
        cmd.append('"{}"'.format(tags))
    return ' '.join(cmd)


def get_cmd(command, ctx, xvars=None, tags=None, verbose=False):
    return _get_cmd(command, ctx, xvars, tags, verbose)


def get_ec2_cmd(command, ctx, xvars=None, tags=None, verbose=False):
    return _get_cmd(command, ctx, xvars, tags, verbose, flavor='ec2')


@task
def log_update(ctx, hostname, verbose=False, tags=None):
    xvars = {
        'instance_hostname': hostname,
        'remote_user': ctx.REMOTE_USER,
        'prj_environment': ctx.PRJ_ENVIRONMENT,
        'python_version': ctx.PYTHON_VERSION,
    }

    r = ctx.run(get_cmd('log_update', ctx, xvars, tags, verbose), pty=True)


@task
def cdh_update(ctx, hostname, verbose=False, tags=None):
    xvars = {
        'instance_hostname': hostname,
        'remote_user': ctx.REMOTE_USER,
        'prj_environment': ctx.PRJ_ENVIRONMENT,
    }

    r = ctx.run(get_cmd('cdh_update', ctx, xvars, tags, verbose), pty=True)


@task
def hbase_update(ctx, hostname, verbose=False, tags=None):
    xvars = {
        'instance_hostname': hostname,
        'remote_user': 'ec2-user',
        'prj_environment': ctx.PRJ_ENVIRONMENT,
        'python_version': ctx.PYTHON_VERSION,
    }

    r = ctx.run(get_cmd('hbase_update', ctx, xvars, tags, verbose), pty=True)


def get_prd_configuration():
    d = {
        'PRJ_ENVIRONMENT': 'production',
        'PRJ_ENV': 'prd',
        'REMOTE_USER': 'ubuntu',
        'PYTHON_VERSION': '2.7.13',

        'ENV_VARS': {},
    }
    with open('.prd_env') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            name, value = line.strip().split('=')
            d['ENV_VARS'][name] = value
    return d


@task
def install_python(ctx, user, host):
    cmd = 'ssh {user}@{host} sudo apt install -y python'.format(**locals())
    r = ctx.run(cmd)


@task
def ec2_list(ctx, tag):
    cmd = [_get_env_str(ctx.ENV_VARS)]
    cmd.append('ansible -i ec2.py tag_Name_{} --list'.format(tag))
    r = ctx.run(' '.join(cmd))


@task
def ec2_refresh_cache(ctx):
    cmd = [_get_env_str(ctx.ENV_VARS)]
    cmd.append('./ec2.py --refresh-cache')
    r = ctx.run(' '.join(cmd))


@task
def ec2_create(ctx, instance_type, tag_name, tag_environment='production',
               ami_id=None, verbose=False, tags=None):
    if ami_id is None:
        # Ubuntu Server 16.04 LTS (HVM), SSD Volume Type
        ami_id = 'ami-405f7226'
    xvars = {
        'aws_region': 'eu-west-1',
        'aws_zone': 'eu-west-1b',
        'key_name': 'bmsilva-key-pair-eu-ireland',
        'instance_type': instance_type,
        'ami_id': ami_id,
        'subnet_1_id': 'subnet-1ebff97b',
        'instance_tag_name': tag_name,
        'instance_tag_environment': tag_environment,
    }

    r = ctx.run(get_cmd('ec2_create', ctx, xvars, tags, verbose), pty=True)


@task
def cdh_start_proxy(ctx):
    ro = re.compile(r'^(?P<hostname>\w+)\s+'
                    r'ansible_host=(?P<ip>\d+\.\d+\.\d+\.\d+)\s+'
                    r'ansible_user=(?P<user>\w+)$')
    ip = None
    user = None
    with open('inventory/hosts') as fh:
        for line in fh:
            mo = ro.search(line)
            if mo and mo.group('hostname') == 'cdh':
                ip = mo.group('ip')
                user = mo.group('user')
                break
    if ip is None:
        print("Couldn't find host!")
        return
    ctx.run('ssh -CND 8157 {}@{}'.format(user, ip))

@task
def cdh_start_chrome(ctx):
    ctx.run('/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome '
            '--user-data-dir="$HOME/chrome-with-proxy" '
            '--proxy-server="socks5://localhost:8157"')


prd = Collection(
    'prd',
    log_update,
    install_python,
    cdh_update,
    cdh_start_proxy,
    cdh_start_chrome,
    hbase_update,
    ec2_create,
    ec2_list,
    ec2_refresh_cache,
)
prd.configure(get_prd_configuration())

ns = Collection(prd)
