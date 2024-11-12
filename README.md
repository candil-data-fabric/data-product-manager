# Data Product Manager

The Data Product Manager plays a pivotal role in the Data Fabric, serving as the orchestrator for seamless data product onboarding. This component efficiently manages the integration of new data products, ensuring a coherent and standardized process.

## Data Product Definition

The data product is defined as the combination of the following metadata and artifacts:

### 1. Batch Data Products

#### 1.1 Batch Data Products – Data Files

Generated from periodic collections of raw data stored in local or remote files. When defining a Batch Data Product with files as a data source, these are the details that must be provided:

- **Name (Optional)**: Name of the Data Product.

- **Description (Optional)**: Descriptive text of the Data Product.

- **Tags (Optional)**: List of tags that identify and categorize the Data Product.

- **Data Source Type**: String that identifies the type of the Data Product within the Data Product Manager. For these Batch Data Products it must always be `BATCH_FILE`.

- **Freshness (Optional)**: The freshness of data sources is a crucial factor and is only applicable to Batch-type data sources. It determines how frequently the aerOS Data Fabric collects raw data from the target data source. This property is optional and can be tailored based on the user's specific requirements.

- **Path to Data File**: The location of the data file is specified using the `file_path` property. Users must specify this property to indicate where the raw data is stored, facilitating seamless data processing.

#### 1.2 Batch Data Products – Relational Databases

Generated from periodic collections of raw data stored in relational databases. When creating a Batch Data Product with relational databases as a data source, these are the details that must be provided:

- **Name (Optional)**: Name of the Data Product.

- **Description (Optional)**: Descriptive text of the Data Product.

- **Tags (Optional)**: List of tags that identify and categorize the Data Product.

- **Data Source Type**: String that identifies the type of the Data Product within the Data Product Manager. For these Batch Data Products it must always be `BATCH_RELATIONAL_DATABASE`.

- **Freshness (Optional)**: The freshness of data sources remains a critical aspect and is specifically relevant to Batch-type data sources. It establishes the frequency at which the aerOS Data Fabric retrieves raw data from the designated relational database. Users have the flexibility to define the freshness, determining the frequency of data collection. This property is optional, allowing users to align data retrieval with their specific operational needs.

- **Database URL**: The database URL is specified using the `db_url` property. This parameter indicates the location and configuration details of the relational database from which raw data is collected.

### 2. Streaming Data Products

Streaming Data Products are generated in real-time as data flows continuously from streaming sources such as Kafka or MQTT. When configuring a Streaming Data Product, these are the details that must be provided:

#### 2.1	Streaming Data Products – Kafka Source

- **Name (Optional)**: Name of the Data Product.

- **Description (Optional)**: Descriptive text of the Data Product.

- **Tags (Optional)**: List of tags that identify and categorize the Data Product.

- **Input format**: Specifies the format for the input data. Valid values are `XML`, `JSON` or `CSV`.

- **Input Topic**: The topic property is utilized to specify the streaming broker topic. This parameter defines the channel or subject from which real-time data is sourced.

- **Data Source Type**: String that identifies the type of the Data Product within the Data Product Manager. For these Streaming Data Products it must always be `STREAMING_KAFKA`.

- **Host**: IP address or FQDN where the Kafka broker is reachable.

- **Port**: Port number where the Kafka broker is reachable.

#### 2.2	Streaming Data Products – MQTT Source

- **Name (Optional)**: Name of the Data Product.

- **Description (Optional)**: Descriptive text of the Data Product.

- **Tags (Optional)**: List of tags that identify and categorize the Data Product.

- **Input format**: Specifies the format for the input data. Valid values are `XML`, `JSON` or `CSV`.

- **Input Topic**: The topic property is utilized to specify the streaming broker topic. This parameter defines the channel or subject from which real-time data is sourced.

- **Data Source Type**: String that identifies the type of the Data Product within the Data Product Manager. For these Streaming Data Products it must always be `STREAMING_MQTT`.

- **Host**: IP address or FQDN where the MQTT broker is reachable.

- **Port**: Port number where the MQTT broker is reachable.

