#!/usr/bin/env bash

sudo apt update

sudo apt install -y memcached libmemcached-tools
sudo systemctl status memcached
sudo vim /etc/memcached.conf
sudo systemctl restart memcached

sudo apt install -y python3 python3-pip memcached libmemcached-tools

#sudo groupadd docker
#sudo usermod -aG docker $USER
#newgrp docker

docker pull anakli/parsec:dedup-native-reduced
docker pull anakli/parsec:splash2x-fft-native-reduced
docker pull anakli/parsec:blackscholes-native-reduced
docker pull anakli/parsec:canneal-native-reduced
docker pull anakli/parsec:freqmine-native-reduced
docker pull anakli/parsec:ferret-native-reduced

pip3 install psutil docker

echo ""
echo "Now copy the scheduler files to the server and run them."
echo ""
