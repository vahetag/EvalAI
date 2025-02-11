import json
import logging
import os
import signal
import sys
import time
import boto3
import botocore
import yaml
from kubernetes import client

# TODO: Add exception in all the commands
from kubernetes.client.rest import ApiException

# from statsd_utils import increment_and_push_metrics_to_statsd
from worker_utils import EvalAI_Interface


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True


formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

NODEGROUP = "Submission-workers-GPU-L4-staging"

AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "auth_token")
EVALAI_API_SERVER = os.environ.get("EVALAI_API_SERVER", "http://localhost:8000")
QUEUE_NAME = os.environ.get("QUEUE_NAME", "evalai_submission_queue")
script_config_map_name = "evalai-scripts-cm"

UBUNTU_IMAGE = "345594572510.dkr.ecr.us-west-2.amazonaws.com/ibpc:ubuntu"
# ZENOH_CONTAINER_IMAGE = "345594572510.dkr.ecr.us-west-2.amazonaws.com/ibpc:zenoh"
ZENOH_CONTAINER_IMAGE = "345594572510.dkr.ecr.us-west-2.amazonaws.com/ibpc:zenohd_tini"
ROS_HOST_CONTAINER_IMAGE = "345594572510.dkr.ecr.us-west-2.amazonaws.com/ibpc:HOST_3"

DATASET_TO_USE = "test"


def get_or_create_sqs_queue(queue_name="evalai_submission_queue", challenge=None):
    """
    Returns:
        Returns the SQS Queue object
    """
    if challenge and challenge.get("use_host_sqs"):
        sqs = boto3.resource(
            "sqs",
            region_name=challenge.queue_aws_region,
            aws_secret_access_key=challenge.aws_secret_access_key,
            aws_access_key_id=challenge.aws_access_key_id,
        )
    else:
        sqs = boto3.resource(
            "sqs",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        )
    if queue_name == "":
        queue_name = "evalai_submission_queue"
    # Check if the queue exists. If no, then create one
    try:
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except botocore.exceptions.ClientError as ex:
        if ex.response["Error"]["Code"] != "AWS.SimpleQueueService.NonExistentQueue":
            logger.exception("Cannot get queue: {}".format(queue_name))
        sqs_retention_period = os.getenv("SQS_RETENTION_PERIOD", "345600") if challenge is None else str(challenge.get("sqs_retention_period"))
        queue = sqs.create_queue(
            QueueName=queue_name,
            Attributes={"MessageRetentionPeriod": sqs_retention_period},
        )
    return queue, queue_name


def get_volume_mount_object(mount_path, name, read_only=False):
    volume_mount = client.V1VolumeMount(mount_path=mount_path, name=name, read_only=read_only)
    logger.info("Volume mount created at path: %s" % str(mount_path))
    return volume_mount


def get_volume_mount_list(mount_path, read_only=False):
    pvc_claim_name = "efs-claim"
    volume_mount = get_volume_mount_object(mount_path, pvc_claim_name, read_only)
    volume_mount_list = [volume_mount]
    return volume_mount_list


def get_volume_list():
    pvc_claim_name = "efs-claim"
    persistent_volume_claim = client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_claim_name)
    volume = client.V1Volume(persistent_volume_claim=persistent_volume_claim, name=pvc_claim_name)
    logger.info("Volume object created for '%s' pvc" % str(pvc_claim_name))
    volume_list = [volume]
    return volume_list


def get_empty_volume_object(volume_name):
    empty_dir = client.V1EmptyDirVolumeSource()
    volume = client.V1Volume(empty_dir=empty_dir, name=volume_name)
    return volume


def get_config_map_volume_object(config_map_name, volume_name):
    config_map = client.V1ConfigMapVolumeSource(name=config_map_name)
    volume = client.V1Volume(config_map=config_map, name=volume_name)
    return volume


def create_config_map_object(config_map_name, file_paths):
    # Configure ConfigMap metadata
    metadata = client.V1ObjectMeta(
        name=config_map_name,
    )
    config_data = {}
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        file_content = open(file_path, "r").read()
        config_data[file_name] = file_content
    # Instantiate the config_map object
    config_map = client.V1ConfigMap(api_version="v1", kind="ConfigMap", data=config_data, metadata=metadata)
    return config_map


