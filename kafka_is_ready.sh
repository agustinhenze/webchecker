#!/bin/bash

KAFKA_INSTANCES_NUMBER=$(kafka-broker-api-versions --bootstrap-server localhost:9092 | grep '^kafka' | wc -l 2> /dev/null)

while [ ${KAFKA_INSTANCES_NUMBER} -lt 3 ]; do
  KAFKA_INSTANCES_NUMBER=$(kafka-broker-api-versions --bootstrap-server localhost:9092 | grep '^kafka' | wc -l 2> /dev/null)
  sleep 5s
done
