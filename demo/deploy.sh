#!/bin/bash
docker build ../ -f Dockerfile -t datasette-comments
fly deploy --image datasette-comments --local-only
