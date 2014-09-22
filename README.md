Borg
====

Dirty Python scripts to orchestrate the execution of [locust.io](http://locust.io/) across machines.

Uses [sqlalchemy](http://www.sqlalchemy.org/)+[sqlite](http://www.sqlite.org/)
to keep record of the hosts and tests, and [paramiko](https://github.com/paramiko/paramiko)
to orchestrate the slave nodes.

The tests are pushed into the slaves inside a virtualenv and installed using pip, so the dependencies
can be resolved automatically.

## Usage

#### Add a new host
```bash
borg agents add (user@)host
```

#### Add a new test suite
```bash
borg tests add alias test-location
```

#### Push a test suite to each host
```bash
borg orchestrate push alias
```

#### Start master and slaves
```bash
borg orchestrate start alias locust-test-file target-host
```

## Example
```bash
borg agents add root@planet-express.cern.ch
borg agents add root@arioch.cern.ch
borg tests add fts3 ~/Source/Borg/borg-tests/fts3-rest-test/
borg orchestrate push fts3
borg orchestrate -v start fts3 test_rucio.py fts3devel01.cern.ch
firefox http://localhost:8089 &
```