def create_script_config_map(config_map_name):
    submission_script_file_path = "./scripts/workers/code_upload_worker_utils/make_submission.sh"
    monitor_submission_script_path = "./scripts/workers/code_upload_worker_utils/monitor_submission.sh"
    script_config_map = create_config_map_object(config_map_name, [submission_script_file_path, monitor_submission_script_path])
    return script_config_map


def create_configmap(core_v1_api_instance, config_map):
    try:
        config_maps = core_v1_api_instance.list_namespaced_config_map(namespace="default")
        if len(config_maps.items) and config_maps.items[0].metadata.name == script_config_map_name:
            # Replacing existing configmap
            logger.info("Replacing existing config map")
            core_v1_api_instance.replace_namespaced_config_map(
                name=script_config_map_name,
                namespace="default",
                body=config_map,
            )
            return
        logger.info("Creating new config map.")
        core_v1_api_instance.create_namespaced_config_map(
            namespace="default",
            body=config_map,
        )
    except Exception as e:
        logger.debug("Exception while creating configmap with error {}".format(e))
        logger.exception("Exception while creating configmap with error {}".format(e))


def get_submission_meta_update_curl(submission_pk):
    url = "{}/api/jobs/submission/{}/update_started_at/".format(EVALAI_API_SERVER, submission_pk)
    curl_request = "curl --location --request PATCH '{}' --header 'Authorization: Bearer {}'".format(url, AUTH_TOKEN)
    return curl_request


def get_job_object(submission_pk, spec):
    """Function to instantiate the AWS EKS Job object

    Arguments:
        submission_pk {[int]} -- Submission id
        spec {[V1JobSpec]} -- Specification of deployment of job

    Returns:
        [AWS EKS Job class object] -- AWS EKS Job class object
    """

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="submission-{0}".format(submission_pk)),
        spec=spec,
    )
    return job


def get_init_container(submission_pk):
    curl_request = get_submission_meta_update_curl(submission_pk)
    # Configure init container
    init_container = client.V1Container(
        name="init-container",
        image=UBUNTU_IMAGE,
        command=["/bin/bash", "-c", "apt update && apt install -y curl && {}".format(curl_request)],
    )
    return init_container


def get_pods_from_job(api_instance, core_v1_api_instance, job_name):
    pods_list = []
    job_def = read_job(api_instance, job_name)
    if job_def:
        controller_uid = job_def.metadata.labels["controller-uid"]
        pod_label_selector = "controller-uid=" + controller_uid
        pods_list = core_v1_api_instance.list_namespaced_pod(
            namespace="default",
            label_selector=pod_label_selector,
            timeout_seconds=10,
        )

    return pods_list


def get_job_constraints(challenge):
    constraints = {}
    if not challenge.get("cpu_only_jobs"):
        constraints["nvidia.com/gpu"] = "1"
    else:
        constraints["cpu"] = challenge.get("job_cpu_cores")
        constraints["memory"] = challenge.get("job_memory")
    return constraints


