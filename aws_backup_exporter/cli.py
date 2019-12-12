# /bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2019 Aljosha Friemann <a.friemann@automate.wtf>
#
# Distributed under terms of the 3-clause BSD license.

import time

import boto3
from prometheus_client import Gauge, Summary, start_http_server

CLIENT = boto3.client('backup')

COMMON_LABELS = ['creation_date']

JOB_LABELS = COMMON_LABELS + [
    'completion_date',
    'backup_job_id',
    'backup_job_state',
    'backup_rule_id',
    'backup_plan_id',
    'backup_vault_name',
]

BACKUP_JOB_SIZE_BYTES = Gauge(
    'aws_backup_job_size_bytes', 'AWS Backup job size in bytes', JOB_LABELS)
BACKUP_JOB_PERCENT_DONE = Gauge(
    'aws_backup_job_percent_done', 'AWS Backup job percent done', JOB_LABELS)


def paginate(data_function, process_function):
    response = data_function()

    while True:
        process_function(response)

        if 'NextToken' not in response:
            break

        response = data_function(response['NextToken'])


def get_backup_jobs():
    """
    {
        'BackupJobs': [
            {
                'BackupJobId': 'string',
                'BackupVaultName': 'string',
                'BackupVaultArn': 'string',
                'RecoveryPointArn': 'string',
                'ResourceArn': 'string',
                'CreationDate': datetime(2015, 1, 1),
                'CompletionDate': datetime(2015, 1, 1),
                'State': 'CREATED'|'PENDING'|'RUNNING'|'ABORTING'|'ABORTED'|'COMPLETED'|'FAILED'|'EXPIRED',
                'StatusMessage': 'string',
                'PercentDone': 'string',
                'BackupSizeInBytes': 123,
                'IamRoleArn': 'string',
                'CreatedBy': {
                    'BackupPlanId': 'string',
                    'BackupPlanArn': 'string',
                    'BackupPlanVersion': 'string',
                    'BackupRuleId': 'string'
                },
                'ExpectedCompletionDate': datetime(2015, 1, 1),
                'StartBy': datetime(2015, 1, 1),
                'ResourceType': 'string',
                'BytesTransferred': 123
            },
        ],
        'NextToken': 'string'
    }
    """

    def observe(response):
        for job in response.get('BackupJobs', []):
            # print(job)
            labels = [
                job['CreationDate'],
                job['CompletionDate'],
                job['BackupJobId'],
                job['State'],
                job['CreatedBy']['BackupRuleId'],
                job['CreatedBy']['BackupPlanId'],
                job['BackupVaultName'],
            ]

            BACKUP_JOB_PERCENT_DONE.labels(
                *labels).set(float(job['PercentDone']))

            if 'BackupSizeInBytes' in job:
                BACKUP_JOB_SIZE_BYTES.labels(
                    *labels).set(float(job['BackupSizeInBytes']))

    paginate(CLIENT.list_backup_jobs, observe)


VAULT_LABELS = COMMON_LABELS + [
    'backup_vault_name',
]


BACKUP_VAULT_RECOVERY_POINTS = Gauge(
    'aws_backup_recovery_points', 'AWS Backup vault number of recovery points', VAULT_LABELS)


def get_backup_vaults():
    """
    {
        'BackupVaultList': [
            {
                'BackupVaultName': 'string',
                'BackupVaultArn': 'string',
                'CreationDate': datetime(2015, 1, 1),
                'EncryptionKeyArn': 'string',
                'CreatorRequestId': 'string',
                'NumberOfRecoveryPoints': 123
            },
        ],
        'NextToken': 'string'
    }
    """

    def observe(response):
        for vault in response.get('BackupVaultList', []):
            labels = [
                vault['CreationDate'],
                vault['BackupVaultName'],
            ]

            BACKUP_VAULT_RECOVERY_POINTS.labels(
                *labels).set(vault['NumberOfRecoveryPoints'])

    paginate(CLIENT.list_backup_vaults, observe)


def main():
    start_http_server(8000)

    while True:
        get_backup_vaults()
        get_backup_jobs()

        time.sleep(5)


# # Create a metric to track time spent and requests made.
# REQUEST_TIME = Summary('request_processing_seconds',
#                        'Time spent processing request')
#
# # Decorate function with metric.
# @REQUEST_TIME.time()
# def process_request(t):
#     """A dummy function that takes some time."""
#     time.sleep(t)
#
#
# if __name__ == '__main__':
#     # Start up the server to expose the metrics.
#     start_http_server(8000)
#     # Generate some requests.
#
#     while True:
#         process_request(random.random())