- **Protocol**: Protocol that must be used for the communication with the MQTT broker. Expected values are `tcp` or `udp`.

## Current versions:
- **Data Product Manager application**: 3.0.0 (November 12th, 2024).
- **Dockerfile**: 3.0.0 (November 12th, 2024).

## Data Product Manager Deployment

The Data Product Manager is intended to be deployed by installing a Helm Chart.

For batch data sources/products, upon successful submission of metadata and artifacts, the Data Product Manager then proceeds to generate two ConfigMaps within the Kubernetes environment. The first ConfigMap encapsulates a `config.ini` file, created by the application, and the second captures the RML/YARRRML mappings file. These ConfigMaps serve as vital components, enabling seamless integration and transformation of data within the Data Fabric, with Morph-KGC leveraging both the `config.ini` and RML ConfigMaps in subsequent phases. For streaming data sources, the Data Product Manager sends HTTP POST requests to the Semantic Annotator to create the corresponding channels.

This deployment, inclusive of coordinating computing resources like Kubernetes, is seamlessly achieved using Helm Charts and HTTP requests.

When creating batch data products, the Data Product Manager will orchestrate the deployment of Morph-KGC in a Kubernetes cluster using Helm Controller.

For further details, the API documentation of the Data Product Manager can be found at:

- `http://<host>:<port>/docs`
- `http://<host>:<port>/redoc`

To check the host and port of the Data Product Manager API, issue the following command after the deployment:

```bash
$ kubectl get all
```

### Environmental variables

These are the environmental variables that can be configured:

|                    **Variable**                   |                                                                                         **Description**                                                                                         |
|:-------------------------------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|               `KUBERNETES_NAMESPACE`              |                                                                    Namespace where Morph-KGC Helm Releases will be deployed.                                                                    |
|                  `HELM_REPO_NAME`                 |                                                                   Name of the Helm Repository that stores Morph-KGC releases.                                                                   |
|                  `HELM_REPO_URL`                  |                                                                           URL where the Helm Repository is reachable.                                                                           |
|                   `KAFKA_BROKER`                  |                                                          Endpoint <IP_or_FQDN:port_number> where the output Kafka broker is reachable.                                                          |
|                   `KAFKA_TOPIC`                   |                                                                 Name of the topic where final RDF triples will be written.                                                                      |
|                  `KAFKA_GROUP_ID`                 |                                                                              Group ID for the output Kafka broker.                                                                              |
|                `MORPH_RELEASE_NAME`               |                                                                               Name of the Morph-KGC Helm Release.                                                                               |
|              `MORPH_IMAGE_REPOSITORY`             |                                                                Repository URL where the Docker image of Morph-KGC is available.                                                                 |
|                 `MORPH_CHART_NAME`                |                                                                                Name of the Morph-KGC Helm Chart.                                                                                |
|               `MORPH_CHART_VERSION`               |                                                                               Version of the Morph-KGC Helm Chart.                                                                              |
|              `SEMANTIC_ANNOTATOR_URI`             |                                                                      HTTP(S) URI where the Semantic Annotator is reachable.                                                                     |
|      `SEMANTIC_ANNOTATOR_ERROR_TOPIC_ENABLED`     |                                             Whether or not the error topic for the Semantic Annotator is used (for logging and debugging purposes).                                             |
|  `SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC_ENABLED` |                                         Whether or not the input monitor topic for the Semantic Annotator is used (for logging and debugging purposes).                                         |
| `SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC_ENABLED` |                                         Whether or not the output monitor topic for the Semantic Annotator is used (for logging and debugging purposes).                                        |
|          `SEMANTIC_ANNOTATOR_ERROR_TOPIC`         |                                                     Name of the topic where Semantic Annotator error messages will be written (if enabled).                                                     |
|      `SEMANTIC_ANNOTATOR_INPUT_MONITOR_TOPIC`     |                                                 Name of the topic where Semantic Annotator input monitor messages will be written (if enabled).                                                 |
|     `SEMANTIC_ANNOTATOR_OUTPUT_MONITOR_TOPIC`     |                                                 Name of the topic where Semantic Annotator output monitor messages will be written (if enabled).                                                |
|         `SEMANTIC_ANNOTATOR_OUTPUT_FORMAT`        | Output format for the RDF triples generated by the Semantic Annotator. Multiple valid values are available (see Semantic Annotator documentation). `NQUADS` is recommended for homogeneization. |
|             `SEMANTIC_TRANSLATOR_URI`             |                                                                     HTTP(S) URI where the Semantic Translator is reachable.                                                                     |
|         `SEMANTIC_TRANSLATOR_SOURCE_TOPIC`        |                                                           Name of the topic where the Semantic Translator will read RDF triples from.                                                           |
|                   `MONGO_DB_URI`                  |                                                      MongoDB URI <mongodb://IP_or_FQDN:port_number/> where the MongoDB server is reachable.                                                     |