def create_static_code_upload_submission_job_object(message, challenge):
    """Function to create the static code upload pod AWS EKS Job object

    Arguments:
        message {[dict]} -- Submission message from AWS SQS queue
        challenge {challenges.Challenge} - Challenge model for the related challenge

    Returns:
        [AWS EKS Job class object] -- AWS EKS Job class object
    """

    # Get job constraints
    job_constraints = get_job_constraints(challenge)

    # Used to create submission file by phase_pk and selecting dataset location
    submission_pk = message["submission_pk"]
    challenge_pk = message["challenge_pk"]
    phase_pk = message["phase_pk"]
    submission_meta = message["submission_meta"]
    image = message["submitted_image_uri"]  # Submitted image

    # Container environment variables
    ######################################################################################################
    PYTHONUNBUFFERED_ENV = client.V1EnvVar(name="PYTHONUNBUFFERED", value="1")
    SUBMISSION_PK_ENV = client.V1EnvVar(name="SUBMISSION_PK", value=str(submission_pk))
    CHALLENGE_PK_ENV = client.V1EnvVar(name="CHALLENGE_PK", value=str(challenge_pk))
    PHASE_PK_ENV = client.V1EnvVar(name="PHASE_PK", value=str(phase_pk))
    # Using Default value 1 day = 86400s as Time Limit.
    SUBMISSION_TIME_LIMIT_ENV = client.V1EnvVar(name="SUBMISSION_TIME_LIMIT", value=str(submission_meta["submission_time_limit"]))
    SUBMISSION_TIME_DELTA_ENV = client.V1EnvVar(name="SUBMISSION_TIME_DELTA", value="300")

    AUTH_TOKEN_ENV = client.V1EnvVar(name="AUTH_TOKEN", value=AUTH_TOKEN)
    EVALAI_API_SERVER_ENV = client.V1EnvVar(name="EVALAI_API_SERVER", value=EVALAI_API_SERVER)

    submission_path = "/submission"
    SUBMISSION_PATH_ENV = client.V1EnvVar(name="SUBMISSION_PATH", value=submission_path)

    EFS_VOLUME_MOUNT_PATH = r"/opt/ros/underlay/install/datasets"
    EFS_VOLUME_MOUNT_PATH_ENV = client.V1EnvVar(name="BOP_PATH", value=EFS_VOLUME_MOUNT_PATH)

    DATASET_ENV = client.V1EnvVar(name="SPLIT_TYPE", value=DATASET_TO_USE),
    ######################################################################################################

    # Volume and Volume mount object setup
    ######################################################################################################
    # Get dataset volume and volume mounts

    # Creates a default volume backed by PVC 'efs-claim' and returns the Volume object in a list.
    volume_list = get_volume_list()

    # Creates a default volume mount object using the volume create above and also returns the volume mount object in a list.
    volume_mount_list = get_volume_mount_list(EFS_VOLUME_MOUNT_PATH, True)

    # Create a new volume by name 'script_volume_name' using the ConfigMap created previously.
    script_volume_name = "evalai-scripts"
    script_volume = get_config_map_volume_object(script_config_map_name, script_volume_name)

    # Creates a new volume mount object that uses the new volume's name.
    script_volume_mount = get_volume_mount_object("/evalai_scripts", script_volume_name, True)

    volume_list.append(script_volume)
    volume_mount_list.append(script_volume_mount)

    # Create empty volume and volume mount object for submissions.
    submission_volume_name = "submissions-dir"
    submission_volume = get_empty_volume_object(submission_volume_name)
    submission_volume_mount = get_volume_mount_object(submission_path, submission_volume_name)

    volume_list.append(submission_volume)
    volume_mount_list.append(submission_volume_mount)

    # Setup containers
    ######################################################################################################
    # Get init container
    init_container = get_init_container(submission_pk)

    # Configure Pod sidecar container
    sidecar_container = client.V1Container(
        name="sidecar-container",
        image=UBUNTU_IMAGE,
        command=["/bin/sh", "-c", "apt update && apt install -y curl && sh /evalai_scripts/monitor_submission.sh"],
        env=[
            SUBMISSION_PATH_ENV,
            CHALLENGE_PK_ENV,
            PHASE_PK_ENV,
            SUBMISSION_PK_ENV,
            AUTH_TOKEN_ENV,
            EVALAI_API_SERVER_ENV,
            SUBMISSION_TIME_LIMIT_ENV,
            SUBMISSION_TIME_DELTA_ENV,
        ],
        volume_mounts=volume_mount_list,
    )

    # Container based on ZENOH_CONTAINER_IMAGE
    zenoh_container = client.V1Container(name="zenoh-container", image=ZENOH_CONTAINER_IMAGE)

    # Container based on ROS_HOST_CONTAINER_IMAGE
    ros_host_container = client.V1Container(
        name="ros-host-container",
        image=ROS_HOST_CONTAINER_IMAGE,
        # Add environment variables or commands if needed
        env=[
            PYTHONUNBUFFERED_ENV,
            SUBMISSION_PATH_ENV,
            CHALLENGE_PK_ENV,
            PHASE_PK_ENV,
            EFS_VOLUME_MOUNT_PATH_ENV,
            DATASET_ENV,
        ],
        volume_mounts=volume_mount_list,
    )

    # Container based on Submitted image
    submission_container = client.V1Container(
        name="ros-participant-container",
        image=image,
        env=[
            PYTHONUNBUFFERED_ENV,
            SUBMISSION_PATH_ENV,
            CHALLENGE_PK_ENV,
            PHASE_PK_ENV,
        ],
        resources=client.V1ResourceRequirements(limits=job_constraints),
        volume_mounts=volume_mount_list,
    )

    ######################################################################################################
    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "evaluation"}),
        spec=client.V1PodSpec(
            init_containers=[init_container],
            containers=[
                sidecar_container,
                zenoh_container,
                ros_host_container,
                submission_container,
            ],
            restart_policy="Never",
            termination_grace_period_seconds=600,
            volumes=volume_list,
            # Target the new node group with the label "eks.amazonaws.com/nodegroup" whose value is Submission-workers-2
            # need to set the label in the ASG as well. k8s.io/cluster-autoscaler/node-template/label/eks.amazonaws.com/nodegroup: Submission-workers-2
            # node_selector={
            #     "eks.amazonaws.com/nodegroup": "Submssion-workers-8G-RAM-2",
            # },
            node_selector={
                "eks.amazonaws.com/nodegroup": NODEGROUP,
                "k8s.amazonaws.com/accelerator": "L4",
            },
        ),
    )

    # Create the specification of deployment
    spec = client.V1JobSpec(backoff_limit=1, template=template)

    # Instantiate the job object
    job = get_job_object(submission_pk, spec)

    return job


