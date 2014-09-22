import imp
import itertools
import logging
import os
import paramiko
import socket
from ConfigParser import ConfigParser
from sqlalchemy import create_engine

from db import Base, Session
from agent import Agent, AgentManager
from test import  TestSuite, TestSuiteManager


log = logging.getLogger(__name__)

__all__ = ['Borg']


class AgentWrapper(object):
    def __init__(self, base_dir, agent):
        self.base_dir = base_dir
        self.agent = agent

    def _get_remote_path(self, remote):
        return os.path.join(self.base_dir, remote)

    def put(self, local, remote):
        remote = self._get_remote_path(remote)
        self.agent.put(local, remote)
        return remote

    def putstr(self, string, remote):
        remote = self._get_remote_path(remote)
        self.agent.putstr(string, remote)
        return remote

    def set_environ(self, **kwargs):
        content = "\n".join(map(lambda (k, v): "export %s=%s" % (k, v), kwargs.iteritems())) + "\n"
        return self.putstr(content, "environ.sh")


class Borg(object):

    base_dir = os.path.join(os.path.abspath(os.sep), 'tmp', 'borg')

    def __init__(self, config=None):
        user_home = os.path.expanduser('~')
        if not config:
            config = os.path.join(user_home, '.borg')
        self.config = ConfigParser()

        # Defaults
        self.config.add_section('borg')
        self.config.set('borg', 'database', os.path.join(user_home, '.borg.db'))

        self.config.read(config)
        engine = create_engine('sqlite:///' + self.config.get('borg', 'database'))

        Session.configure(bind=engine)
        Base.metadata.bind = Session.bind
        Base.metadata.create_all(checkfirst=True)

        self.agents = AgentManager()
        self.tests = TestSuiteManager()

    def clean_all(self, alias):
        alias_path = os.path.join(self.base_dir, alias)
        cmd = 'rm -r ' + alias_path
        for agent in itertools.chain(self.agents, [self.agents.local]):
            log.info("Cleaning %s on %s" % (alias, agent.hostname))
            try:
                agent.run(cmd)
            except paramiko.SSHException, e:
                log.error("Could not clean: %s" % str(e))

    def push_all(self, alias):
        test_suite = self.tests.get(alias)
        alias_path = os.path.join(self.base_dir, alias)

        custom_setup = None
        if os.path.isdir(test_suite.location):
            setup_py = os.path.join(test_suite.location, 'borg_setup.py')
            if os.access(setup_py, os.R_OK):
                mod_name = 'borg.test_' + alias
                log.debug("Loading %s as %s" % (setup_py, mod_name))
                mod = imp.load_source(mod_name, setup_py)
                if hasattr(mod, 'setup'):
                    log.info('Found a borg_setup.py:setup for the test')
                    custom_setup = mod.setup

        for agent in itertools.chain(self.agents, [self.agents.local]):
            try:
                log.info("Setting up virtualenv %s in %s" % (alias, agent.hostname))
                agent.run('mkdir -p ' + self.base_dir)
                agent.run('virtualenv ' + alias_path)
                agent.deploy(alias_path, test_suite)
                if custom_setup:
                    log.info("Calling borg_setup.py:setup for %s" % agent.hostname)
                    custom_setup(AgentWrapper(alias_path, agent))
            except paramiko.SSHException, e:
                log.error("Could not initialize test environment: %s" % str(e))

    def start_all(self, alias, test_file, target):
        alias_path = os.path.join(self.base_dir, alias)
        this_ip = socket.gethostbyaddr(socket.gethostname())[2][0]
        # Start master
        log.info("Starting master")
        self.agents.local.run(
            "cd %s; . ./bin/activate; if [ -f \"./environ.sh\" ]; then . ./environ.sh; fi; locust --master -H %s -f `which %s` --web-host ''" % (alias_path, target, test_file),
            daemonize=True
        )
        # Start slaves
        for agent in self.agents:
            log.info("Starting slave in %s" % agent.hostname)
            agent.run(
                "cd %s; . ./bin/activate; if [ -f \"./environ.sh\" ]; then . ./environ.sh; fi; locust --slave -H %s -f `which %s` --master-host %s" % (alias_path, target, test_file, this_ip),
                daemonize=True
            )

    def stop_all(self):
        log.info("Stopping slaves")
        for agent in self.agents:
            log.info("Starting slave in %s" % agent.hostname)
            agent.run("pkill -9 locust")
        log.info("Stopping master")
        self.agents.local.run("pkill -9 locust")
