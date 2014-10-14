from locust import TaskSet, task

from FTS3Locust import FTS3Locust


class RucioUseCase(TaskSet):

    def __init__(self, parent):
        super(RucioUseCase, self).__init__(parent)
        self.job_id = None
        self.dlg_id = None

    @task(1)
    def whoami(self):
        response = self.client.whoami()
        self.dlg_id = response['delegation_id']

    @task(2)
    def get_job_list(self):
        if self.dlg_id:
            self.client.list_jobs(delegation_id=self.dlg_id, state_in=['SUBMITTED', 'ACTIVE', 'FINISHED'])

    @task(100)
    def poll(self):
        if self.job_id:
            self.client.get_job_status(self.job_id)

    @task(4)
    def submit(self):
        response = self.client.submit(
            {
                "files": [
                    {
                    "sources": ["mock://source.com/path"],
                    "destinations": ["mock://destination.com/path"]
                    }
                ],
                "params": {
                    "retry": -1
                }
            }
        )
        self.job_id = response

    @task(200)
    def delete(self):
        response = self.client.submit(
            {
                "delete": ["mock://file/path"]
            }
        )
        self.job_id = response


class RucioLocust(FTS3Locust):
    task_set = RucioUseCase
    min_wait = 50
    max_wait = 100