When installing the Helm Chart, upgrade it with a custom `myvalues.yaml` file where you define the environmental variables that you wish to override.

## Interacting with the Data Product Manager

### 1. Onboarding Data Products

The onboarding process can be done either using the Swagger UI or by sending HTTP POST requests.

#### 1.1 Batch Data Products - Data Files

Define a JSON dictionary that contains the following details:

```json
{
   "details": {
   "name": "Data Product Name",
   "description": "Data Product Description",
   "owner": "Data Product Owner URI",
   "glossary_terms": [
      "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
   ],
   "tags": [
      "Tag 1", "Tag 2", "Tag 3", "Tag N"
   ],
   "freshness": "Freshness (in crontab/cronjob format)",
   "data_source_type": "BATCH_FILE",
   "file_path": "URI of the data file"
   }
}
```

When using Swagger UI, paste that JSON in the `data_source` block and attach the mappings file and optional translation files using the dialog.
Once done, click on `Execute` to onboard the Data Product.

When sending an HTTP POST request, use the following command as template:

```shell
curl -X 'POST' 'http://localhost:<port>/dataProducts' \
   -H 'accept: application/json' \
   -H 'Content-Type: multipart/form-data' \
   -F 'data_source={
         "details": {
         "name": "Data Product Name",
         "description": "Data Product Description",
         "owner": "Data Product Owner URI",
         "glossary_terms": [
            "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
         ],
         "tags": [
            "Tag 1", "Tag 2", "Tag 3", "Tag N"
         ],
         "freshness": "Freshness (in crontab/cronjob format)",
         "data_source_type": "BATCH_FILE",
         "file_path": "URI of the data file"
         }
      }' \
   # Mappings file is mandatory. Extension can be RML or YARRRML.
   -F 'mappings_file=@path_to_mappings_file'
   # Translation file from source ontology to central ontology is optional. Extension must always be XML.
   -F 'translation_source_to_central_file=@path_to_translation_source_to_central_file'
   # Translation file from central ontology to target ontology is optional. Extension must always be XML.
   -F 'translation_central_to_target_file=@path_to_translation_central_to_target_file'
```

Once the onboarding has completed, a JSON object with details about the Data Product will be returned in response.

#### 1.2 Batch Data Products - Relational Databases

Define a JSON dictionary that contains the following details:

```json
{
   "details": {
   "name": "Data Product Name",
   "description": "Data Product Description",
   "owner": "Data Product Owner URI",
   "glossary_terms": [
      "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
   ],
   "tags": [
      "Tag 1", "Tag 2", "Tag 3", "Tag N"
   ],
   "freshness": "Freshness (in crontab/cronjob format)",
   "data_source_type": "BATCH_RELATIONAL_DATABASE",
   "db_url": "URL of the database"
   }
}
```

When using Swagger UI, paste that JSON in the `data_source` block and attach the mappings file and optional translation files using the dialog.
Once done, click on `Execute` to onboard the Data Product.

When sending an HTTP POST request, use the following command as template:

