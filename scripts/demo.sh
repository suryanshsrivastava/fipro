#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/fipro-demo-XXXXXX")"
INPUT_DIR="$WORKDIR/input"
OUTPUT_DIR="$WORKDIR/output"
PROCESSED_DIR="$WORKDIR/processed"
FAILED_DIR="$WORKDIR/failed"
STATE_DIR="$WORKDIR/state"
CONFIG_PATH="$WORKDIR/config.toml"
FIXTURE_DIR="$ROOT/tests/fixtures/extraction/raw_monthly_exports_2025_08_27/input"

mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$PROCESSED_DIR" "$FAILED_DIR" "$STATE_DIR"
cp "$FIXTURE_DIR"/* "$INPUT_DIR"/

cat > "$CONFIG_PATH" <<EOF
[fipro]
version = "0.1.0"
log_level = "INFO"

[paths]
input = "$INPUT_DIR"
output = "$OUTPUT_DIR"
processed = "$PROCESSED_DIR"
failed = "$FAILED_DIR"
dashboard_data = "$OUTPUT_DIR/dashboard_data.csv"

[processing]
supported_extensions = ["xls", "xlsx"]
skip_internal_transfers = false
seen_hashes_path = "$STATE_DIR/.seen_hashes"

[banks.hdfc]
name = "HDFC"
patterns = ["*hdfc*", "*HDFC*"]
date_format = "%d/%m/%y"

[banks.sbi]
name = "SBI"
patterns = ["*sbi*", "*SBI*"]
date_format = "%d %b %Y"

[banks.axis]
name = "AXIS"
patterns = ["*axis*", "*Axis*"]
date_format = "%d-%m-%Y"

[export.goodbudget]
default_envelope = "Unallocated"
default_status = "cleared"
max_description_length = 50

[external_accounts]
names = ["CREDIT_CARD"]
payment_keywords = ["CREDIT CARD", "CC PAYMENT", "CARD PAYMENT", "CRED"]
EOF

cd "$ROOT"
uv run fipro --config "$CONFIG_PATH" status
printf '\n'
uv run fipro --config "$CONFIG_PATH" process
printf '\nDemo workspace: %s\n' "$WORKDIR"
printf 'Goodbudget CSV: %s\n' "$OUTPUT_DIR/goodbudget_export.csv"
printf 'Dashboard CSV:  %s\n' "$OUTPUT_DIR/dashboard_data.csv"
printf 'Report JSON:    %s\n' "$OUTPUT_DIR/processing_report.json"
printf '\nLaunch dashboard with:\n'
printf '  uv run fipro --config %q dashboard --csv %q --port 8080 --open\n' "$CONFIG_PATH" "$OUTPUT_DIR/dashboard_data.csv"
