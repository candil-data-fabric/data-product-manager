__name__ = "Data Product Manager"
__version__ = "3.0.0"
__author__ = [
    "Lucía Cabanillas Rodríguez",
    "David Martínez García"
]
__credits__ = [
    "Telefónica I+D",
    "GIROS DIT-UPM",
    "Ignacio Domínguez Martínez-Casanueva",
    "Luis Bellido Triana",
    "Lucía Cabanillas Rodríguez",
    "David Martínez García"
]

## -- BEGIN IMPORT STATEMENTS -- ##

from configparser import ConfigParser
from contextlib import asynccontextmanager
from croniter import croniter
from datetime import datetime, timezone
from fastapi import Body, FastAPI, File, HTTPException, UploadFile, status, Request
from fastapi.responses import Response, JSONResponse
import json
from kubernetes import config
import kubernetes.client
from kubernetes.client import CustomObjectsApi
from kubernetes.client.rest import ApiException
import logging
import os
from pydantic import BaseModel, Field, model_validator
import pymongo
import requests
from typing import Literal, Union
import uuid

## -- END IMPORT STATEMENTS -- ##

## -- BEGIN LOGGING CONFIGURATION -- ##

logger = logging.getLogger(__name__)
logging.basicConfig(
    format = '%(asctime)s %(levelname)-8s %(message)s',
    level = logging.DEBUG,
    datefmt = '%Y-%m-%d %H:%M:%S'
)

## -- END LOGGING CONFIGURATION -- ##

## -- BEGIN CONSTANTS DECLARATION -- ##

### KUBERNETES CLUSTER INFORMATION ###

KUBERNETES_NAMESPACE = os.getenv("KUBERNETES_NAMESPACE")

### --- ###

### HELM REPOSITORY INFORMATION -- FOR FLUXCD ###

HELM_REPO_NAME = os.getenv("HELM_REPO_NAME")
HELM_REPO_URL = os.getenv("HELM_REPO_URL")

### --- ###

### DATA FABRIC KAFKA BROKER INFORMATION ###

KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", None)

### --- ###

### MORPH-KGC IMAGE AND HELM CHART INFORMATION ###

MORPH_RELEASE_NAME = os.getenv("MORPH_RELEASE_NAME")
MORPH_IMAGE_REPOSITORY = os.getenv("MORPH_IMAGE_REPOSITORY")
MORPH_CHART_NAME = os.getenv("MORPH_CHART_NAME")
MORPH_CHART_VERSION = os.getenv("MORPH_CHART_VERSION")

### --- ###

### SEMANTIC ANNOTATOR INFORMATION ###

SEMANTIC_ANNOTATOR_URI = os.getenv("SEMANTIC_ANNOTATOR_URI")
SEMANTIC_ANNOTATOR_ERROR_TOPIC_ENABLED = os.getenv("SEMANTIC_ANNOTATOR_ERROR_TOPIC_ENABLED", "False") == "True"
SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC_ENABLED = os.getenv("SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC_ENABLED", "False") == "True"
SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC_ENABLED = os.getenv("SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC_ENABLED", "False") == "True"
SEMANTIC_ANNOTATOR_ERROR_TOPIC = os.getenv("SEMANTIC_ANNOTATOR_ERROR_TOPIC")
SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC = os.getenv("SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC")
SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC = os.getenv("SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC")
SEMANTIC_ANNOTATOR_OUTPUT_FORMAT = os.getenv("SEMANTIC_ANNOTATOR_OUTPUT_FORMAT")

### --- ###

### SEMANTIC TRANSLATOR INFORMATION ###

SEMANTIC_TRANSLATOR_URI = os.getenv("SEMANTIC_TRANSLATOR_URI")
SEMANTIC_TRANSLATOR_SOURCE_TOPIC = os.getenv("SEMANTIC_TRANSLATOR_SOURCE_TOPIC")

### --- ###

### MONGO-DB INFORMATION ###

MONGO_DB_URI = os.getenv("MONGO_DB_URI")

### --- ###

## -- BEGIN DEFINITION OF PYDANTIC MODELS -- ##

class BatchDataSource(BaseModel):
    '''
    Base model for any batch data source.
    '''

    name: str = Field(
        default = None,
        description = "Name of the batch data source."
    )
    description: str = Field(
        default = None,
        description = "Description of the batch data source."
    )
    owner: str = Field(
        default = None,
        description = "URI that represents the person/entity that owns the data product."
    )
    glossary_terms: list[str] = Field(
        default = None,
        description = "URIs that represent terms defined in the business glossary."
    )
    tags: list[str] = Field(
        default = None,
        description = "List of tags that identify the batch data source."
    )
    freshness: str = Field(
        default = None,
        description = "Only supported for data sources of batch type. It determines how frequently the Data Fabric collects raw data from the target data source.")

class StreamingDataSource(BaseModel):
    '''
    Base model for any streaming data source.
    '''

    name: str = Field(
        default = None,
        description = "Name of the streaming data source."
    )
    description: str = Field(
        default = None,
        description = "Description of the streaming data source."
    )
    owner: str = Field(
        default = None,
        description = "URI that represents the person/entity that owns the data product."
    )
    glossary_terms: list[str] = Field(
        default = None,
        description = "URIs that represent terms defined in the business glossary."
    )
    tags: list[str] = Field(
        default = None,
        description = "List of tags that identify the streaming data source."
    )
    input_format: Union[
        Literal["JSON"], Literal["XML"], Literal["CSV"]
    ] = Field(description = "Input data format of the streaming data source.")
    input_topic: str = Field(description = "Name of the input topic.")

class RelationalDatabaseDataSource(BatchDataSource):
    '''
    Specific model for a relational database data source (batch data source).
    '''

    data_source_type: Literal["BATCH_RELATIONAL_DATABASE"]
    db_url: str = Field(description = "URL of source relational database.")

