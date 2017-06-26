#!/bin/bash
export GOOGLE_APPLICATION_CREDENTIALS=../paidtech-07060b047c89.json
if [[ ! -r "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
  gcloud auth application-default login
fi