def create_job(api_instance, job):
    """Function to create a job on AWS EKS cluster

    Arguments:
        api_instance {[AWS EKS API object]} -- API object for creating job
        job {[AWS EKS job object]} -- Job object returned after running create_job_object fucntion

    Returns:
        [V1Job object] -- [AWS EKS V1Job]
        For reference: https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Job.md
    """
    api_response = api_instance.create_namespaced_job(body=job, namespace="default", pretty=True)
    logger.info("Job created with status='%s'" % str(api_response.status))
    return api_response


def delete_job(api_instance, job_name):
    """Function to delete a job on AWS EKS cluster

    Arguments:
        api_instance {[AWS EKS API object]} -- API object for deleting job
        job_name {[string]} -- Name of the job to be terminated
    """
    api_response = api_instance.delete_namespaced_job(
        name=job_name,
        namespace="default",
        body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=5),
    )
    logger.info("Job deleted with status='%s'" % str(api_response.status))


def process_submission_callback(api_instance, body, challenge_phase, challenge, evalai):
    """Function to process submission message from SQS Queue

    Arguments:
        body {[dict]} -- Submission message body from AWS SQS Queue
        evalai {[EvalAI class object]} -- EvalAI class object imported from worker_utils
    """
    try:
        logger.info("[x] Received submission message %s" % body)
        if body.get("is_static_dataset_code_upload_submission"):
            job = create_static_code_upload_submission_job_object(body, challenge)
        # else:
        #     environment_image = challenge_phase.get("environment_image")
        #     job = create_job_object(body, environment_image, challenge)
        response = create_job(api_instance, job)
        submission_data = {
            "submission_status": "queued",
            "submission": body["submission_pk"],
            "job_name": response.metadata.name,
        }
        evalai.update_submission_status(submission_data, body["challenge_pk"])
    except Exception as e:
        logger.exception("Exception while receiving message from submission queue with error {}".format(e))


def get_api_object(cluster_name, cluster_endpoint, challenge, evalai):
    configuration = client.Configuration()
    aws_eks_api = evalai.get_aws_eks_bearer_token(challenge.get("id"))
    configuration.host = cluster_endpoint
    configuration.verify_ssl = True
    configuration.ssl_ca_cert = "./scripts/workers/certificate.crt"
    configuration.api_key["authorization"] = aws_eks_api["aws_eks_bearer_token"]
    configuration.api_key_prefix["authorization"] = "Bearer"
    api_instance = client.BatchV1Api(client.ApiClient(configuration))
    return api_instance


def get_api_client(cluster_name, cluster_endpoint, challenge, evalai):
    configuration = client.Configuration()
    aws_eks_api = evalai.get_aws_eks_bearer_token(challenge.get("id"))
    configuration.host = cluster_endpoint
    configuration.verify_ssl = True
    configuration.ssl_ca_cert = "./scripts/workers/certificate.crt"
    configuration.api_key["authorization"] = aws_eks_api["aws_eks_bearer_token"]
    configuration.api_key_prefix["authorization"] = "Bearer"
    api_instance = client.ApiClient(configuration)
    return api_instance


