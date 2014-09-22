import logging
import os
import tarfile
import tempfile
from sqlalchemy import Column, String
from urlparse import urlparse

from db import Base, Session


log = logging.getLogger(__name__)


def _validate_alias(alias):
    for c in alias:
        if not (c.isalnum() or c == '_'):
            raise ValueError('Only alphanumeric and _ are accepted in an alias')
    if alias[0] == '_':
        raise ValueError('Aliases can not start with _')


class TestSuite(Base):
    __tablename__ = 't_test_suites'

    alias = Column(String(255), primary_key=True)
    location = Column(String(1024), nullable=False)

    bundle = None

    def is_local(self):
        url = urlparse(self.location)
        return not url.scheme or url.scheme == 'file'

    def generate_bundle(self):
        if self.bundle:
            return self.bundle

        self.bundle = tempfile.NamedTemporaryFile(mode='wb', suffix='.tar.gz', prefix=self.alias, delete=True)
        log.info("Packaging %s into %s" % (self.location, self.bundle.name))
        tar = tarfile.open(fileobj=self.bundle, mode='w:gz')
        tar.add(self.location, arcname=os.path.basename(str(self.location)), recursive=True)
        for f in tar.getnames():
            log.debug("Bundle entry: %s" % f)
        tar.close()
        self.bundle.flush()
        return self.bundle


class TestSuiteManager(object):
    def __iter__(self):
        for t in Session.query(TestSuite).all():
            yield t

    def add(self, alias, location):
        _validate_alias(alias)
        try:
            suite = TestSuite(alias=alias, location=location)
            Session.merge(suite)
            Session.commit()
        except:
            Session.rollback()
            raise

    def remove(self, alias):
        try:
            suite = Session.query(TestSuite).get(alias)
            if suite:
                Session.delete(suite)
                Session.commit()
        except:
            Session.rollback()
            Session.commit()

    def get(self, alias):
        suite = Session.query(TestSuite).get(alias)
        if not suite:
            raise KeyError("Test suite %s not found" % alias)
        return suite


__all__ = ['TestSuite', 'TestSuiteManager']
