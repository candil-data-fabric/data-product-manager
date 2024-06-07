import json
import logging
import os
from configparser import ConfigParser
from typing import Literal, Union

import kubernetes.client
from croniter import croniter
from fastapi import Body, FastAPI, File, HTTPException, UploadFile, status
from kubernetes import config
from kubernetes.client import CustomObjectsApi
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

# Helm information
HELM_REPO_NAME = os.getenv("REPOSITORY", "aeros-common")
HELM_REPO_URL = os.getenv(
    "HELM_REPO_URL",
    "https://project_65_bot_30cb0556c5d561c94459227ce8c18168:glpat-S247U1KuYykMWwwgwKqx@gitlab.aeros-project.eu/api/v4/projects/65/packages/helm/stable"
)
# Kafka information
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

# TODO: Make these variables as above
release_name = "morph-kgc"
chart_name = "morph-kgc"
chart_version = "1.1.0"
namespace = 'default'

class BatchDataSource(BaseModel):
    freshness: str = Field(
        default=None,
        description="Only supported for data sources of batch type. " \
                    "Determines how frequently the aerOS Data Fabric collects raw data from the target data source")

class RelationalDataSource(BatchDataSource):
    data_source_type: Literal["RELATIONAL_DATABASE"]
    db_url: str = Field(description="URL of source relational databases")

class FileDataSource(BatchDataSource):
    data_source_type: Literal["FILE"]
    file_path: str = Field(description="Location of source file")

class StreamingDataSource(BaseModel):
    data_source_type: Literal["STREAMING"]
    topic: str = Field(description="Topic of source streaming broker, e.g., Kafka, MQTT")

class DataSource(BaseModel):
    details: Union[
        RelationalDataSource,
        FileDataSource,
        StreamingDataSource] = Field(discriminator="data_source_type")

    # See https://stackoverflow.com/questions/71108731/how-to-include-json-and-file-data-together-in-fastapi-endpoint
    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

def translate_to_ini(data_source, output_kafka_topic, name_mapping_file, uid):
    config = ConfigParser()

    config.add_section("CONFIGURATION")
    config.set("CONFIGURATION", "output_kafka_server", KAFKA_BROKER)
    config.set("CONFIGURATION", "output_kafka_topic", output_kafka_topic)

    config.add_section("DataSource")
    config.set("DataSource", "mappings", "config/files/" + name_mapping_file)

    if isinstance(data_source.details, FileDataSource):
        config.set("DataSource", "file_path", data_source.details.file_path)
    elif isinstance(data_source.details, RelationalDataSource):
        config.set("DataSource", "db_url", data_source.details.db_url)

    filename = f"config_{uid}.ini"
    with open(filename, "w") as config_file:
        config.write(config_file)

    return filename

def create_helm_repository(api_instance, name, namespace, repo_url):
    body = {
        "apiVersion": "source.toolkit.fluxcd.io/v1beta2",
        "kind": "HelmRepository",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "interval": "1m",
            "url": repo_url
        }
    }
    custom_api_instance = CustomObjectsApi(api_instance.api_client)

    try:
        custom_api_instance.create_namespaced_custom_object(
            group="source.toolkit.fluxcd.io",
            version="v1beta2",
            namespace=namespace,
            plural="helmrepositories",
            body=body
        )
        logger.info("HelmRepository '{0}' created successfully.".format(name))
    except Exception as e:
        logger.warning("HelmRepository '{0}': {1} already created".format(name, e))

def create_helm_release(api_instance, name, namespace, chart_name, chart_version, repository_name, name_job, configuration, name_configmap_mapping, name_configmap_config, freshness):
    body = {
        "apiVersion": "helm.toolkit.fluxcd.io/v2beta2",
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
                "name": name_job,
                "morph_kgc_config": "config/"+configuration,
                "configmap_config": name_configmap_config,
                "configmap_mapping": name_configmap_mapping,
                "image":{
                    "repository": "ghcr.io/candil-data-fabric/morph-kgc"
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
        custom_api_instance.create_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2beta2",
            namespace=namespace,
            plural="helmreleases",
            body=body
        )
        logger.info(f"HelmRelease '{name}' created successfully.")
    except Exception as e:
        logger.info(f"Error creating HelmRelease '{name}': {e}")

config.load_incluster_config()
# Initialize Kubernetes client
k8s_client = kubernetes.client.CoreV1Api()

# Create HelmRepository resource
create_helm_repository(k8s_client, HELM_REPO_NAME, namespace, HELM_REPO_URL)

# Star FastAPI server
app = FastAPI()

uid = 0

@app.post("/onboard")
async def onboard_data_product(
    data_source: DataSource = Body(...),
    rml_file: UploadFile = File(...)):

    logger.info(data_source.model_dump_json())

    rml_content = await rml_file.read()
    
    global uid
    uid += 1
    
    if data_source.details.freshness:
        try:
            croniter(data_source.details.freshness)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cron format for freshness")
        
    name_configmap_mapping = "configmap-mapping-"+str(uid)
    name_configmap_config = "configmap-config-"+str(uid)
    name_mapping_file = "mapping_file_"+str(uid)+".rml.ttl"
    name_job = "morph-kgc-app"+str(uid)

    if isinstance(data_source.details, BatchDataSource):
        configuration = translate_to_ini(data_source, "data-product-"+str(uid), name_mapping_file, uid)

    with open(configuration, "r") as file:
        file_content = file.read()

    body = kubernetes.client.V1ConfigMap(
        metadata=kubernetes.client.V1ObjectMeta(name=name_configmap_mapping),
        data={name_mapping_file: rml_content.decode('utf-8')}
    )  # V1ConfigMap |
    body_2 = kubernetes.client.V1ConfigMap(
        metadata=kubernetes.client.V1ObjectMeta(name=name_configmap_config),
        data={"config_"+str(uid)+".ini": file_content})  # V1ConfigMap |
    field_validation = 'Ignore'

    try:
        k8s_client.create_namespaced_config_map(
            namespace, body, field_validation=field_validation
        )
    except ApiException as e:
        logger.warning("Exception when calling CoreV1Api->create_namespaced_config_map: {0}\n".format(e))

    try:
        k8s_client.create_namespaced_config_map(
            namespace, body_2, field_validation=field_validation
        )
    except ApiException as e:
        logger.warning("Exception when calling CoreV1Api->create_namespaced_config_map: {0}\n".format(e))

    create_helm_release(k8s_client, release_name + str(uid), namespace, chart_name, chart_version, HELM_REPO_NAME, name_job, configuration, name_configmap_mapping, name_configmap_config, data_source.details.freshness)

    await rml_file.close()

    return {"status": "Data product onboarded successfully"}