def get_core_v1_api_object(cluster_name, cluster_endpoint, challenge, evalai):
    configuration = client.Configuration()
    aws_eks_api = evalai.get_aws_eks_bearer_token(challenge.get("id"))
    configuration.host = cluster_endpoint
    configuration.verify_ssl = True
    configuration.ssl_ca_cert = "./scripts/workers/certificate.crt"
    configuration.api_key["authorization"] = aws_eks_api["aws_eks_bearer_token"]
    configuration.api_key_prefix["authorization"] = "Bearer"
    api_instance = client.CoreV1Api(client.ApiClient(configuration))
    return api_instance


def get_running_jobs(api_instance):
    """Function to get all the current jobs on AWS EKS cluster
    Arguments:
        api_instance {[AWS EKS API object]} -- API object for deleting job
    """
    namespace = "default"
    try:
        api_response = api_instance.list_namespaced_job(namespace)
    except ApiException as e:
        logger.exception("Exception while receiving running Jobs{}".format(e))
    return api_response


def read_job(api_instance, job_name):
    """Function to get the status of a running job on AWS EKS cluster
    Arguments:
        api_instance {[AWS EKS API object]} -- API object for deleting job
    """
    namespace = "default"
    try:
        api_response = api_instance.read_namespaced_job(job_name, namespace)
    except ApiException as e:
        logger.exception("Exception while reading Job with error {}".format(e))
        return None
    return api_response


def cleanup_submission_job_delete(
    api_instance,
    evalai,
    job_name,
    submission_pk,
    challenge_pk,
    phase_pk,
    stderr,
    environment_log,
    submission_failed,
):
    """Function to update status of submission to EvalAi, Delete corrosponding job from cluster and message from SQS.
    Arguments:
        api_instance {[AWS EKS API object]} -- API object for deleting job
        evalai {[EvalAI class object]} -- EvalAI class object imported from worker_utils
        job_name {[string]} -- Name of the job to be terminated
        submission_pk {[int]} -- Submission id
        challenge_pk {[int]} -- Challenge id
        phase_pk {[int]} -- Challenge Phase id
        stderr {[string]} -- Reason of failure for submission/job
        environment_log {[string]} -- Reason of failure for submission/job from environment (code upload challenges only)
    """
    try:
        if submission_failed:
            submission_data = {
                "challenge_phase": phase_pk,
                "submission": submission_pk,
                "stdout": "",
                "stderr": stderr,
                "environment_log": environment_log,
                "submission_status": "FAILED",
                "result": "[]",
                "metadata": "",
            }
        else:
            submission_data = {
                "challenge_phase": phase_pk,
                "submission": submission_pk,
                "stdout": "",
                "stderr": stderr,
                "environment_log": environment_log,
                "submission_status": "evaluating",
                "result": "[]",
                "metadata": "",
            }

        evalai.update_submission_data(submission_data, challenge_pk, phase_pk)
        try:
            delete_job(api_instance, job_name)
        except Exception as e:
            logger.exception("Failed to delete submission job: {}".format(e))

    except Exception as e:
        logger.exception("Exception while EKS Job cleanup Submission {}:  {}".format(submission_pk, e))


def cleanup_submission_sqs_message_delete(submission_pk, message, queue_object):
    """Function to delete message from SQS.
    Arguments:
        submission_pk {[int]} -- Submission id
        message {[dict]} -- Submission message from AWS SQS queue
    """
    try:
        message_receipt_handle = message.get("receipt_handle")
        if message_receipt_handle:
            delete_message_from_sqs_queue(queue_object, message_receipt_handle)
    except Exception as e:
        logger.exception("Exception while SQS message cleanup Submission {}:  {}".format(submission_pk, e))