class FileDataSource(BatchDataSource):
    '''
    Specific model for a file data source (batch data source).
    '''

    data_source_type: Literal["BATCH_FILE"]
    file_path: str = Field(description = "Location (path) of source file.")

class KafkaDataSource(StreamingDataSource):
    '''
    Specific model for a Kafka data source (streaming data source).
    '''

    data_source_type: Literal["STREAMING_KAFKA"]
    host: str = Field(description = "Hostname, FQDN or IP address where the Kafka broker is reachable.")
    port: int = Field(description = "Port number where the Kafka broker is reachable.")
    group_id: str = Field(default = None, description = "Kafka group ID.")

class MqttDataSource(StreamingDataSource):
    '''
    Specific model for a MQTT data source (streaming data source).
    '''

    data_source_type: Literal["STREAMING_MQTT"]
    protocol: str = Field(description = "Protocol name used by the MQTT broker.")
    host: str = Field(description = "Hostname, FQDN or IP address where the MQTT broker is reachable.")
    port: int = Field(description = "Port number where the MQTT broker is reachable.")
    client_id: str = Field(default = None, description = "Client ID to use with the MQTT broker.")
    user: str = Field(default = None, description = "Username to use for authentication with the MQTT broker.")
    password: str = Field(default = None, description = "Password to use for authentication with the MQTT broker.")

class DataSource(BaseModel):
    '''
    Base model for any data source.
    '''

    details: Union[
        RelationalDatabaseDataSource,
        FileDataSource,
        KafkaDataSource,
        MqttDataSource
    ] = Field(description = "Data source type.", discriminator = "data_source_type")

    # See https://stackoverflow.com/questions/71108731/how-to-include-json-and-file-data-together-in-fastapi-endpoint
    @model_validator(mode = "before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

## -- END DEFINITION OF PYDANTIC MODELS -- ##

## -- BEGIN DEFINITION OF AUXILIARY FUNCTIONS -- ##

def translate_to_ini(data_source: DataSource, output_kafka_topic: str, mappings_file_name: str, config_file_name: str) -> str:
    '''
    Auxiliary function: translate_to_ini.

    ONLY FOR BATCH DATA SOURCES.

    It generates a Morph-KGC config.ini given the details of the data source, the mappings file name and the
    output configuration.
    '''

    logger.info("Generating config.ini file for Morph-KGC...")

    config = ConfigParser()

    config.add_section("CONFIGURATION")
    config.set("CONFIGURATION", "output_kafka_server", KAFKA_BROKER)
    config.set("CONFIGURATION", "output_kafka_topic", output_kafka_topic)
    config.set("CONFIGURATION", "mapping_partitioning", "no")

    config.add_section("DataSource")
    config.set("DataSource", "mappings", "config/files/" + mappings_file_name)

    if isinstance(data_source.details, FileDataSource):
        config.set("DataSource", "file_path", data_source.details.file_path)
    elif isinstance(data_source.details, RelationalDatabaseDataSource):
        config.set("DataSource", "db_url", data_source.details.db_url)

    with open(config_file_name, "w") as config_file:
        config.write(config_file)

    logger.info("Done.")

    return config_file_name

def create_helm_repository(api_instance: kubernetes.client.CoreV1Api, name: str, namespace: str, repo_url: str) -> None:
    '''
    Auxiliary function: create_helm_repository.

    ONLY FOR BATCH DATA SOURCES.

    It creates the HelmRepository within the FluxCD system for deploying Morph-KGC jobs/instances.
    '''

    logger.info(f"Trying to create HelmRepository '{name}'...")

    body = {
        "apiVersion": "source.toolkit.fluxcd.io/v1",
        "kind": "HelmRepository",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "interval": "1m0s",
            "url": repo_url
        }
    }

    custom_api_instance = CustomObjectsApi(api_instance.api_client)

    try:
        custom_api_instance.create_namespaced_custom_object(
            group = "source.toolkit.fluxcd.io",
            version = "v1",
            namespace = namespace,
            plural = "helmrepositories",
            body = body
        )
        logger.info(f"HelmRepository '{name}' created successfully.")
    except Exception as e:
        logger.info(f"Exception while trying to create HelmRepository '{name}': {e}.")

def create_helm_release(
        api_instance: kubernetes.client.CoreV1Api,
        name: str,
        namespace: str,
        chart_name: str,
        chart_version: str,
        repository_name: str,
        job_name: str,
        configuration: str,
        configmap_mappings_name: str,
        configmap_config_name: str,
        image_repository_url: str,
        freshness: str
    ):
    '''
    Auxiliary function: create_helm_release.

    ONLY FOR BATCH DATA SOURCES.

    It creates a HelmRelease within the FluxCD system for deploying a Morph-KGC job/instance.
    '''

    logger.info(f"Trying to create HelmRelease '{name}'...")

    body = {
        "apiVersion": "helm.toolkit.fluxcd.io/v2",
        "kind": "HelmRelease",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "chart": {
                "spec": {
                    "chart": f"{chart_name}",
                    "version": chart_version,
                    "sourceRef": {
                        "kind": "HelmRepository",
                        "name": repository_name
                    }
                }
            },
            "interval": "1m",
            "values": {
                "name": job_name,
                "morph_kgc_config": "config/" + configuration,
                "configmap_config": configmap_config_name,
                "configmap_mappings": configmap_mappings_name,
                "image":{
                    "repository": image_repository_url
                },
                "cronJob": {
                    "enabled": True if freshness is not None else False,
                    "schedule": str(freshness) if freshness is not None else "* * * * *",
                },
            }
        }
    }

    custom_api_instance = CustomObjectsApi(api_instance.api_client)

    try:
        api_response = custom_api_instance.create_namespaced_custom_object(
            group = "helm.toolkit.fluxcd.io",
            version = "v2",
            namespace = namespace,
            plural = "helmreleases",
            body = body
        )
        logger.info(f"HelmRelease '{name}' created successfully.")
    except Exception as e:
        logger.info(f"Exception while trying to create HelmRelease '{name}': {e}.")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Exception while trying to create HelmRelease '{name}': {e}."
        )
    
    return api_response