```shell
curl -X 'POST' 'http://localhost:<port>/dataProducts' \
   -H 'accept: application/json' \
   -H 'Content-Type: multipart/form-data' \
   -F 'data_source={
         "details": {
         "name": "Data Product Name",
         "description": "Data Product Description",
         "owner": "Data Product Owner URI",
         "glossary_terms": [
            "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
         ],
         "tags": [
            "Tag 1", "Tag 2", "Tag 3", "Tag N"
         ],
         "freshness": "Freshness (in crontab/cronjob format)",
         "data_source_type": "BATCH_RELATIONAL_DATABASE",
         "db_url": "URL of the database"
         }
      }' \
   # Mappings file is mandatory. Extension can be RML or YARRRML.
   -F 'mappings_file=@path_to_mappings_file'
   # Translation file from source ontology to central ontology is optional. Extension must always be XML.
   -F 'translation_source_to_central_file=@path_to_translation_source_to_central_file'
   # Translation file from central ontology to target ontology is optional. Extension must always be XML.
   -F 'translation_central_to_target_file=@path_to_translation_central_to_target_file'
```

Once the onboarding has completed, a JSON object with details about the Data Product will be returned in response.

#### 1.3 Streaming Data Products - Kafka Sources

Define a JSON dictionary that contains the following details:

```json
{
   "details": {
   "name": "Data Product Name",
   "description": "Data Product Description",
   "owner": "Data Product Owner URI",
   "glossary_terms": [
      "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
   ],
   "tags": [
      "Tag 1", "Tag 2", "Tag 3", "Tag N"
   ],
   "input_format": "Expected valid values are XML, JSON or CSV",
   "input_topic": "Name of the input topic where source data is written",
   "data_source_type": "STREAMING_KAFKA",
   "host": "IP or FQDN where the Kafka broker is reachable",
   "port": "Port number where the Kafka broker is reachable (integer, without double quotes)"
   }
}
```

When using Swagger UI, paste that JSON in the `data_source` block and attach the mappings file and optional translation files using the dialog.
Beware that Streaming Data Products require RML/CARML mapping files.
Once done, click on `Execute` to onboard the Data Product.

When sending an HTTP POST request, use the following command as template:

```shell
curl -X 'POST' 'http://localhost:<port>/dataProducts' \
   -H 'accept: application/json' \
   -H 'Content-Type: multipart/form-data' \
   -F 'data_source={
         "details": {
         "name": "Data Product Name",
         "description": "Data Product Description",
         "owner": "Data Product Owner URI",
         "glossary_terms": [
            "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
         ],
         "tags": [
            "Tag 1", "Tag 2", "Tag 3", "Tag N"
         ],
         "input_format": "Expected valid values are XML, JSON or CSV",
         "input_topic": "input-topic",
         "data_source_type": "STREAMING_KAFKA",
         "host": "IP or FQDN where the Kafka broker is reachable",
         "port": "Port number where the Kafka broker is reachable (integer, without double quotes)"
         }
      }' \
   # Mappings file is mandatory. Extension must always RML (CARML mappings).
   -F 'mappings_file=@path_to_mappings_file'
   # Translation file from source ontology to central ontology is optional. Extension must always be XML.
   -F 'translation_source_to_central_file=@path_to_translation_source_to_central_file'
   # Translation file from central ontology to target ontology is optional. Extension must always be XML.
   -F 'translation_central_to_target_file=@path_to_translation_central_to_target_file'
```

Once the onboarding has completed, a JSON object with details about the Data Product will be returned in response.

#### 1.4 Streaming Data Products - MQTT Sources

Define a JSON dictionary that contains the following details:

```json
{
   "details": {
   "name": "Data Product Name",
   "description": "Data Product Description",
   "owner": "Data Product Owner URI",
   "glossary_terms": [
      "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
   ],
   "tags": [
      "Tag 1", "Tag 2", "Tag 3", "Tag N"
   ],
   "input_format": "Expected valid values are XML, JSON or CSV",
   "input_topic": "input/topic",
   "data_source_type": "STREAMING_MQTT",
   "host": "IP or FQDN where the MQTT broker is reachable",
   "port": "Port number where the MQTT broker is reachable (integer, without double quotes)",
   "protocol": "Protocol that must be used for the communication with the MQTT broker. Expected values are tcp or udp"
   }
}
```

When using Swagger UI, paste that JSON in the `data_source` block and attach the mappings file and optional translation files using the dialog.
Beware that Streaming Data Products require RML/CARML mapping files.
Once done, click on `Execute` to onboard the Data Product.

