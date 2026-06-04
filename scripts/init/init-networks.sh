#!/usr/bin/env bash

set -e

create_network() {
  local name="$1"
  local internal_flag="$2"

  if docker network inspect "$name" >/dev/null 2>&1; then
    echo "Network '$name' already exists — skipping"
  else
    echo "Creating network '$name'..."
    docker network create $internal_flag "$name"
  fi
}

create_network "proxy" ""
create_network "internal" "--internal"
create_network "monitoring" "--internal"

echo "Done."