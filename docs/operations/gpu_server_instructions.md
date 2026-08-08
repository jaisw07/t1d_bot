# Remote GPU Server (DGX H200 Cluster) — Usage & Configuration Guide

This guide provides comprehensive instructions for accessing and utilizing the NVIDIA DGX H200 GPU cluster. It covers secure connection, image management, resource scheduling, persistent storage, data transfer, custom container image building, and service deployment.

---

## 1. Accessing the Cluster via SSH

Secure Shell (SSH) is the standard protocol for establishing an encrypted connection between your local machine and the remote DGX cluster head node.

### Connection Command
Execute the following command in your terminal (PowerShell/Command Prompt on Windows, Terminal on macOS/Linux):

```bash
ssh <username>@<server-ip>
```

*Example:*
```bash
ssh test@10.1.0.176
```

> [!NOTE]
> * **First-Time Login:** The system will prompt you to verify the server's authenticity (fingerprint check). Type `yes` to store the server's public key in your known hosts list, then enter your password when prompted.
> * **Head Node:** Once connected, you are on the head node (control plane). This node is the management center where you will execute all `kubectl` commands.

---

## 2. Managing & Finding Available Container Images

Before launching workloads, you must identify what pre-configured and custom environment images are available on the cluster.

### Listing Available Images
Run the following custom cluster utility command:

```bash
imgctl get
```

This output is divided into two distinct sections:

1. **Harbor Registry Images (`bmu-headnode:9443/...`):**
   * These are stored in the central, private Harbor registry.
   * Includes custom images built by you or your team, as well as pulled remote images.
   * *Caching Behavior:* The first time a Harbor image is referenced in a Pod manifest, the cluster pulls and caches it on the assigned worker node. Once cached, it also appears in the worker node images list.

2. **Worker Node Images:**
   * These are immediately available ("ready-to-run") on the server.
   * Includes standard NVIDIA NGC catalog images (e.g., PyTorch, TensorFlow) and cached custom images.

### Image Synchronization Rules
In multi-worker node clusters, image caching behaves as follows:
* **Automatic Synchronization:** Images with names starting with `nvcr` (NVIDIA container registry) or `bmu` are automatically synced across all worker nodes.
* **Local Caches Only:** Images without these prefixes remain only on the worker node that pulled them and will not be available on other nodes.

### Referencing Images in Pod Manifests
To use an image, combine the registry prefix, repository path, and tag:

```yaml
image: bmu-headnode:9443/nvcr.io/nvidia/pytorch:24.10-py3
```

---

## 3. Creating and Managing GPU Pods

A Pod is the smallest deployable unit in Kubernetes. To utilize GPU resources, you must specify your resource requests and limits inside a Pod configuration file.

### Checking Resource Quotas
Always verify your namespace's remaining resource limit before creating a Pod:

```bash
kubectl get resourcequotas
```

### H200 GPU Partition Sizes
The DGX H200 cluster supports Multi-Instance GPU (MIG) partitioning. Use the appropriate resource name in your manifest depending on your workload size:

| GPU Resource Name | Description | Memory Size |
| :--- | :--- | :--- |
| `nvidia.com/mig-1g.18gb` | 1 Computing Unit GPU Instance | 18 GB |
| `nvidia.com/mig-2g.35gb` | 2 Computing Unit GPU Instance | 35 GB |
| `nvidia.com/mig-3g.71gb` | 3 Computing Unit GPU Instance | 71 GB |
| `nvidia.com/gpu` | Full Physical H200 GPU | 141 GB |

### Pod Configuration Template (`pod.yaml`)
Create a file named `pod.yaml` using a terminal text editor (e.g., `vim pod.yaml`) and use the template below:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
  labels:
    app: gpu-app-label
