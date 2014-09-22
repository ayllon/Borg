from setuptools import setup

setup(
    name='fts3_rest_tests',
    py_modules=['FTS3Locust'],
    scripts=['test_rucio.py'],
    install_requires=[
        'locustio',
        'fts3-rest>=3.2.28'
    ],
    dependency_links=[
        'https://github.com/cern-it-sdc-id/fts3-rest/tarball/develop#egg=fts3-rest-3.2.28'
    ]
)
