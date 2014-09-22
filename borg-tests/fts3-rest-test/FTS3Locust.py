import os
import time
import urlparse
from locust import Locust, events
from fts3.rest.client import Context
from fts3.rest.client.easy import whoami, list_jobs, get_job_status, submit, cancel


class FTS3Client(object):
    """"
    FTS3 REST context wrapped so successes and failures can be accounted
    """

    def _call_method(self, func, *args, **kwargs):
        start_time = time.time()
        name = func.__name__
        try:
            result = func(*args, **kwargs)
        except Exception, e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(
                request_type="https", name=name, response_time=total_time, exception=e
            )
            raise
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                request_type="https", name=name, response_time=total_time, response_length=len(str(result))
            )
        return result

    def __init__(self, endpoint, verify):
        uproxy = os.environ.get('X509_USER_PROXY', None)
        self.context = Context(endpoint, verify=verify, ucert=uproxy, ukey=uproxy)

    def whoami(self):
        return self._call_method(whoami, self.context)

    def list_jobs(self, *args, **kwargs):
        return self._call_method(list_jobs, self.context, *args, **kwargs)

    def get_job_status(self, *args, **kwargs):
        return self._call_method(get_job_status, self.context, *args, **kwargs)

    def submit(self, *args, **kwargs):
        return self._call_method(submit, self.context, *args, **kwargs)

    def cancel(self, *args, **kwargs):
        return self._call_method(cancel, self.context, *args, **kwargs)


class FTS3Locust(Locust):
    def __init__(self):
        super(FTS3Locust, self).__init__()
        if self.host is not None:
            parsed = urlparse.urlparse(self.host)
            if not parsed.scheme:
                self.host = 'https://' + self.host
            if not parsed.port:
                self.host += ':8446'
            print "Connecting to %s" % self.host
            self.client = FTS3Client(endpoint=self.host, verify=False)
        else:
            self.client = FTS3Client(endpoint='https://fts3devel01.cern.ch:8446', verify=False)
