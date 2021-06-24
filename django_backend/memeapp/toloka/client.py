import os
import requests
from . import constants
from .toloka_exception import TolokaException
from time import sleep
from typing import Any, List, Dict


class TolokaClient:

    def __init__(self):
        self.token = os.getenv('TOLOKA_TOKEN')
        self.host = constants.HOST
        self.headers = {"Authorization": "OAuth " + self.token}

    def push_tasks(self, image_urls):
        json_raw = []
        for image in image_urls:
            json_raw.append(
                {
                    'input_values': {'image': image},
                    'overlap': constants.OVERLAP,
                    'pool_id': constants.POOL_ID
                }
            )

        r = requests.post(self.host + 'tasks', headers=self.headers, json=json_raw)
        if not r.ok:
            raise TolokaException(r.status_code, r.text)

    def get_answers(self) -> List[Dict[str, Any]]:
        json_raw_aggregate = {
            'pool_id': constants.POOL_ID,
            'type': 'DAWID_SKENE',
            'fields': [
                {
                    'name': constants.RESULT_FIELD_NAME
                }
            ]
        }
        aggregate_operation = requests.post(
            self.host + 'aggregated-solutions/aggregate-by-pool',
            headers=self.headers,
            json=json_raw_aggregate)

        if not aggregate_operation.ok:
            raise TolokaException(aggregate_operation.status_code, aggregate_operation.text)

        operation_id = aggregate_operation.json()['id']
        operation_status = requests.get(self.host + 'operations/{}'.format(operation_id), headers=self.headers)
        completed = operation_status.json()['status'] == 'SUCCESS'
        while not completed:
            sleep(30)  # агрегация Дэвида Скина довольно долгая
            operation_status = requests.get(self.host + 'operations/{}'.format(operation_id), headers=self.headers)
            current_status = operation_status.json()['status']
            if current_status == 'SUCCESS':
                completed = True
            elif current_status == 'FAIL':
                raise TolokaException(500, 'Aggregation operation failed')

        results = requests.get(self.host + 'aggregated-solutions/{}?limit=10000'.format(operation_id), headers=self.headers)
        if not results.ok:
            raise TolokaException(results.status_code, results.text)
        answers_raw = results.json()['items']

        tasks_req = requests.get(self.host + 'tasks?pool_id={}?limit=10000'.format(constants.POOL_ID), headers=self.headers)
        if not tasks_req.ok:
            raise TolokaException(tasks_req.status_code, tasks_req.text)
        tasks_raw = tasks_req.json()['items']
        tasks = {}
        for task in tasks_raw:
            tasks[task['id']] = tasks_raw[task['input_values']['image']]

        answers = []
        for answer in answers_raw:
            answers.append({
                'image': tasks[answer['task_id']],
                'answer': answer['output_values'][constants.RESULT_FIELD_NAME] == 'OK'
                            })
        return answers

