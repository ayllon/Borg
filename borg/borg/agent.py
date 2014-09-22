import getpass
import logging
import os
import paramiko
import shutil
import subprocess
from sqlalchemy import Column, String
from StringIO import StringIO

from db import Base, Session
from test import TestSuite

log = logging.getLogger(__name__)

_ssh_password = None
def _get_ssh_password():
    global _ssh_password
    if not _ssh_password:
        _ssh_password = getpass.getpass('SSH private key password: ')
    return _ssh_password

def _ssh_connect(agent):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    log.debug('Connecting to ' + agent.hostname)
    ssh_client.connect(agent.hostname, username=agent.user, password=_get_ssh_password())
    log.info('Connected to ' + agent.hostname)
    return ssh_client


def _run_command(hostname, ssh_client, cmd, daemonize):
    try:
        log.info("@%s > %s" % (hostname, cmd))
        if daemonize:
            ssh_client.exec_command("%s &>> /tmp/borg.log &" % cmd)
        else:
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            for line in stdout:
                log.debug(line.strip())
            for line in stderr:
                log.warning(line.strip())
        return 0
    except paramiko.SSHException, e:
        log.error(str(e))
        return 1


class AgentBase(object):
    hostname = None

    def run(self, cmd, daemonize=False):
        raise NotImplementedError()

    def put(self, local, remote):
        raise NotImplementedError()

    def putstr(self, string, remote):
        raise NotImplementedError()

    def unlink(self, path):
        raise NotImplementedError()

    def deploy(self, env_path, suite):
        assert(isinstance(suite, TestSuite))
        if suite.is_local():
            remote_location = "/tmp/borg/borg-%s.tar.gz" % suite.alias
            bundle = suite.generate_bundle()
            self.put(bundle.name, remote_location)
        else:
            remote_location = suite.location
        self.run(
            "cd %s; . ./bin/activate; pip install %s" % (env_path, remote_location)
        )
        if suite.is_local():
            log.info("Cleaning %s:%s" % (self.hostname, remote_location))
            self.unlink(remote_location)


class Agent(Base, AgentBase):
    __tablename__ = 't_agents'

    hostname = Column(String(255), primary_key=True)
    user     = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)

    ssh_client = None
    sftp_client = None

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)

    def _connect(self):
        if not self.ssh_client:
            self.ssh_client = _ssh_connect(self)
            self.sftp_client = self.ssh_client.open_sftp()

    def run(self, cmd, daemonize=False):
        self._connect()
        _run_command(self.hostname, self.ssh_client, cmd, daemonize)

    def put(self, local, remote):
        self.sftp_client.put(local, remote)

    def putstr(self, string, remote):
        buffer = StringIO(string)
        self.sftp_client.putfo(buffer, remote)

    def unlink(self, path):
        self.sftp_client.unlink(path)


class LocalAgent(AgentBase):
    hostname = 'localhost'
    user     = None
    password = None

    def put(self, local, remote):
        shutil.copyfile(local, remote)

    def putstr(self, string, remote):
        f = open(remote, "w")
        f.write(string)
        f.flush()
        f.close()

    def unlink(self, path):
        os.unlink(path)

    def run(self, cmd, daemonize=False):
        if daemonize:
            log.info("@localhost DAEMON %s" % cmd)
            os.system("%s &>> /tmp/borg.log &" % cmd)
        else:
            log.info("@localhost > %s" % cmd)
            child = subprocess.Popen(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            done = False
            while not done:
                for line in child.stdout.readlines():
                    log.debug(line.strip())
                for line in child.stderr.readlines():
                    log.warning(line.strip())
                child.poll()
                if child.returncode is not None:
                    done = True


class AgentManager(object):

    def __init__(self):
        self.local = LocalAgent()

    def __iter__(self):
        for a in Session.query(Agent).all():
            yield a

    def add(self, hostname, user, password):
        try:
            agent = Agent(hostname=hostname, user=user, password=password)
            Session.merge(agent)
            Session.commit()
            return agent
        except:
            Session.rollback()
            raise

    def remove(self, hostname):
        try:
            agent = Session.query(Agent).get(hostname)
            if not agent:
                raise KeyError("%s not found" % hostname)
            Session.delete(agent)
            Session.commit()
        except:
            Session.rollback()
            raise


__all__ = ['Agent', 'AgentManager']