def update_jobs_and_send_logs(
    api_instance,
    core_v1_api_instance,
    evalai,
    job_name,
    submission_pk,
    challenge_pk,
    phase_pk,
    message,
    queue_name,
    disable_logs,
    queue_object,
):
    clean_submission = False
    submission_failed = True

    code_upload_environment_error = "Submission Job Failed."
    submission_error = "Submission Job Failed."

    logger.debug("In update_jobs_and_send_logs")
    logger.debug("job_name", job_name)
    logger.debug("submission_pk", submission_pk)
    logger.debug("challenge_pk", challenge_pk)
    logger.debug("phase_pk", phase_pk)
    logger.debug("message", message)
    logger.debug("queue_name", queue_name)

    try:
        pods_list = get_pods_from_job(api_instance, core_v1_api_instance, job_name)
        if pods_list:
            logger.debug("has pods_list")
            if disable_logs:
                code_upload_environment_error = None
                submission_error = None
            else:
                # Prevents monitoring when Job created with pending pods state (not assigned to node)
                if pods_list.items[0].status.container_statuses:
                    container_state_map = {}

                    for container in pods_list.items[0].status.container_statuses:
                        container_state_map[container.name] = container.state

                    logger.debug("container_state_map", container_state_map)

                    for container_name, container_state in container_state_map.items():
                        if container_name in ["agent", "ros-participant-container", "environment"]:
                            if container_state.terminated is not None:
                                reason = container_state.terminated.reason
                                exit_code = container_state.terminated.exit_code
                                logger.info(
                                    "Submission: {} :: Container {} terminated with reason: {} and exit_code: {}".format(
                                        submission_pk, container_name, reason, exit_code
                                    )
                                )

                                if reason == "Completed" and exit_code == 0:
                                    logger.info("Submission: {} :: Container {} executed successfully.".format(submission_pk, container_name))
                                    clean_submission = True
                                    submission_failed = False
                                else:
                                    logger.info("Submission: {} :: Container {} failed with reason: {}".format(submission_pk, container_name, reason))
                                    clean_submission = True  # Or handle failure logic here
                                    submission_failed = True

                                pod_name = pods_list.items[0].metadata.name

                                try:
                                    pod_log_response = core_v1_api_instance.read_namespaced_pod_log(
                                        name=pod_name,
                                        namespace="default",
                                        _return_http_data_only=True,
                                        _preload_content=False,
                                        container=container_name,
                                    )
                                    pod_log = pod_log_response.data.decode("utf-8")
                                    pod_log = pod_log[-10000:]
                                    # logger.info("pod_log")
                                    # logger.info(pod_log)
                                    if container_name == "environment":
                                        code_upload_environment_error = pod_log
                                    else:
                                        submission_error = pod_log

                                except client.rest.ApiException as e:
                                    logger.exception(f"Exception while reading logs for container {container_name}: {e}")
                else:
                    # if submission_pk_status in ("evaluating", "finished", "cancelled", "failed"):
                    #     clean_submission = True
                    # else:
                    logger.info("Job pods in pending state, waiting for node assignment for submission {}".format(submission_pk))
        else:
            logger.debug("Exception while reading Job {}, does not exist.".format(job_name))
            logger.exception("Exception while reading Job {}, does not exist.".format(job_name))
            clean_submission = True

    except Exception as e:
        logger.debug("Exception while reading Job {}".format(e))
        logger.exception("Exception while reading Job {}".format(e))
        clean_submission = True

    logger.info("Submission: {} :: clean_submission, submission_failed. {}, {}".format(submission_pk, clean_submission, submission_failed))

    if clean_submission:
        logger.info("cleanup_submission :: deleting job")
        cleanup_submission_job_delete(
            api_instance, evalai, job_name, submission_pk, challenge_pk, phase_pk, submission_error, code_upload_environment_error, submission_failed
        )
        logger.info("cleanup_submission :: deleting SQS message, {}".format(message))
        cleanup_submission_sqs_message_delete(submission_pk, message, queue_object)


