#!/bin/bash
rc=0
echo "authenticating" >&2
credentials_file=`ls ../*.json | head -1`
GOOGLE_APPLICATION_CREDENTIALS=${credentials_file}
if [[ ! -r "${credentials_file}" ]]; then
  echo "falling back to interactive authentication" >&2
  gcloud auth application-default login
else
  echo -n "GOOGLE_APPLICATION_CREDENTIALS=${credentials_file};"
  echo -n "export GOOGLE_APPLICATION_CREDENTIALS;"
  echo -n "export GOOGLE_CLOUD_PROJECT=ohgee-176600;"
fi
echo "authenticated" >&2
echo "rc=${rc}"
