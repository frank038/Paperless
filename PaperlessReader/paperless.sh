#!/bin/bash
thisdir=$(dirname "$0")
cd $thisdir

python3 Paperless.py "$@" &
