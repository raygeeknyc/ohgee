#!/bin/bash
credentials_file=`ls ../*.json | head -1`
GOOGLE_APPLICATION_CREDENTIALS=${credentials_file}
if [[ ! -r "${credentials_file}" ]]; then
  echo "falling back to interactive authentication" >&2
  gcloud auth application-default login
else
  export GOOGLE_APPLICATION_CREDENTIALS=${credentials_file}
  export GOOGLE_CLOUD_PROJECT=ohgee-176600
fi
