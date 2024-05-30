# Data Product Manager

The Data Product Manager plays a pivotal role in the Data Fabric, serving as the orchestrator for seamless data product onboarding. This component efficiently manages the integration of new data products, ensuring a coherent and standardized process.

## Data Product Definition

The data product is defined as the combination of the following metadata and artifacts:

### 1. Batch Data Products

#### 1.1 Batch Data Products – Data Files

Generated from periodic collections of raw data stored in local or remote files. When defining a Batch Data Product with files as a data source, users encounter two key properties:

- **Freshness (Optional):**

   The freshness of data sources is a crucial factor and is only applicable to Batch-type data sources. It determines how frequently the Data Fabric collects raw data from the target data source. This property is optional and can be tailored based on the user's specific requirements.

- **Path to Data File:**

   The location of the data file is specified using the file_path property. Users must specify this property to indicate where the raw data is stored, facilitating seamless data processing.

#### 1.2 Batch Data Products – Relational Databases

Generated from periodic collections of raw data stored in relational databases. When creating a Batch Data Product with relational databases as a data source, users encounter two essential considerations:

- **Freshness (Optional):**

   The freshness of data sources remains a critical aspect and is specifically relevant to Batch-type data sources. It establishes the frequency at which the Data Fabric retrieves raw data from the designated relational database. Users have the flexibility to define the freshness, determining the frequency of data collection. This property is optional, allowing users to align data retrieval with their specific operational needs.

- **Database URL:**

   The database URL is specified using the `db_url` property. This parameter indicates the location and configuration details of the relational database from which raw data is collected.

### 2. Streaming Data Products

Streaming Data Products are generated in real-time as data flows continuously from streaming sources such as Kafka or MQTT. When configuring a Streaming Data Product, users engage with key settings that ensure seamless real-time data processing:

- **Streaming Broker Topic:**

   The topic property is utilized to specify the streaming broker topic. This parameter defines the channel or subject from which real-time data is sourced.

---

## Data Product Manager Deployment

Upon successful submission of metadata and artifacts, the Data Product Manager then proceeds to generate two ConfigMaps within the Kubernetes environment. The first ConfigMap encapsulates a `config.ini` file, created by the application, and the second captures the RML file. These ConfigMaps serve as vital components, enabling seamless integration and transformation of data within the Data Fabric, with Morph-KGC leveraging both the “config.ini” and RML ConfigMaps in subsequent phases.

This deployment, inclusive of coordinating computing resources like Kubernetes, is seamlessly achieved using Helm Charts.

Furthermore, the Data Product Manager will orchestrate the deployment of various tools (Morph-KGC) in a Kubernetes cluster using Helm Controller.

- Building the Docker Image

```shell
docker build -t data-product-manager .
```

- Running with Helm:

```shell
helm install data-product-manager ./helm
```

To find the port of the Data Product Manager API, issue the following command:

```shell
kubectl get all
```

For further details, the API documentation of the Data Product Manager can be found at:

(http://127.0.0.1:port/docs)

- Install Helm Controller

```shell
kubectl apply -f https://github.com/fluxcd/flux2/releases/latest/download/install.yaml
```

- Roles and Role Binding Configuration

These roles are necessary for performing specific operations on cluster resources, such as creating ConfigMaps, HelmRepositories, and HelmReleases.

Apply the `ClusterRole` by running the following command:

```shell
kubectl apply -f k8s/clusterRole.yaml
```

## Acknowledgements

This work was partially supported by the following projects:

- **Horizon Europe aerOS**: Autonomous, scalablE, tRustworthy, intelligent European meta Operating System for the IoT edge-cloud continuum. Grant agreement 101069732
- **SNS Horizon Europe ROBUST-6G**: Smart, Automated, and Reliable Security Service Platform for 6G. Grant agreement 101139068
- **UNICO 5G I+D 6G-DATADRIVEN**: Redes de próxima generación (B5G y 6G) impulsadas por datos para la fabricación sostenible y la respuesta a emergencias. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.
- **UNICO 5G I+D 6G-CHRONOS**: Arquitectura asistida por IA para 5G-6G con red determinista para comunicaciones industriales. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.

  ![UNICO](./images/ack-logo.png)