def delete_helm_repository(api_instance: kubernetes.client.CoreV1Api, name: str, namespace: str) -> None:
    '''
    Auxiliary function: delete_helm_repository.

    ONLY FOR BATCH DATA SOURCES.

    It deletes the HelmRepository within the FluxCD system for deploying Morph-KGC jobs/instances.
    '''

    logger.info(f"Trying to delete HelmRepository '{name}'...")

    custom_api_instance = CustomObjectsApi(api_instance.api_client)

    try:
        custom_api_instance.delete_namespaced_custom_object(
            group = "source.toolkit.fluxcd.io",
            version = "v1",
            namespace = namespace,
            plural = "helmrepositories",
            name = name
        )
        logger.info(f"HelmRepository '{name}' deleted successfully.")
    except Exception as e:
        logger.info(f"Exception while trying to delete HelmRepository '{name}': {e}.")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Exception while trying to delete HelmRepository '{name}': {e}."
        )

def delete_helm_release(api_instance: kubernetes.client.CoreV1Api, name: str, namespace: str) -> None:
    '''
    Auxiliary function: delete_helm_release.

    ONLY FOR BATCH DATA SOURCES.

    It deletes a HelmRelease within the FluxCD system for deploying a Morph-KGC job/instance.
    It also deletes ConfigMaps associated with the batch data product.
    Therefore, it can be considered a function to delete a batch data product.
    '''

    logger.info(f"Trying to delete batch data product / HelmRelease '{name}'...")

    custom_api_instance = CustomObjectsApi(api_instance.api_client)

    try:
        custom_api_instance.delete_namespaced_custom_object(
            group = "helm.toolkit.fluxcd.io",
            version = "v2",
            namespace = namespace,
            plural = "helmreleases",
            name = name
        )
        logger.info(f"Batch data product / HelmRelease '{name}' deleted successfully.")
    except Exception as e:
        logger.info(f"Exception while trying to delete batch data product / HelmRelease '{name}': {e}.")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Exception while trying to delete batch data product / HelmRelease '{name}': {e}."
        )
    
    try:
        api_instance.delete_namespaced_config_map(
            name = name + "-" + "configmap-mappings",
            namespace = namespace
        )
        api_instance.delete_namespaced_config_map(
            name = name + "-" + "configmap-config",
            namespace = namespace
        )
        logger.info(f"ConfigMaps for batch data product / HelmRelease '{name}' deleted successfully.")
    except Exception as e:
        logger.info(f"Exception while trying to delete ConfigMaps for batch data product / HelmRelease '{name}': {e}.")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Exception while trying to delete ConfigMaps for batch data product / HelmRelease '{name}': {e}."
        )

def onboard_batch_data_product(data_source: DataSource, mappings_file: UploadFile, mappings_content: bytes, kafka_topic: str, data_product: dict) -> dict:
    '''
    Auxiliary function: onboard_batch_data_product.

    It creates a HelmRelease within the FluxCD system to deploy Morph-KGC jobs that pull data from the
    data source and do the corresponding mappings. It also creates the corresponding ConfigMaps within
    the cluster to store Morph-KGC configuration and mappings. The create_helm_release auxiliary function is used.

    When semantic translation is required, the output topic where Morph-KGC will write RDF triples is the input/source topic
    used by the Semantic Translator. In this case, the output topic to be used by the Semantic Translator will be the output topic for
    Morph-KGC when no semantic translation is needed.

    * NO SEMANTIC TRANSLATION:
    Morph-KGC --> KAFKA_TOPIC

    * WITH SEMANTIC TRANSLATION:
    Morph-KGC --> SEMANTIC_TRANSLATOR_SOURCE_TOPIC <-- Semantic Translator --> KAFKA_TOPIC

    It returns a dictionary object with the data product details if all operations are successful. In any other case,
    an HTTPException is raised.
    '''

    logger.info("Trying to onboard a new batch data product...")

    if data_source.details.freshness:
        try:
            # Check if freshness schedule format is valid (crontab/cronjob format).
            croniter(data_source.details.freshness)
        except ValueError:
            raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Invalid crontab/cronjob format for freshness.")

    configmap_mappings_name = "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_source.details.name + "-" + "configmap-mappings"
    configmap_config_name = "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_source.details.name + "-" + "configmap-config"
    mappings_file_name = mappings_file.filename
    mappings_file_name_splitted = mappings_file_name.split(".")
    # name_mappings_file_splitted[0] is the original name of the file without the extension.
    # name_mappings_file_splitted[1] is the file extension.
    mappings_file_name = "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_source.details.name + "-" + "mappings" + "." + mappings_file_name_splitted[1]
    job_name = "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_source.details.name + "-" + "job"
    config_file_name = "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_source.details.name + "-" + "config" + "." + "ini"

    configuration = translate_to_ini(data_source, kafka_topic, mappings_file_name, config_file_name)

    with open(configuration, "r") as file:
        config_content = file.read()
    
    k8s_configmap_mappings_body = kubernetes.client.V1ConfigMap(
        metadata = kubernetes.client.V1ObjectMeta(name = configmap_mappings_name),
        data = {
            mappings_file_name: mappings_content.decode("utf-8")
        }
    )

    k8s_configmap_config_body = kubernetes.client.V1ConfigMap(
        metadata = kubernetes.client.V1ObjectMeta(name = configmap_config_name),
        data = {
            config_file_name: config_content
        }
    )

    helm_release_name = "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_source.details.name

    try:
        k8s_client.create_namespaced_config_map(
            KUBERNETES_NAMESPACE, k8s_configmap_mappings_body, field_validation = "Ignore"
        )
        k8s_client.create_namespaced_config_map(
            KUBERNETES_NAMESPACE, k8s_configmap_config_body, field_validation="Ignore"
        )
        logger.info(f"ConfigMaps for batch data product / HelmRelease '{helm_release_name}' created successfully.")
    except Exception as e:
        logger.info(f"Exception while trying to create ConfigMaps for batch data product / HelmRelease '{helm_release_name}': {e}.")
        logger.info("Exception while trying to create a new batch data product.")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Exception while trying to create ConfigMaps for batch data product / HelmRelease '{helm_release_name}': {e}. Exception while trying to create a new batch data product."
        )
    
    api_response = create_helm_release(
        k8s_client, helm_release_name, KUBERNETES_NAMESPACE, MORPH_CHART_NAME, MORPH_CHART_VERSION, HELM_REPO_NAME, job_name, configuration,
        configmap_mappings_name, configmap_config_name, MORPH_IMAGE_REPOSITORY, data_source.details.freshness
    )

    if isinstance(data_source.details, RelationalDatabaseDataSource):
        data_product["details"]["db_url"] = data_source.details.db_url
    if isinstance(data_source.details, FileDataSource):
        data_product["details"]["file_path"] = data_source.details.file_path
    data_product["details"]["freshness"] = {}
    data_product["details"]["freshness"]["enabled"] = str(api_response["spec"]["values"]["cronJob"]["enabled"])
    data_product["details"]["freshness"]["schedule"] = str(data_source.details.freshness)
    data_product["creationTimestamp"] = api_response["metadata"]["creationTimestamp"]

    logger.info("Batch data product onboarded successfully.")

    return data_product

