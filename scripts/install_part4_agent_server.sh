#!/usr/bin/env bash

sudo apt update

sudo apt-get update
sudo apt-get install libevent-dev libzmq3-dev git make g++ --yes
sudo apt-get build-dep memcached --yes
git clone https://github.com/eth-easl/memcache-perf-dynamic.git
cd memcache-perf-dynamic || exit
make

echo "\nstart executing\n"

./mcperf -T 16 -A