def install_gpu_drivers(api_instance):
    """
    NOTE: Installed via kubectl ./install_dependencies.sh file
    Function to get the status of a running job on AWS EKS cluster
    Arguments:
        api_instance {[AWS EKS API object]} -- API object for creating deamonset
    """
    logging.info("Installing Nvidia-GPU Drivers ...")
    # Original manifest source: https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v1.11/nvidia-device-plugin.yml
    manifest_path = "./scripts/workers/code_upload_worker_utils/nvidia-device-plugin.yml"
    manifest_path = "./scripts/workers/code_upload_worker_utils/nvidia-device-plugin-latest.yml"
    logging.info("Using daemonset file: %s", manifest_path)
    nvidia_manifest = open(manifest_path).read()
    daemonset_spec = yaml.load(nvidia_manifest, yaml.FullLoader)
    ext_client = client.AppsV1Api(api_instance)
    try:
        namespace = daemonset_spec["metadata"]["namespace"]
        ext_client.create_namespaced_daemon_set(namespace, daemonset_spec)
    except ApiException as e:
        if e.status == 409:
            logging.info("Nvidia GPU driver daemon set has already been installed")
        else:
            raise


def get_message_from_sqs_queue(queue_object):
    try:
        messages = queue_object.receive_messages()
        if len(messages):
            message_receipt_handle = messages[0].receipt_handle
            message_body = json.loads(messages[0].body)
            logger.info("A submission is received with pk {}".format(message_body.get("submission_pk")))
        else:
            logger.info("No submission received")
            message_receipt_handle = None
            message_body = None

        response_data = {
            "body": message_body,
            "receipt_handle": message_receipt_handle,
        }
        return response_data
    except botocore.exceptions.ClientError as ex:
        response_data = {"error": ex}
        logger.exception("Exception raised: {}".format(ex))
        return response_data


def delete_message_from_sqs_queue(queue_object, receipt_handle):
    try:
        message = queue_object.Message(receipt_handle)
        message.delete()
        response_data = {"success": "Message deleted successfully from the queue: {}".format(queue_object.url.split("/")[-1])}
        return response_data
    except botocore.exceptions.ClientError as ex:
        response_data = {"error": ex}
        logger.exception("SQS message is not deleted due to {}".format(response_data))
        return response_data


