#!/usr/bin/env bash

gsutil mb $KOPS_STATE_STORE

PROJECT='gcloud config get-value project'
export KOPS_FEATURE_FLAGS=AlphaAllowGCE # to unlock the GCE features
kops create -f project_yaml_files/part4.yaml

kops update cluster --name part4.k8s.local --yes --admin
kops validate cluster --wait 10m

kubectl get nodes -o wide


gcloud compute scp --scp-flag=-r src/controller_final ubuntu@memcache-server-m10r:/home/ubuntu/ --zone europe-west3-a

gcloud compute scp --scp-flag=-r scripts/ ubuntu@memcache-server-m10r:/home/ubuntu/ --zone europe-west3-a
gcloud compute scp --scp-flag=-r scripts/ ubuntu@client-agent-v0mv:/home/ubuntu/ --zone europe-west3-a
gcloud compute scp --scp-flag=-r scripts/ ubuntu@client-measure-v376:/home/ubuntu/ --zone europe-west3-a
