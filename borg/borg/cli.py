import logging
import sys
from optparse import OptionParser

from . import Borg


log = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
if sys.stdout.isatty():
    logging.addLevelName(logging.DEBUG, "\033[1;2m%-8s\033[1;m" % logging.getLevelName(logging.DEBUG))
    logging.addLevelName(logging.INFO, "\033[1;34m%-8s\033[1;m" % logging.getLevelName(logging.INFO))
    logging.addLevelName(logging.ERROR, "\033[1;31m%-8s\033[1;m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.WARNING, "\033[1;33m%-8s\033[1;m" % logging.getLevelName(logging.WARNING))


class CommandLineException(Exception):
    pass


class BadCommand(CommandLineException):
    pass


class MissingParameter(CommandLineException):
    pass


class Command(object):
    actions = []

    def __init__(self, borg):
        self.borg = borg
        self.option_parser = OptionParser()
        self.option_parser.add_option('-v', '--verbose', action='store_true', default=False)

    def search_method(self, name):
        matches = filter(lambda m: m.__name__ == name, self.actions)
        if matches:
            return matches[0]
        return None

    def __call__(self, argv):
        options, argv = self.option_parser.parse_args(argv)
        if options.verbose:
            log.setLevel(logging.DEBUG)
        method_name = None if not argv else argv[0]
        method = self.search_method(method_name)
        if method is None:
            self.option_parser.error(
                'Unknown action %s. Expected one of: ' % method_name + ' '.join(map(lambda m: m.__name__, self.actions))
            )
            return 1

        try:
            method(self, options, argv[1:])
        except CommandLineException, e:
            self.option_parser.error(str(e))
            return 1
        except Exception, e:
            log.error(e)
            if log.getEffectiveLevel() == logging.DEBUG:
                logging.exception(e)
            return 1


class AgentsCommand(Command):
    def list(self, options, argv):
        for agent in self.borg.agents:
            print agent.hostname,
            if agent.user:
                print "(%s)" % agent.user,
            print

    def add(self, options, argv):
        if not argv:
            raise MissingParameter('Missing host name')
        if '@' in argv[0]:
            user, hostname = argv[0].split('@', 2)
        else:
            user , hostname = None, argv[0]
        # TODO: Passwords
        self.borg.agents.add(hostname, user, None)

    def remove(self, options, argv):
        if not argv:
            raise MissingParameter('Missing host name')
        self.borg.agents.remove(argv[0])

    def clear(self, options, argv):
        for agent in self.borg.agents:
            log.info("Removing", agent.hostname)
            self.borg.agents.remove(agent.hostname)

    actions = [list, add, remove, clear]


class TestsCommand(Command):

    def add(self, options, argv):
        if len(argv) < 2:
            raise MissingParameter('Required parameters: alias and location')
        self.borg.tests.add(argv[0], argv[1])

    def remove(self, options, argv):
        if len(argv) < 1:
            raise MissingParameter('Required parameters: alias')
        self.borg.tests.remove(argv[0])

    def list(self, options, argv):
        for test in self.borg.tests:
            print "%s\t%s" % (test.alias, test.location)

    def push(self, options, argv):
        if len(argv) < 1:
            raise MissingParameter('Required parameters: alias')
        self.borg.push_test(argv[0])

    def clean(self, options, argv):

        self.borg.clean_remote(argv[0])

    def run(self, options, argv):
        if len(argv) < 1:
            raise MissingParameter('Required parameters: alias')
        self.borg.run_tests(argv[0])

    actions = [add, remove, list, push, clean, run]


class OrchestrateCommand(Command):

    def clean(self, options, argv):
        if len(argv) < 1:
            raise MissingParameter('Required parameters: alias')
        self.borg.clean_all(argv[0])

    def push(self, options, argv):
        if len(argv) < 1:
            raise MissingParameter('Required parameters: alias')
        self.borg.push_all(argv[0])

    def start(self, options, argv):
        if len(argv) < 3:
            raise MissingParameter('Required parameters: alias, test file and target')
        self.borg.start_all(argv[0], argv[1], argv[2])

    def stop(self, options, argv):
        self.borg.stop_all()

    actions = [clean, push, start, stop]


_operations = {
    'agents': AgentsCommand,
    'tests': TestsCommand,
    'orchestrate': OrchestrateCommand,
}


def main():
    try:
        if len(sys.argv) < 2:
            raise BadCommand('Missing command')
        op = _operations.get(sys.argv[1], None)
        if not op:
            raise BadCommand('Unknown command')
    except BadCommand, e:
        print e.message
        print 'Known commands:'
        for op in _operations.keys():
            print '\t', op
        return 1

    borg = Borg()
    return op(borg)(sys.argv[2:])


__all__ = ['main']