When sending an HTTP POST request, use the following command as template:

```shell
curl -X 'POST' 'http://localhost:<port>/dataProducts' \
   -H 'accept: application/json' \
   -H 'Content-Type: multipart/form-data' \
   -F 'data_source={
         "details": {
         "name": "Data Product Name",
         "description": "Data Product Description",
         "owner": "Data Product Owner URI",
         "glossary_terms": [
            "Term 1 URI", "Term 2 URI", "Term 3 URI", "Term N URI"
         ],
         "tags": [
            "Tag 1", "Tag 2", "Tag 3", "Tag N"
         ],
         "input_format": "Expected valid values are XML, JSON or CSV",
         "input_topic": "input/topic",
         "data_source_type": "STREAMING_MQTT",
         "host": "IP or FQDN where the MQTT broker is reachable",
         "port": "Port number where the MQTT broker is reachable (integer, without double quotes)",
         "protocol": "Protocol that must be used for the communication with the MQTT broker. Expected values are tcp or udp"
         }
      }' \
   # Mappings file is mandatory. Extension must always RML (CARML mappings).
   -F 'mappings_file=@path_to_mappings_file'
   # Translation file from source ontology to central ontology is optional. Extension must always be XML.
   -F 'translation_source_to_central_file=@path_to_translation_source_to_central_file'
   # Translation file from central ontology to target ontology is optional. Extension must always be XML.
   -F 'translation_central_to_target_file=@path_to_translation_central_to_target_file'
```

Once the onboarding has completed, a JSON object with details about the Data Product will be returned in response.

### 2. Reading existing Data Products

There are two HTTP GET methods available for getting information about the existing Data Products:

#### 2.1 Read all existing Data Products

This method returns a list with details of all existing Data Products.
It can be executed using Swagger UI or by sending the following HTTP GET request:

```shell
curl -X 'GET' 'http://localhost:<port>/dataProducts' \
   -H 'accept: application/json'
```

#### 2.2 Read an existing Data Product

This method returns the details of an existing Data Product which ID is passed as parameter.
It can be executed using Swagger UI or by sending the following HTTP GET request:

```shell
curl -X 'GET' 'http://localhost:<port>/dataProducts/{data_product_id}' \
   -H 'accept: application/json'
```

Replace `{data_product_id}` with the Data Product ID that was returned during the onboarding process.

### 3. Deleting Data Products

There are two HTTP DELETE methods available for deleting Data Products:

#### 3.1 Delete all existing Data Products

This method deletes all existing Data Products.
It can be executed using Swagger UI or by sending the following HTTP DELETE request:

```shell
curl -X 'DELETE' 'http://localhost:<port>/dataProducts'
```

#### 3.2 Delete an existing Data Product

This method deletes only the Data Product which ID is passed as parameter.
It can be executed using Swagger UI or by sending the following HTTP DELETE request:

```shell
curl -X 'DELETE' 'http://localhost:<port>/dataProducts/{data_product_id}'
```

Replace `{data_product_id}` with the Data Product ID that was returned during the onboarding process.

## Authors

- Telefónica I+D (TID): Ignacio Domínguez Martínez-Casanueva and Lucía Cabanillas Rodríguez.

- Universidad Politécnica de Madrid (UPM): Luis Bellido Triana and David Martínez García.


## Acknowledgements

This work was partially supported by the following projects:

- **Horizon Europe aerOS**: Autonomous, scalablE, tRustworthy, intelligent European meta Operating System for the IoT edge-cloud continuum. Grant agreement 101069732
- **SNS Horizon Europe ROBUST-6G**: Smart, Automated, and Reliable Security Service Platform for 6G. Grant agreement 101139068
- **UNICO 5G I+D 6G-DATADRIVEN**: Redes de próxima generación (B5G y 6G) impulsadas por datos para la fabricación sostenible y la respuesta a emergencias. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.
- **UNICO 5G I+D 6G-CHRONOS**: Arquitectura asistida por IA para 5G-6G con red determinista para comunicaciones industriales. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.

  ![UNICO](./images/ack-logo.png)