def onboard_streaming_data_product(data_source: DataSource, mappings_content: bytes, kafka_topic: str, data_product: dict) -> dict:
    '''
    Auxiliary function: onboard_streaming_data_product.

    It creates a body structure compliant with Semantic Annotator schemas given the streaming source data product details and its mappings,
    and then sends an HTTP POST request to the Semantic Annotator to create the corresponding channel.

    When semantic translation is required, the output topic where the Semantic Annotator will write RDF triples is the input/source topic
    used by the Semantic Translator. In this case, the output topic to be used by the Semantic Translator will be the output topic for
    the Semantic Annotator when no semantic translation is needed.

    * NO SEMANTIC TRANSLATION:
    Semantic Annotator --> KAFKA_TOPIC

    * WITH SEMANTIC TRANSLATION:
    Semantic Annotator --> SEMANTIC_TRANSLATOR_SOURCE_TOPIC <-- Semantic Translator --> KAFKA_TOPIC

    It returns a dictionary object with the data product details in case the request is successful. In any other case, an HTTPException is raised
    with the response details given by the Semantic Annotator.
    '''

    logger.info("Trying to onboard a new streaming data product...")

    body = {}
    body["metadata"] = {}
    if data_source.details.name is not None:
        body["metadata"]["name"] = data_source.details.name
    body["metadata"]["author"] = "Data Product Manager"
    if data_source.details.description is not None:
        body["metadata"]["description"] = data_source.details.description
    if data_source.details.tags is not None:
        body["metadata"]["tags"] = data_source.details.tags
    body["metadata"]["mapping"] = {}
    body["metadata"]["mapping"]["name"] = "Mappings"
    body["metadata"]["mapping"]["author"] = "Data Product Manager"
    body["metadata"]["mapping"]["inputFormat"] = data_source.details.input_format
    body["metadata"]["mapping"]["outputFormat"] = SEMANTIC_ANNOTATOR_OUTPUT_FORMAT
    body["metadata"]["mapping"]["rml"] = mappings_content.decode("utf-8")
    body["settings"] = {}
    body["settings"]["channelId"] = data_product["_id"]
    body["settings"]["inputTopicSettings"] = {}
    body["settings"]["inputTopicSettings"]["topic"] = data_source.details.input_topic
    if isinstance(data_source.details, MqttDataSource):
        body["settings"]["inputTopicSettings"]["brokerType"] = "MQTT"
        body["settings"]["inputTopicSettings"]["mqttSettings"] = {}
        body["settings"]["inputTopicSettings"]["mqttSettings"]["protocol"] = data_source.details.protocol
        body["settings"]["inputTopicSettings"]["mqttSettings"]["host"] = data_source.details.host
        body["settings"]["inputTopicSettings"]["mqttSettings"]["port"] = data_source.details.port
        if data_source.details.client_id is not None:
            body["settings"]["inputTopicSettings"]["mqttSettings"]["clientId"] = data_source.details.client_id
        if data_source.details.user is not None:
            body["settings"]["inputTopicSettings"]["mqttSettings"]["user"] = data_source.details.user
        if data_source.details.password is not None:
            body["settings"]["inputTopicSettings"]["mqttSettings"]["password"] = data_source.details.password
    if isinstance(data_source.details, KafkaDataSource):
        body["settings"]["inputTopicSettings"]["brokerType"] = "KAFKA"
        body["settings"]["inputTopicSettings"]["kafkaSettings"] = {}
        body["settings"]["inputTopicSettings"]["kafkaSettings"]["host"] = data_source.details.host
        body["settings"]["inputTopicSettings"]["kafkaSettings"]["port"] = data_source.details.port
        if data_source.details.group_id is not None:
            body["settings"]["inputTopicSettings"]["kafkaSettings"]["groupId"] = data_source.details.group_id
    body["settings"]["outputTopicSettings"] = {}
    body["settings"]["outputTopicSettings"]["topic"] = kafka_topic
    body["settings"]["outputTopicSettings"]["brokerType"] = "KAFKA"
    body["settings"]["outputTopicSettings"]["kafkaSettings"] = {}
    body["settings"]["outputTopicSettings"]["kafkaSettings"]["host"] = KAFKA_BROKER.split(":")[0]
    body["settings"]["outputTopicSettings"]["kafkaSettings"]["port"] = int(KAFKA_BROKER.split(":")[1])
    if KAFKA_GROUP_ID is not None:
        body["settings"]["outputTopicSettings"]["kafkaSettings"]["groupId"] = KAFKA_GROUP_ID
    if SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC_ENABLED == True:
        body["settings"]["monitorInputTopicSettings"] = {}
        body["settings"]["monitorInputTopicSettings"]["topic"] = SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC
        body["settings"]["monitorInputTopicSettings"]["brokerType"] = "KAFKA"
        body["settings"]["monitorInputTopicSettings"]["kafkaSettings"] = {}
        body["settings"]["monitorInputTopicSettings"]["kafkaSettings"]["host"] = KAFKA_BROKER.split(":")[0]
        body["settings"]["monitorInputTopicSettings"]["kafkaSettings"]["port"] = int(KAFKA_BROKER.split(":")[1])
        if KAFKA_GROUP_ID is not None:
            body["settings"]["monitorInputTopicSettings"]["kafkaSettings"]["groupId"] = KAFKA_GROUP_ID
    if SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC_ENABLED == True:
        body["settings"]["monitorOutputTopicSettings"] = {}
        body["settings"]["monitorOutputTopicSettings"]["topic"] = SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC
        body["settings"]["monitorOutputTopicSettings"]["brokerType"] = "KAFKA"
        body["settings"]["monitorOutputTopicSettings"]["kafkaSettings"] = {}
        body["settings"]["monitorOutputTopicSettings"]["kafkaSettings"]["host"] = KAFKA_BROKER.split(":")[0]
        body["settings"]["monitorOutputTopicSettings"]["kafkaSettings"]["port"] = int(KAFKA_BROKER.split(":")[1])
        if KAFKA_GROUP_ID is not None:
            body["settings"]["monitorOutputTopicSettings"]["kafkaSettings"]["groupId"] = KAFKA_GROUP_ID
    if SEMANTIC_ANNOTATOR_ERROR_TOPIC_ENABLED == True:
        body["settings"]["errorTopicSettings"] = {}
        body["settings"]["errorTopicSettings"]["topic"] = SEMANTIC_ANNOTATOR_ERROR_TOPIC
        body["settings"]["errorTopicSettings"]["brokerType"] = "KAFKA"
        body["settings"]["errorTopicSettings"]["kafkaSettings"] = {}
        body["settings"]["errorTopicSettings"]["kafkaSettings"]["host"] = KAFKA_BROKER.split(":")[0]
        body["settings"]["errorTopicSettings"]["kafkaSettings"]["port"] = int(KAFKA_BROKER.split(":")[1])
        if KAFKA_GROUP_ID is not None:
            body["settings"]["errorTopicSettings"]["kafkaSettings"]["groupId"] = KAFKA_GROUP_ID
    body["status"] = {}
    body["status"]["isStopped"] = False
    body["status"]["inputTopicEnabled"] = True
    body["status"]["outputTopicEnabled"] = True
    if SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC_ENABLED == True:
        body["status"]["inputMonitorTopicEnabled"] = True
    else:
        body["status"]["inputMonitorTopicEnabled"] = False
    if SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC_ENABLED == True:
        body["status"]["outputMonitorTopicEnabled"] = True
    else:
        body["status"]["outputMonitorTopicEnabled"] = False
    if SEMANTIC_ANNOTATOR_ERROR_TOPIC_ENABLED == True:
        body["status"]["errorTopicEnabled"] = True
    else:
        body["status"]["errorTopicEnabled"] = False
    
    response = requests.post(
        url = SEMANTIC_ANNOTATOR_URI + "channels",
        headers = {
            "accept": "text/plain",
            "Content-Type": "application/json"
        },
        json = body
    )
    if response.status_code != status.HTTP_200_OK:
        logger.info("Exception while trying to onboard a new streaming data product.")
        raise HTTPException(status_code = response.status_code, detail = response.text)
    
    data_product["details"] = body
    data_product["creationTimestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    logger.info("Streaming data product onboarded successfully.")

    return data_product

def delete_streaming_data_product(data_product_id: str) -> None:
    '''
    Auxiliary function: delete_streaming_data_product.

    It sends an HTTP DELETE request to the Semantic Annotator to delete the channel associated
    with the streaming source data product, which ID string is passed as a parameter.

    In case the request is not successful, an HTTPException is raised with the response details given by
    the Semantic Annotator.
    '''

    logger.info(f"Trying to delete streaming data product '{data_product_id}'...")

    response = requests.delete(
        url = SEMANTIC_ANNOTATOR_URI + "channels" + "/" + data_product_id,
        headers = {
            "accept": "text/plain"
        }
    )
    if response.status_code == status.HTTP_200_OK:
        logger.info(f"Streaming data product '{data_product_id}' deleted successfully.")
    else:
        logger.info(f"Exception while trying to delete streaming data product '{data_product_id}'.")
        raise HTTPException(status_code = response.status_code, detail = response.text)

def create_alignment(translation_rules: bytes) -> dict:
    '''
    Auxiliary function: create_alignment.

    It sends an HTTP POST request to the Semantic Translator to create the alignment
    (set of translation rules) which content is passed as body of the request.

    In case the request is not successful, an HTTPException is raised with the response details given by
    the Semantic Translator.
    '''

    logger.info("Trying to create a new alignment...")

    response = requests.post(
        url = SEMANTIC_TRANSLATOR_URI + "alignments",
        headers = {
            "accept": "application/json",
            "Content-Type": "application/xml"
        },
        data = translation_rules.decode("utf-8")
    )
    if response.status_code == status.HTTP_201_CREATED:
        alignment_name = response.json()["info"]["name"]
        alignment_version = response.json()["info"]["version"]
        logger.info(f"Alignment '{alignment_name} / {alignment_version}' created successfully.")
        return response.json()["info"]
    else:
        logger.info("Exception while trying to create alignment - " + response.json()["message"])
        raise HTTPException(status_code = response.status_code, detail = response.json()["message"])

def delete_alignment(name: str, version: str) -> None:
    '''
    Auxiliary function: delete_alignment.

    It sends an HTTP DELETE request to the Semantic Translator to delete the alignment
    (set of translation rules) which name and version are passed as parameters.

    In case the request is not successful, an HTTPException is raised with the response details given by
    the Semantic Translator.
    '''
    
    logger.info(f"Trying to delete alignment '{name} / {version}'...")

    response = requests.delete(
        url = SEMANTIC_TRANSLATOR_URI + "alignments" + "/" + name + "/" + version,
        headers = {
            "accept": "application/json"
        }
    )
    if response.status_code == status.HTTP_204_NO_CONTENT:
        logger.info(f"Alignment '{name} / {version}' successfully deleted.")
    else:
        logger.info("Exception while trying to delete alignment - " + response.json()["message"])
        raise HTTPException(status_code = response.status_code, detail = response.json()["message"])

def create_translation_channel(translation_channel_settings: dict, data_product: dict) -> dict:
    '''
    Auxiliary function: create_translation_channel.

    It send an HTTP POST request to the Semantic Translator to create a new translation channel
    which settings are passed as a parameter.

    In case the request is not successful, an HTTPException is raised with the response details
    given by the Semantic Translator.
    '''

    logger.info("Trying to create a new translation channel...")
    logger.info("Settings:")
    logger.info(json.dumps(translation_channel_settings, indent = 4))

    response = requests.post(
        url = SEMANTIC_TRANSLATOR_URI + "channels",
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        },
        json = translation_channel_settings
    )
    if response.status_code == status.HTTP_201_CREATED:
        logger.info("Translation channel successfully created.")
        translation_channel_settings.update({"channelId": str(response.json()["info"]["id"])})
        translation_channel_settings.update({"descId": response.json()["info"]["descId"]})
        data_product["translation"]["settings"] = translation_channel_settings
    else:
        logger.info("Exception while trying to create a new translation channel.")
        raise HTTPException(status_code = response.status_code, detail = response.json()["message"])

    return data_product

