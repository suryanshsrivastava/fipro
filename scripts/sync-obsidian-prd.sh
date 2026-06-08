#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${REPO_ROOT}/docs/PRD.md"
VAULT_DIR="${HOME}/Documents/Notes/holistic/pages/projects/fipro-docs"
TARGET="${VAULT_DIR}/PRD.md"

if [[ ! -f "${SOURCE}" ]]; then
  echo "Missing canonical PRD: ${SOURCE}" >&2
  exit 1
fi

mkdir -p "${VAULT_DIR}"

if [[ -L "${TARGET}" ]]; then
  current="$(readlink "${TARGET}")"
  if [[ "${current}" == "${SOURCE}" ]]; then
    echo "Obsidian PRD already linked to repo: ${TARGET} -> ${SOURCE}"
    exit 0
  fi
  rm "${TARGET}"
elif [[ -f "${TARGET}" ]]; then
  backup="${TARGET}.bak.$(date +%Y%m%d%H%M%S)"
  mv "${TARGET}" "${backup}"
  echo "Backed up vault copy to ${backup}"
fi

ln -s "${SOURCE}" "${TARGET}"
echo "Linked ${TARGET} -> ${SOURCE}"