def main():
    killer = GracefulKiller()
    evalai = EvalAI_Interface(
        AUTH_TOKEN=AUTH_TOKEN,
        EVALAI_API_SERVER=EVALAI_API_SERVER,
        QUEUE_NAME=QUEUE_NAME,
    )
    challenge = evalai.get_challenge_by_queue_name()
    queue, queue_name = get_or_create_sqs_queue(QUEUE_NAME, challenge=challenge)

    logger.info("Deploying Worker for {}".format(queue_name))

    # is_remote = int(challenge.get("remote_evaluation"))
    cluster_details = evalai.get_aws_eks_cluster_details(challenge.get("id"))
    cluster_name = cluster_details.get("name")
    cluster_endpoint = cluster_details.get("cluster_endpoint")

    api_instance_client = get_api_client(cluster_name, cluster_endpoint, challenge, evalai)
    # Install GPU drivers for GPU only challenges

    # if not challenge.get("cpu_only_jobs"):
    #     install_gpu_drivers(api_instance_client)

    api_instance = get_api_object(cluster_name, cluster_endpoint, challenge, evalai)
    core_v1_api_instance = get_core_v1_api_object(cluster_name, cluster_endpoint, challenge, evalai)

    if challenge.get("is_static_dataset_code_upload"):
        # Create and Mount Script Volume
        script_config_map = create_script_config_map(script_config_map_name)
        create_configmap(core_v1_api_instance, script_config_map)

    submission_meta = {}
    submission_meta["submission_time_limit"] = challenge.get("submission_time_limit")

    logger.info("running main")

    while True:
        time.sleep(2)
        # message = evalai.get_message_from_sqs_queue()
        message = get_message_from_sqs_queue(queue)
        message_body = message.get("body")

        if message_body:
            logger.debug("in while :: message_body", message_body)
            if challenge.get("is_static_dataset_code_upload") and not message_body.get("is_static_dataset_code_upload_submission"):
                logger.info("sleeping for 35 seconds")
                time.sleep(35)
                continue

            api_instance = get_api_object(cluster_name, cluster_endpoint, challenge, evalai)
            core_v1_api_instance = get_core_v1_api_object(cluster_name, cluster_endpoint, challenge, evalai)

            message_body["submission_meta"] = submission_meta

            submission_pk = message_body.get("submission_pk")
            challenge_pk = message_body.get("challenge_pk")
            phase_pk = message_body.get("phase_pk")

            challenge_phase = evalai.get_challenge_phase_by_pk(challenge_pk, phase_pk)

            disable_logs = challenge_phase.get("disable_logs")

            submission = evalai.get_submission_by_pk(submission_pk)

            logger.info("Submission: {}, status: {}".format(submission_pk, submission.get("status")))

            if submission:
                if (
                    submission.get("status") == "finished"
                    or submission.get("status") == "failed"
                    or submission.get("status") == "cancelled"
                    or submission.get("status") == "evaluating"
                ):
                    # try:
                    #     # Fetch the last job name from the list as it is the latest running job
                    #     job_name = submission.get("job_name")
                    #     message_receipt_handle = message.get("receipt_handle")
                    #     if job_name:
                    #         job_name = submission.get("job_name")[-1]
                    #         logger.debug("deleting job in while loop", job_name)
                    #         update_jobs_and_send_logs(
                    #             api_instance,
                    #             core_v1_api_instance,
                    #             evalai,
                    #             job_name,
                    #             submission_pk,
                    #             challenge_pk,
                    #             phase_pk,
                    #             message,
                    #             QUEUE_NAME,
                    #             disable_logs,
                    #             queue,
                    #             submission.get("status"),
                    #         )
                    #         # latest_job_name = job_name[-1]
                    #         # delete_job(api_instance, latest_job_name)
                    #     else:
                    #         logger.info(
                    #             "No job name found corresponding to submission: {} with status: {}.Deleting it from queue.".format(
                    #                 submission_pk, submission.get("status")
                    #             )
                    #         )
                    try:
                        # Fetch the last job name from the list as it is the latest running job
                        job_name = submission.get("job_name")
                        message_receipt_handle = message.get("receipt_handle")
                        if job_name:
                            logger.info("Deleting job")
                            latest_job_name = job_name[-1]
                            delete_job(api_instance, latest_job_name)
                        else:
                            logger.info(
                                "No job name found corresponding to submission: {} with status: {}.Deleting it from queue.".format(
                                    submission_pk, submission.get("status")
                                )
                            )
                        delete_message_from_sqs_queue(queue, message_receipt_handle)
                        # evalai.delete_message_from_sqs_queue(message_receipt_handle)
                        # increment_and_push_metrics_to_statsd(
                        #     QUEUE_NAME, is_remote
                        # )
                    except Exception as e:
                        logger.exception("Failed to delete submission job: {}".format(e))
                        # Delete message from sqs queue to avoid re-triggering job delete
                        # evalai.delete_message_from_sqs_queue(message_receipt_handle)
                        delete_message_from_sqs_queue(queue, message_receipt_handle)

                        # increment_and_push_metrics_to_statsd(
                        #     QUEUE_NAME, is_remote
                        # )
                elif submission.get("status") == "queued":
                    logger.debug("In queue")
                    job_name = submission.get("job_name")[-1]
                    pods_list = get_pods_from_job(api_instance, core_v1_api_instance, job_name)
                    if pods_list and pods_list.items[0].status.container_statuses:
                        logger.debug("pods_list.items[0].status.container_statuses", pods_list.items[0].status.container_statuses)
                        # Update submission to running
                        submission_data = {
                            "submission_status": "running",
                            "submission": submission_pk,
                            "job_name": job_name,
                        }
                        evalai.update_submission_status(submission_data, challenge_pk)

                elif submission.get("status") == "running":
                    logger.debug("In running")
                    job_name = submission.get("job_name")[-1]
                    update_jobs_and_send_logs(
                        api_instance,
                        core_v1_api_instance,
                        evalai,
                        job_name,
                        submission_pk,
                        challenge_pk,
                        phase_pk,
                        message,
                        QUEUE_NAME,
                        disable_logs,
                        queue,
                        # submission.get("status"),
                    )

                else:
                    logger.info("Processing message body: {0}".format(message_body))
                    challenge_phase = evalai.get_challenge_phase_by_pk(challenge_pk, phase_pk)
                    process_submission_callback(api_instance, message_body, challenge_phase, challenge, evalai)

        if killer.kill_now:
            break


if __name__ == "__main__":
    logger.debug("running main")
    main()
    logger.info("Quitting Submission Worker.")