def delete_translation_channel(channel_id: str) -> None:
    '''
    Auxiliary function: delete_translation_channel.

    It sends an HTTP DELETE request to the Semantic Translator to delete the translation channel
    which ID is passed as a parameter.

    In case the request is not successful, an HTTPException is raised with the response details
    given by the Semantic Translator.
    '''

    logger.info(f"Trying to delete translation channel '{channel_id}'...")

    response = requests.delete(
        url = SEMANTIC_TRANSLATOR_URI + "channels" + "/" + channel_id,
        headers = {
            "accept": "application/json"
        }
    )
    if response.status_code == status.HTTP_204_NO_CONTENT:
        logger.info(f"Translation channel '{channel_id}' successfully deleted.")
    else:
        logger.info("Exception while trying to delete translation channel - " + response.json()["message"])
        raise HTTPException(status_code = response.status_code, detail = response.json()["message"])

## -- END DEFINITION OF AUXILIARY FUNCTIONS -- ##

## -- BEGIN MAIN CODE -- ##

# Initialize Kubernetes client:
config.load_incluster_config()
k8s_client = kubernetes.client.CoreV1Api()

# Initialize Mongo-DB client:
mongodb_client = pymongo.MongoClient(MONGO_DB_URI)
mongodb_database = mongodb_client["data-fabric-data-product-manager"]
mongodb_collection = mongodb_database["data-products"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    '''
    FastAPI lifespan manager (on startup and shutdown events).
    '''

    # -- BEGIN STARTUP -- #

    logger.info("Application started.")

    # Create HelmRepository resource:
    create_helm_repository(k8s_client, HELM_REPO_NAME, KUBERNETES_NAMESPACE, HELM_REPO_URL)

    # -- END STARTUP -- #

    yield

    # -- BEGIN SHUTDOWN -- #

    logger.info("Shutdown event detected. Beginning cleanup process...")
    # Cleanup process:
    data_products = list(mongodb_collection.find())
    if len(data_products) > 0:
        for data_product in data_products:
            if data_product["translation"]["defined"] == "yes":
                # Delete translation channel:
                delete_translation_channel(data_product["translation"]["settings"]["channelId"])
                # Delete alignments/translation rules:
                if (data_product["translation"]["source_to_central"] == "yes") and (data_product["translation"]["source_to_central"] == "no"):
                    delete_alignment(data_product["translation"]["settings"]["inpAlignmentName"], data_product["translation"]["settings"]["inpAlignmentVersion"])
                if (data_product["translation"]["source_to_central"] == "no") and (data_product["translation"]["source_to_central"] == "yes"):
                    delete_alignment(data_product["translation"]["settings"]["outAlignmentName"], data_product["translation"]["settings"]["outAlignmentVersion"])
                if (data_product["translation"]["source_to_central"] == "yes") and (data_product["translation"]["source_to_central"] == "yes"):
                    delete_alignment(data_product["translation"]["settings"]["inpAlignmentName"], data_product["translation"]["settings"]["inpAlignmentVersion"])
                    delete_alignment(data_product["translation"]["settings"]["outAlignmentName"], data_product["translation"]["settings"]["outAlignmentVersion"])
            if "BATCH" in data_product["data_source_type"]:
                delete_helm_release(k8s_client, "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_product["name"], KUBERNETES_NAMESPACE)
            elif "STREAMING" in data_product["data_source_type"]:
                delete_streaming_data_product(data_product["_id"])
        mongodb_collection.delete_many({})
    delete_helm_repository(k8s_client, HELM_REPO_NAME, KUBERNETES_NAMESPACE)
    logger.info("Cleanup process completed.")

    logger.info("Application finished.")

    # -- END SHUTDOWN -- #

# Start FastAPI server:
app = FastAPI(
    lifespan = lifespan,
    title = __name__ + " - REST API",
    version = __version__
)

@app.get(
        path = "/dataProducts",
        description = "Retrieve all data products.",
        tags = ["Read"]
)
async def get_data_products(request: Request):
    '''
    FastAPI request handler function: HTTP GET /dataProducts.
    '''

    print("\n")
    logger.info("Received GET request to access /dataProducts resource from " + request.client.host + ":" + str(request.client.port) + ".")
    logger.info("Request is for retrieving all existing Data Products.")

    data_products = list(mongodb_collection.find())
    if len(data_products) == 0:
        return Response(status_code = status.HTTP_204_NO_CONTENT)
    else:
        return JSONResponse(status_code = status.HTTP_200_OK, content = data_products)

@app.get(
        path = "/dataProducts/{data_product_id}", 
        description = "Retrieve data product by passing its ID.",
        tags = ["Read"]
)
async def get_data_product(request: Request, data_product_id: str):
    '''
    FastAPI request handler function: HTTP GET /dataProducts/{data_product_id}.
    '''
    
    print("\n")
    logger.info("Received GET request to access /dataProducts resource from " + request.client.host + ":" + str(request.client.port) + ".")
    logger.info("Request is for retrieving the Data Product with ID: " + data_product_id + ".")

    data_product = list(mongodb_collection.find({"_id": data_product_id}))
    if len(data_product) == 0:
        return Response(status_code = status.HTTP_204_NO_CONTENT)
    else:
        return JSONResponse(status_code = status.HTTP_200_OK, content = data_product[0])

@app.post(
        path = "/dataProducts",
        description = "Onboard single data product.\
            Mappings file can be RML or YARRRML for batch data sources and MUST BE CARML for streaming data sources.\
            Optional translation files (alignment files) must be XML.\
            If no translation files are provided, semantic translation will not be used.\
            If any of the translation files is not provided, the IDENTITY alignment will then be used.",
        tags = ["Create"]
)
async def post_data_product(
    request: Request,
    data_source: DataSource = Body(...),
    mappings_file: UploadFile = File(...),
    translation_source_to_central_file: Union[UploadFile, None] = None,
    translation_central_to_target_file: Union[UploadFile, None] = None
):
    '''
    FastAPI request handler function: HTTP POST /dataProduct.
    '''

    print("\n")
    logger.info("Received POST request to access /dataProducts resource from " + request.client.host + ":" + str(request.client.port) + ".")
    logger.info("Request is for onboarding a new Data Product.")
    logger.info("Data Product details:")
    logger.info(data_source.model_dump_json(indent=4))

    mappings_content = await mappings_file.read()

    data_product = {}
    data_product["_id"] = str(uuid.uuid4())
    if data_source.details.name is not None:
        data_product["name"] = data_source.details.name
    else:
        data_product["name"] = "Default"
    if data_source.details.description is not None:
        data_product["description"] = data_source.details.description
    else:
        data_product["description"] = "Default Data Product"
    if data_source.details.owner is not None:
        data_product["owner"] = data_source.details.owner
    else:
        data_product["owner"] = "Default Data Product Owner"
    if data_source.details.glossary_terms is not None:
        data_product["glossary_terms"] = data_source.details.glossary_terms
    else:
        data_product["glossary_terms"] = ["default"]
    if data_source.details.tags is not None:
        data_product["tags"] = data_source.details.tags
    else:
        data_product["tags"] = ["default"]
    data_product["data_source_type"] = data_source.details.data_source_type
    data_product["translation"] = {}
    data_product["details"] = {}

    if (translation_source_to_central_file is None) and (translation_central_to_target_file is None):
        # No semantic translation is required.
        data_product["translation"]["defined"] = "no"
        data_product_output_kafka_topic = KAFKA_TOPIC
    if (translation_source_to_central_file is not None) and (translation_central_to_target_file is None):
        # Semantic translation is required from source to central.
        data_product["translation"]["defined"] = "yes"
        data_product["translation"]["source_to_central"] = "yes"
        data_product["translation"]["central_to_target"] = "no"
        data_product["translation"]["settings"] = {}
        translation_source_to_central_contents = await translation_source_to_central_file.read()
        input_alignment_details = create_alignment(translation_source_to_central_contents)
        await translation_source_to_central_file.close()
        translation_channel_settings = {
            "chanType": "KK",
            "source": SEMANTIC_TRANSLATOR_SOURCE_TOPIC,
            "inpAlignmentName": input_alignment_details["name"],
            "inpAlignmentVersion": input_alignment_details["version"],
            "outAlignmentName": "",
            "outAlignmentVersion": "",
            "sink": KAFKA_TOPIC,
            "parallelism": 0
        }
        data_product = create_translation_channel(translation_channel_settings, data_product)
        data_product_output_kafka_topic = SEMANTIC_TRANSLATOR_SOURCE_TOPIC
    if (translation_source_to_central_file is None) and (translation_central_to_target_file is not None):
        # Semantic translation is required from central to target.
        data_product["translation"]["defined"] = "yes"
        data_product["translation"]["source_to_central"] = "no"
        data_product["translation"]["central_to_target"] = "yes"
        data_product["translation"]["settings"] = {}
        translation_central_to_target_contents = await translation_central_to_target_file.read()
        output_alignment_details = create_alignment(translation_central_to_target_contents)
        await translation_central_to_target_file.close()
        translation_channel_settings = {
            "chanType": "KK",
            "source": SEMANTIC_TRANSLATOR_SOURCE_TOPIC,
            "inpAlignmentName": "",
            "inpAlignmentVersion": "",
            "outAlignmentName": output_alignment_details["name"],
            "outAlignmentVersion": output_alignment_details["version"],
            "sink": KAFKA_TOPIC,
            "parallelism": 0
        }
        data_product = create_translation_channel(translation_channel_settings, data_product)
        data_product_output_kafka_topic = SEMANTIC_TRANSLATOR_SOURCE_TOPIC
    if (translation_source_to_central_file is not None) and (translation_central_to_target_file is not None):
        # Semantic translation is required from source to central and from central to target.
        data_product["translation"]["defined"] = "yes"
        data_product["translation"]["source_to_central"] = "yes"
        data_product["translation"]["central_to_target"] = "yes"
        data_product["translation"]["settings"] = {}
        translation_source_to_central_contents = await translation_source_to_central_file.read()
        translation_central_to_target_contents = await translation_central_to_target_file.read()
        input_alignment_details = create_alignment(translation_source_to_central_contents)
        output_alignment_details = create_alignment(translation_central_to_target_contents)
        await translation_source_to_central_file.close()
        await translation_central_to_target_file.close()
        translation_channel_settings = {
            "chanType": "KK",
            "source": SEMANTIC_TRANSLATOR_SOURCE_TOPIC,
            "inpAlignmentName": input_alignment_details["name"],
            "inpAlignmentVersion": input_alignment_details["version"],
            "outAlignmentName": output_alignment_details["name"],
            "outAlignmentVersion": output_alignment_details["version"],
            "sink": KAFKA_TOPIC,
            "parallelism": 0
        }
        data_product = create_translation_channel(translation_channel_settings, data_product)
        data_product_output_kafka_topic = SEMANTIC_TRANSLATOR_SOURCE_TOPIC

    if isinstance(data_source.details, BatchDataSource):
        data_product = onboard_batch_data_product(data_source, mappings_file, mappings_content, data_product_output_kafka_topic, data_product)
    elif isinstance(data_source.details, StreamingDataSource):
        data_product = onboard_streaming_data_product(data_source, mappings_content, data_product_output_kafka_topic, data_product)

    await mappings_file.close()

    mongodb_collection.insert_one(data_product)

    return JSONResponse(status_code = status.HTTP_201_CREATED, content = {"message": "Data product onboarded successfully.", "data_product": data_product})

@app.delete(
        path = "/dataProducts",
        description = "Delete all data products.",
        tags = ["Delete"]
)
async def delete_data_products(request: Request):
    '''
    FastAPI request handler function: HTTP DELETE /dataProducts.
    '''

    print("\n")
    logger.info("Received DELETE request to access /dataProducts resource from " + request.client.host + ":" + str(request.client.port) + ".")
    logger.info("Request is for deleting all existing Data Products.")

    data_products = list(mongodb_collection.find())
    if len(data_products) == 0:
        return Response(status_code = status.HTTP_204_NO_CONTENT)
    else:
        for data_product in data_products:
            if data_product["translation"]["defined"] == "yes":
                # Delete translation channel:
                delete_translation_channel(data_product["translation"]["settings"]["channelId"])
                # Delete alignments/translation rules:
                if (data_product["translation"]["source_to_central"] == "yes") and (data_product["translation"]["source_to_central"] == "no"):
                    delete_alignment(data_product["translation"]["settings"]["inpAlignmentName"], data_product["translation"]["settings"]["inpAlignmentVersion"])
                if (data_product["translation"]["source_to_central"] == "no") and (data_product["translation"]["source_to_central"] == "yes"):
                    delete_alignment(data_product["translation"]["settings"]["outAlignmentName"], data_product["translation"]["settings"]["outAlignmentVersion"])
                if (data_product["translation"]["source_to_central"] == "yes") and (data_product["translation"]["source_to_central"] == "yes"):
                    delete_alignment(data_product["translation"]["settings"]["inpAlignmentName"], data_product["translation"]["settings"]["inpAlignmentVersion"])
                    delete_alignment(data_product["translation"]["settings"]["outAlignmentName"], data_product["translation"]["settings"]["outAlignmentVersion"])
            if "BATCH" in data_product["data_source_type"]:
                delete_helm_release(k8s_client, "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_product["name"], KUBERNETES_NAMESPACE)
            elif "STREAMING" in data_product["data_source_type"]:
                delete_streaming_data_product(data_product["_id"])
        mongodb_collection.delete_many({})
        return Response(status_code = status.HTTP_204_NO_CONTENT)

@app.delete(
        path = "/dataProducts/{data_product_id}",
        description = "Delete data product by passing its ID.",
        tags = ["Delete"]
)
async def delete_data_product(request: Request, data_product_id: str):
    '''
    FastAPI request handler function: HTTP DELETE /dataProducts/{data_product_id}.
    '''

    print("\n")
    logger.info("Received DELETE request to access /dataProducts resource from " + request.client.host + ":" + str(request.client.port) + ".")
    logger.info("Request is for deleting the Data Product with ID: " + data_product_id + ".")

    data_product = list(mongodb_collection.find({"_id": data_product_id}))
    if len(data_product) == 0:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        data_product = data_product[0]
        if data_product["translation"]["defined"] == "yes":
            # Delete translation channel:
            delete_translation_channel(data_product["translation"]["settings"]["channelId"])
            # Delete alignments/translation rules:
            if (data_product["translation"]["source_to_central"] == "yes") and (data_product["translation"]["source_to_central"] == "no"):
                delete_alignment(data_product["translation"]["settings"]["inpAlignmentName"], data_product["translation"]["settings"]["inpAlignmentVersion"])
            if (data_product["translation"]["source_to_central"] == "no") and (data_product["translation"]["source_to_central"] == "yes"):
                delete_alignment(data_product["translation"]["settings"]["outAlignmentName"], data_product["translation"]["settings"]["outAlignmentVersion"])
            if (data_product["translation"]["source_to_central"] == "yes") and (data_product["translation"]["source_to_central"] == "yes"):
                delete_alignment(data_product["translation"]["settings"]["inpAlignmentName"], data_product["translation"]["settings"]["inpAlignmentVersion"])
                delete_alignment(data_product["translation"]["settings"]["outAlignmentName"], data_product["translation"]["settings"]["outAlignmentVersion"])
        if "BATCH" in data_product["data_source_type"]:
            delete_helm_release(k8s_client, "data-fabric" + "-" + MORPH_RELEASE_NAME + "-" + data_product["name"], KUBERNETES_NAMESPACE)
        elif "STREAMING" in data_product["data_source_type"]:
            delete_streaming_data_product(data_product_id)
        mongodb_collection.delete_one({"_id": data_product_id})
        return Response(status_code=status.HTTP_204_NO_CONTENT)

## -- END MAIN CODE -- ##
