#!/usr/bin/env bash

sudo apt update

sudo apt-get update
sudo apt-get install libevent-dev libzmq3-dev git make g++ --yes
sudo apt-get build-dep memcached --yes
git clone https://github.com/eth-easl/memcache-perf-dynamic.git
cd memcache-perf-dynamic || exit
make

./mcperf -s INTERNAL_MEMCACHED_IP --loadonly
./mcperf -s INTERNAL_MEMCACHED_IP -a INTERNAL_AGENT_IP \
--noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 1800 \
--qps_interval 5 --qps_min 5000 --qps_max 100000 \
--qps_seed 42
