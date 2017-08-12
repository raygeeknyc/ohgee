#!/bin/bash
rc=0
echo "authenticating" >&2
credentials_file=`ls ../*.json | head -1`
GOOGLE_APPLICATION_CREDENTIALS=${credentials_file}
auth_file=`ls ../*auth*.py | head -1`
if [[ ! -r "${auth_file}" ]]; then
  echo "Cannot read auth.py file ${auth_file}" >&2
  rc=255
else
  rm -fr authinfo.py
  echo "copying authinfo.py from ${auth_file}" >&2
  ln ${auth_file} ./authinfo.py
fi
if [[ $rc -eq 0 ]]; then
  if [[ ! -r "${credentials_file}" ]]; then
    echo "falling back to interactive authentication" >&2
    gcloud auth application-default login
  else
    echo -n "GOOGLE_APPLICATION_CREDENTIALS=${credentials_file};"
    echo -n "export GOOGLE_APPLICATION_CREDENTIALS;"
    echo -n "export GOOGLE_CLOUD_PROJECT=ohgee-176600;"
  fi
  echo "authenticated" >&2
fi
echo "rc=${rc}"