spec:
  containers:
    - name: pytorch-container
      image: bmu-headnode:9443/nvcr.io/nvidia/pytorch:24.10-py3
      resources:
        requests:
          cpu: "8"
          memory: "16Gi"
          nvidia.com/mig-1g.18gb: 1
        limits:
          cpu: "8"
          memory: "16Gi"
          nvidia.com/mig-1g.18gb: 1
      command: ["/bin/bash", "-c", "while true; do sleep 3600; done"]
```

### Managing Pods
Use the following commands on the head node to manage your Pod lifecycle:

* **Apply Configuration:**
  ```bash
  kubectl apply -f pod.yaml
  ```
* **Check Pod Status:**
  ```bash
  kubectl get pods
  ```
* **View Detailed Diagnostic/Events Info:**
  ```bash
  kubectl describe pod gpu-pod
  ```
* **Enter Container Command Line (Interactive Bash shell):**
  ```bash
  kubectl exec -it gpu-pod -- /bin/bash
  ```
* **Delete Pod:**
  ```bash
  kubectl delete pod gpu-pod
  ```

---

## 4. Configuring Persistent Storage (HostPath Volumes)

> [!WARNING]
> **Pod Storage is Ephemeral:**
> The default internal container directory storage is temporary. When a Pod is stopped or deleted, all internally saved data is **PERMANENTLY DELETED**. You must mount persistent HostPath storage volumes or copy data out manually before deleting Pods.

### HostPath Storage Mount Types
The DGX system supports four primary host mounting directories:

1. **User Home Directory (`/home/<username>`):**
   * *Behavior:* Attaches your central network home folder.
   * *Performance:* Slower read/write performance. Recommended for static storage only. Copy files to the local container scratch directories for training/active computations.
2. **Private Storage (`/workspace/private-storage/<username>`):**
   * *Behavior:* Dedicated personal high-speed local scratch directory on the NVMe drives.
   * *Performance:* Fastest read/write performance. Recommended for training checkpoints, raw datasets, and temporary high-IO workloads.
3. **Shared Resources (`/workspace/shared-ro`):**
   * *Behavior:* Read-only directory containing common datasets uploaded by the administrator.
   * *Performance:* High-speed, shared globally across all cluster users.
4. **Shared Workspace (`/workspace/shared-workspace`):**
   * *Behavior:* Read/Write shared collaborative directory.
   * *Performance:* High-speed. Allows multiple users to read and write shared data assets.

### Crucial Volume-Label Rule
You **MUST** declare the following label under the Pod's `metadata.labels` configuration whenever attaching any HostPath storage. Failing to include this label will result in volume scheduling errors:

```yaml
labels:
  app.kubernetes.io/name: local-storage
```

### Storage Mounting Manifest Examples

#### Private Storage Mount
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-storage-pod
  labels:
    app.kubernetes.io/name: local-storage
spec:
  containers:
    - name: pytorch-container
      image: bmu-headnode:9443/nvcr.io/nvidia/pytorch:24.10-py3
      command: ["/bin/bash", "-c", "while true; do sleep 3600; done"]
      resources:
        limits:
          nvidia.com/gpu: 1
        requests:
          nvidia.com/gpu: 1
      volumeMounts:
        - name: private-vol
          mountPath: /private-storage # Container directory where storage appears
  volumes:
    - name: private-vol
      hostPath:
        path: /workspace/private-storage/dgx-s-college-aiml-1234 # Replace path suffix with your username
        type: DirectoryOrCreate
```

#### Shared Resources (Read-Only) Mount
```yaml
      volumeMounts:
        - name: shared-ro-vol
          mountPath: /shared-ro
          readOnly: true
  volumes:
    - name: shared-ro-vol
      hostPath:
        path: /workspace/shared-ro
        type: Directory
```

#### Combined Multi-Storage Manifest
Use this manifest skeleton to mount all four types of storage simultaneously:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-all-storage
  labels:
    app.kubernetes.io/name: local-storage
