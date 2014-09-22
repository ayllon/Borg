import os

def setup(remote):
    uproxy = os.environ.get('X509_USER_PROXY', "/tmp/x509_u%d" % os.getuid())
    if not os.access(uproxy, os.R_OK):
        raise Exception('Proxy missing')

    remote_path = remote.put(uproxy, 'proxy.pem')

    remote.set_environ(X509_USER_PROXY=remote_path)
