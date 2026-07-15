#!/usr/bin/env bash

set -e
set -x

: "${POSTGRES_DB:=}"
case "${POSTGRES_DB}" in
  *_test|*_pytest)
    ;;
  *)
    echo "Refusing to run backend tests against POSTGRES_DB='${POSTGRES_DB}'." >&2
    echo "Set POSTGRES_DB to an isolated test database ending with _test or _pytest." >&2
    exit 2
    ;;
esac

coverage run -m pytest tests/
coverage report
coverage html --title "${@-coverage}"