spec:
  containers:
    - name: pytorch-container
      image: bmu-headnode:9443/nvcr.io/nvidia/pytorch:24.10-py3
      command: ["/bin/bash", "-c", "while true; do sleep 3600; done"]
      resources:
        limits:
          nvidia.com/gpu: 1
        requests:
          nvidia.com/gpu: 1
      volumeMounts:
        - name: private-storage
          mountPath: /private-storage
        - name: shared-read-only
          mountPath: /shared-ro
          readOnly: true
        - name: shared-workspace
          mountPath: /shared-workspace
        - name: user-home
          mountPath: /user-home
  volumes:
    - name: user-home
      hostPath:
        path: /home/dgx-s-college-aiml-1234 # Replace with your username
        type: Directory
    - name: private-storage
      hostPath:
        path: /workspace/private-storage/dgx-s-aiml-user # Replace with your username
        type: DirectoryOrCreate
    - name: shared-read-only
      hostPath:
        path: /workspace/shared-ro
        type: Directory
    - name: shared-workspace
      hostPath:
        path: /workspace/shared-workspace
        type: Directory
```

> [!NOTE]
> You may notice a warning message stating `groups: cannot find name for group ID ...` when exec-ing into Pods using local-storage. This is normal behavior resulting from HostPath user ID mappings and has **no impact** on the operation or performance of your container workloads.

---

## 5. Sharing Files and Folders (Data Transfer)

To transfer data between your local machine, the head node server, and running Pods, follow these multi-step workflows.

### Workflow A: Transferring Data from Local Machine to Pod

1. **Upload from Local Machine to Head Node Server:**
   Use SCP in your local machine terminal:
   ```bash
   # Upload a file
   scp file.tar.gz <your-username>@<server-ip>:/home/<your-username>/
   
   # Upload a folder recursively
   scp -r project_folder/ <your-username>@<server-ip>:/home/<your-username>/
   ```

2. **Copy from Head Node Server to Pod:**
   Use `kubectl cp` on the head node server terminal:
   ```bash
   # Copy file to Pod directory
   kubectl cp /home/<your-username>/file.tar.gz <pod-name>:/workspace/
   
   # Copy folder to Pod directory
   kubectl cp /home/<your-username>/project_folder <pod-name>:/workspace/project_folder
   ```

### Workflow B: Transferring Data from Pod to Local Machine

1. **Copy from Pod to Head Node Server:**
   Use `kubectl cp` on the head node server terminal:
   ```bash
   kubectl cp <pod-name>:/workspace/output_results.csv /home/<your-username>/output_results.csv
   ```

2. **Download from Head Node Server to Local Machine:**
   Use SCP on your local machine terminal:
   ```bash
   scp <your-username>@<server-ip>:/home/<your-username>/output_results.csv C:\Users\YourUser\Downloads\
   ```

> [!NOTE]
> During `kubectl cp` transfers, you may see an informational warning in your terminal: `tar: Removing leading '/' from member names`. This is a harmless warning generated by the internal `tar` utility that Kubernetes uses to package transfers. It indicates paths are being resolved correctly and can be ignored.

---

## 6. Building Custom Images via Kaniko

Kaniko is a utility used to build container images from a Dockerfile inside a Kubernetes cluster without requiring a Docker daemon or root system privileges. Once built, images are automatically pushed to the private Harbor registry.

### Prerequisites
* **Project Directory:** A directory on the head node (`/home/<username>/<project-folder>`) containing your source files and a valid `Dockerfile` placed directly at the root of the project folder.
* **Harbor Registry Secret:** A Kubernetes secret named `regcred` must exist in your namespace to allow Kaniko to authenticate with Harbor. Verify it exists using:
  ```bash
  kubectl get secret | grep regcred
  ```

### Builder Configuration Pod (`kaniko-pod.yaml`)
Create a file named `kaniko-pod.yaml` and configure the highlighted values:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: kaniko-build-pod
  labels:
    app.kubernetes.io/name: local-storage
    app.kubernetes.io/custom: kaniko
spec:
  restartPolicy: Never
  volumes:
    - name: registry-auth
      secret:
        secretName: regcred
        items:
          - key: .dockerconfigjson
            path: config.json
    - name: source-code
      hostPath:
        path: /home/dgx-s-college-aiml-1234/ # !!! STEP 1: Replace with your absolute home directory path
        type: Directory
  containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:latest
      args:
        - "--dockerfile=/workspace/my-app/Dockerfile" # !!! STEP 2: Replace "my-app" with your project folder name
        - "--context=dir:///workspace/my-app"          # !!! STEP 3: Replace "my-app" with your project folder name
        - "--destination=bmu-headnode:9443/custom/username-myapp:v1" # !!! STEP 4: Name your custom image
        - "--insecure"
        - "--skip-tls-verify"
      volumeMounts:
        - name: registry-auth
          mountPath: /kaniko/.docker
        - name: source-code
          mountPath: /workspace
```

