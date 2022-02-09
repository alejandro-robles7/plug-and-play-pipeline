#!/bin/bash
docker run -p 8080:8080 -v output:/mnt/ml/model iris-model serve
