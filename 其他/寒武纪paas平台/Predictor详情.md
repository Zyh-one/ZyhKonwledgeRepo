在线服务详情

```
{
    "metadata": {
        "creationTimestamp": "2026-08-31T12:42:38.000Z",
        "deletionTimestamp": "0001-01-01T00:00:00.000Z",
        "labels": null,
        "name": "deepseek-v4-dp2tp4",
        "namespace": "e23f5b20fb9b42d3ac674f9691a0b9b1",
        "uid": "fec724d9-5ac1-472f-87db-3da734ece1db",
        "userID": "wangshoutian",
        "username": "wangshoutian"
    },
    "spec": {
        "acl": {
            "effected": [
                "Read",
                "Write",
                "WriteACL"
            ],
            "project": "ReadOnly"
        },
        "auth": {
            "authApps": [],
            "type": "authapp"
        },
        "duration": 0,
        "preferScaleINNodes": [],
        "protocol": "userDefined",
        "routers": [
            {
                "id": "b92e959e-314b-477c-b399-7dc3f1036f15",
                "name": "deepseek-v4-flash-ai-coding"
            }
        ],
        "scenario": "custom",
        "transport": "rest",
        "versions": [
            {
                "components": [
                    {
                        "distributed": true,
                        "distributedSpec": {
                            "enableWorkerServing": true,
                            "size": 2
                        },
                        "flavorID": "1f671259-d42a-4944-841a-f8c6e0b8df70",
                        "flavorInfo": {
                            "cpuMilliCoresLimit": 128000,
                            "cpuMilliCoresRequest": 16000,
                            "credit": 20000000,
                            "deleted": false,
                            "enabled": true,
                            "ephemeralStorageGb": 50,
                            "ephemeralStorageGbLimit": 400,
                            "flavorAppTypes": [
                                "dataProcessing",
                                "deployment",
                                "evaluationJob",
                                "job",
                                "llmAgent",
                                "machineLearning",
                                "notebook",
                                "predictor",
                                "prelabelling",
                                "trainingJob",
                                "trainingJobExperiment",
                                "trainingJobLlmFinetune",
                                "trainingJobScenario"
                            ],
                            "flavorType": "MLU",
                            "gpuMilliCores": 0,
                            "gpuType": "",
                            "id": "1f671259-d42a-4944-841a-f8c6e0b8df70",
                            "mellanoxRdma": 4,
                            "mellanoxRdmaMode": "roce",
                            "mellanoxRdmaType": "share",
                            "memMbLimit": 524288,
                            "memMbRequest": 65536,
                            "mluMilliCores": 4000,
                            "mluType": "mlu590",
                            "name": "M9DK4-ROCE4-DRAIN-0830",
                            "namespaces": null,
                            "nodeSelector": {
                                "ownership": "ai-coding",
                                "project": "ai-coding",
                                "rdma-num": "4"
                            },
                            "nodes": null,
                            "organizationIDs": [
                                ""
                            ]
                        },
                        "modelPackages": [
                            {
                                "deleted": false,
                                "envs": [
                                    {
                                        "name": "VLLM_LATENCY_DEBUG",
                                        "value": "false"
                                    },
                                    {
                                        "name": "MAX_NUM_BATCHED_TOKENS",
                                        "value": "8256"
                                    },
                                    {
                                        "name": "MAX_MODEL_LEN",
                                        "value": "1048576"
                                    },
                                    {
                                        "name": "MAX_NUM_SEQS",
                                        "value": "32"
                                    },
                                    {
                                        "name": "MODEL_PATH",
                                        "value": "/workspace/volume/softdata1/models/Qwen/hairui/0731_dsv4/DeepSeek-V4-Flash-0731-W4A8"
                                    },
                                    {
                                        "name": "LOCAL_SSD_MODEL_PATH",
                                        "value": "/workspace/hostpath/hostpath0/DeepSeek-V4-Flash-0731-W4A8"
                                    },
                                    {
                                        "name": "TP_SIZE",
                                        "value": "4"
                                    },
                                    {
                                        "name": "DP_SIZE",
                                        "value": "2"
                                    },
                                    {
                                        "name": "BLOCK_SIZE",
                                        "value": "256"
                                    },
                                    {
                                        "name": "OTLP_TRACES_ENDPOINT",
                                        "value": "grpc://jaeger.observability:4317"
                                    },
                                    {
                                        "name": "OTEL_SERVICE_NAME",
                                        "value": "deepseek-v4-flash"
                                    },
                                    {
                                        "name": "MLU_GRAPH_CAPTURE_LIST",
                                        "value": "2,4,8,16,24,32"
                                    }
                                ],
                                "id": "9c2ada6d-8ad3-40db-b1c6-6539d990672e",
                                "name": "deepseekv4-flash",
                                "parameters": [],
                                "restApis": [
                                    {
                                        "method": "GET",
                                        "path": "/v1/chat/completions"
                                    }
                                ],
                                "versionID": "52dbb8eb-4499-449e-97f6-c598a58cba1e",
                                "versionName": "0.0.9"
                            }
                        ],
                        "name": "standalone",
                        "nodeNames": [],
                        "privateNodePoolDescription": "ai-coding专用",
                        "privateNodePoolID": "e1194763-cb39-426f-a86f-f21adc5cab89",
                        "privateNodePoolName": "ai-coding",
                        "replicas": 1
                    }
                ],
                "id": "013049a4-5e62-4307-a196-e0c66cb875ba",
                "name": "0.0.1",
                "replicas": 2,
                "storageVolumes": [
                    {
                        "volume": {
                            "deleted": false,
                            "id": "9691e5fe-2bc2-4832-a207-36a341965419",
                            "name": "softdata1",
                            "readOnly": true,
                            "source": "private"
                        }
                    },
                    {
                        "volume": {
                            "deleted": false,
                            "id": "98299b7d-f470-4cbf-ba72-ff3ede4dffd1",
                            "name": "llm-new",
                            "readOnly": false,
                            "source": "private"
                        }
                    }
                ],
                "traffic": 100
            }
        ]
    },
    "status": {
        "expirationTime": "0001-01-01T00:00:00.000Z",
        "internalURL": "",
        "nodeNames": null,
        "overview": "Running",
        "runningTimestamp": "2026-09-02T11:50:40.304Z",
        "statusLog": [
            {
                "lastTransitionTime": "2026-09-02T11:51:30.209Z",
                "probeTime": "2026-09-02T11:50:40.304Z",
                "status": "Running",
                "subResources": {
                    "1d25869c-00e0-4205-aaf3-7471b72146e6": {
                        "events": [
                            {
                                "count": 16,
                                "firstTimestamp": "2026-09-02T11:51:45.000Z",
                                "lastTimestamp": "2026-09-02T11:54:06.000Z",
                                "message": "Readiness probe failed: Get \"http://10.8.141.49:9100/health\": dial tcp 10.8.141.49:9100: connect: connection refused",
                                "reason": "Unhealthy",
                                "source": "kubelet",
                                "type": "Warning"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:50:53.000Z",
                                "lastTimestamp": "2026-09-02T11:50:53.000Z",
                                "message": "0/206 nodes are unavailable: 2 node(s) didn't match Pod's node affinity/selector, 24 Insufficient mellanox.com/rdma_roce_share, 4 Insufficient cpu, 5 Insufficient memory, 5 node(s) were unschedulable, 70 plugin resourcepool predicates failed for task deepseek-v4-dp2tp4-0-0-1-roleset-qj54c-standalone-54b9d4-0-0 because the task doesn't satisfy exclusive node affinity, 96 Insufficient cambricon.com/mlu590.",
                                "reason": "FailedScheduling",
                                "source": "volcano",
                                "type": "Warning"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:42.000Z",
                                "lastTimestamp": "2026-09-02T11:51:42.000Z",
                                "message": "Add net3 [192.168.1.233/24] from ns-e23f5b20fb9b42d3ac674f9691a0b9b1/macvlan-net-c",
                                "reason": "AddedInterface",
                                "source": "multus",
                                "type": "Normal"
                            }
                        ],
                        "resource": {
                            "apiVersion": "v1",
                            "kind": "Pod",
                            "name": "deepseek-v4-dp2tp4-0-0-1-roleset-qj54c-standalone-54b9d4-0-0",
                            "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
                            "uid": "1d25869c-00e0-4205-aaf3-7471b72146e6"
                        },
                        "status": "Running"
                    },
                    "37546e46-044f-4a89-8766-d2c9617c62c1": {
                        "events": [
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:12.000Z",
                                "lastTimestamp": "2026-09-02T11:51:12.000Z",
                                "message": "Pulling image \"docker-user-bj-caip.cambricon.com:30443/cnagent/modelpackage/deepseekv4-flash:0.0.9-nydus\"",
                                "reason": "Pulling",
                                "source": "kubelet",
                                "type": "Normal"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:13.000Z",
                                "lastTimestamp": "2026-09-02T11:51:13.000Z",
                                "message": "Successfully pulled image \"docker-user-bj-caip.cambricon.com:30443/cnagent/modelpackage/deepseekv4-flash:0.0.9-nydus\" in 202ms (202ms including waiting). Image size: 20917009051 bytes.",
                                "reason": "Pulled",
                                "source": "kubelet",
                                "type": "Normal"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:13.000Z",
                                "lastTimestamp": "2026-09-02T11:51:13.000Z",
                                "message": "Started container deepseekv4-flash-0-0-9",
                                "reason": "Started",
                                "source": "kubelet",
                                "type": "Normal"
                            }
                        ],
                        "resource": {
                            "apiVersion": "v1",
                            "kind": "Pod",
                            "name": "deepseek-v4-dp2tp4-0-0-1-roleset-ngzgv-standalone-54b9d4-0-1",
                            "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
                            "uid": "37546e46-044f-4a89-8766-d2c9617c62c1"
                        },
                        "status": "Running"
                    },
                    "cf7b05f5-d76b-4741-acbc-ee36ec24fbf2": {
                        "events": [],
                        "resource": {
                            "apiVersion": "serving.cambricon.com/v1alpha1",
                            "kind": "LLMServing",
                            "name": "deepseek-v4-dp2tp4",
                            "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
                            "uid": "cf7b05f5-d76b-4741-acbc-ee36ec24fbf2"
                        },
                        "status": "Progressing"
                    },
                    "e04dace8-fde1-48e0-ad63-42097c7f3086": {
                        "events": [
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:11.000Z",
                                "lastTimestamp": "2026-09-02T11:51:11.000Z",
                                "message": "Created container: deepseekv4-flash-0-0-9",
                                "reason": "Created",
                                "source": "kubelet",
                                "type": "Normal"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:50:51.000Z",
                                "lastTimestamp": "2026-09-02T11:50:51.000Z",
                                "message": "AttachVolume.Attach succeeded for volume \"pvc-3487e201-80d8-4b0e-9b9c-16b8c4de11a4\" ",
                                "reason": "SuccessfulAttachVolume",
                                "source": "attachdetach-controller",
                                "type": "Normal"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:00.000Z",
                                "lastTimestamp": "2026-09-02T11:51:00.000Z",
                                "message": "Add eth0 [10.8.213.55/32]",
                                "reason": "AddedInterface",
                                "source": "multus",
                                "type": "Normal"
                            }
                        ],
                        "resource": {
                            "apiVersion": "v1",
                            "kind": "Pod",
                            "name": "deepseek-v4-dp2tp4-0-0-1-roleset-ngzgv-standalone-54b9d4-0-0",
                            "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
                            "uid": "e04dace8-fde1-48e0-ad63-42097c7f3086"
                        },
                        "status": "Running"
                    },
                    "f3916d9a-8b78-4466-8053-546db00a04c5": {
                        "events": [
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:30.000Z",
                                "lastTimestamp": "2026-09-02T11:51:30.000Z",
                                "message": "Successfully assigned ns-e23f5b20fb9b42d3ac674f9691a0b9b1/deepseek-v4-dp2tp4-0-0-1-roleset-qj54c-standalone-54b9d4-0-1 to cam-train-081",
                                "reason": "Scheduled",
                                "source": "volcano",
                                "type": "Normal"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:42.000Z",
                                "lastTimestamp": "2026-09-02T11:51:42.000Z",
                                "message": "Add net4 [192.168.1.69/24] from ns-e23f5b20fb9b42d3ac674f9691a0b9b1/macvlan-net-d",
                                "reason": "AddedInterface",
                                "source": "multus",
                                "type": "Normal"
                            },
                            {
                                "count": 1,
                                "firstTimestamp": "2026-09-02T11:51:42.000Z",
                                "lastTimestamp": "2026-09-02T11:51:42.000Z",
                                "message": "Pulling image \"docker-user-bj-caip.cambricon.com:30443/cnagent/modelpackage/deepseekv4-flash:0.0.9-nydus\"",
                                "reason": "Pulling",
                                "source": "kubelet",
                                "type": "Normal"
                            }
                        ],
                        "resource": {
                            "apiVersion": "v1",
                            "kind": "Pod",
                            "name": "deepseek-v4-dp2tp4-0-0-1-roleset-qj54c-standalone-54b9d4-0-1",
                            "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
                            "uid": "f3916d9a-8b78-4466-8053-546db00a04c5"
                        },
                        "status": "Running"
                    }
                }
            }
        ],
        "suspendedTimestamp": null,
        "url": "http://serving-cf7b05f5-d76b-4741-acbc-ee36ec24fbf2.serving.bj.caip.cambricon.com:30089",
        "versionStatus": [
            {
                "components": null,
                "name": "0.0.1",
                "roleSetStatus": [
                    {
                        "conditions": [
                            {
                                "lastTransitionTime": "0001-01-01T00:00:00.000Z",
                                "lastUpdateTime": "0001-01-01T00:00:00.000Z",
                                "reason": "roleset is ready",
                                "status": "True",
                                "type": "Ready"
                            }
                        ],
                        "roles": [
                            {
                                "name": "standalone",
                                "readyReplicas": 1,
                                "replicas": 1,
                                "updatedReadyReplicas": 1,
                                "updatedReplicas": 1
                            }
                        ]
                    },
                    {
                        "conditions": [
                            {
                                "lastTransitionTime": "0001-01-01T00:00:00.000Z",
                                "lastUpdateTime": "0001-01-01T00:00:00.000Z",
                                "reason": "roleset is ready",
                                "status": "True",
                                "type": "Ready"
                            }
                        ],
                        "roles": [
                            {
                                "name": "standalone",
                                "readyReplicas": 1,
                                "replicas": 1,
                                "updatedReadyReplicas": 1,
                                "updatedReplicas": 1
                            }
                        ]
                    }
                ],
                "status": {
                    "availableReplicas": 2,
                    "conditions": [
                        {
                            "lastTransitionTime": "2026-09-08T04:05:06.000Z",
                            "lastUpdateTime": "2026-09-08T04:05:06.000Z",
                            "reason": "Ready",
                            "status": "True",
                            "type": "Ready"
                        }
                    ],
                    "readyReplicas": 2,
                    "replicas": 2,
                    "updatedReplicas": 2
                }
            }
        ]
    }
}
```

该对象应该对应集群中的llmserving资源，后续可以结合50集群skill进行分析