### Build Execution Workflow
1. **Apply the build Pod:**
   ```bash
   kubectl apply -f kaniko-pod.yaml
   ```
2. **Monitor the logs in real time:**
   ```bash
   kubectl logs kaniko-build-pod -f
   ```
3. **Wait for completion:** The Pod status will change to `Completed`.
4. **Clean up the builder Pod:**
   ```bash
   kubectl delete pod kaniko-build-pod
   ```
5. **Verify Harbor Registry Image:**
   ```bash
   imgctl get
   ```

---

## 7. Creating Deployments & Exposing Services

A Deployment manages the replication and health of your container workloads, while a Service exposes network ports to make your applications accessible outside of the cluster.

### Port Definitions in Kubernetes
* **`port`:** The port on which the Service is exposed internally inside the cluster.
* **`targetPort` (ContainerPort):** The port inside the container where your application listens (e.g., Streamlit on port `8501`, JupyterLab on `8888`).
* **`NodePort`:** A dedicated port mapping opened on all cluster worker nodes (range `30000–32767`). Allows external clients to access your Pod.

### Single-File Deployment & NodePort Service Template
This template configures a Deployment to spin up an application (running Streamlit) and exposes it externally via a NodePort Service:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: streamlit-deployment
  labels:
    app: streamlit-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: streamlit-app
  template:
    metadata:
      labels:
        app: streamlit-app
    spec:
      containers:
        - name: app-container
          image: bmu-headnode:9443/custom/username-streamlit:v1
          ports:
            - containerPort: 8501
          command: ["/bin/bash", "-c", "streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]
          resources:
            limits:
              nvidia.com/mig-1g.18gb: 1
            requests:
              nvidia.com/mig-1g.18gb: 1
---
apiVersion: v1
kind: Service
metadata:
  name: streamlit-service
spec:
  type: NodePort
  selector:
    app: streamlit-app
  ports:
    - port: 8501
      targetPort: 8501
      protocol: TCP
```

### Alternative: Exposing an Existing Pod via CLI
If you already have a running Pod named `my-pod`, you can expose it as a Service immediately using the command line:

```bash
kubectl expose pod my-pod --target-port=8888 --type=NodePort --name=my-pod-service
```

### Service Administration Commands
* **List Services and NodePorts:**
  ```bash
  kubectl get services
  ```
  *In the output, note the mapped port under the `PORT(S)` column (e.g., `8501:31452/TCP`). Here, `31452` is the external NodePort.*
* **View Service Details:**
  ```bash
  kubectl describe service streamlit-service
  ```
* **Accessing the Application:**
  Open your web browser and navigate to:
  `http://<any-worker-node-ip>:<nodeport>` (e.g., `http://10.1.0.176:31452`).
* **Delete Service:**
  ```bash
  kubectl delete service streamlit-service
  ```

---

## 8. Summary of Administrative Contacts & Support
For any questions regarding account setup, Harbor credentials, SSH key authorization, network port access, or namespace quotas:
* **Support Email:** training_support.ai@giindia.com
