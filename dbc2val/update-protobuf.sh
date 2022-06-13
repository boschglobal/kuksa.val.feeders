#!/bin/bash
#********************************************************************************
# Copyright (c) 2022 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License 2.0 which is available at
# http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#*******************************************************************************/
# shellcheck disable=SC2086

GEN_DIR="./gen_proto"

[ -d "$GEN_DIR" ] || mkdir -p "$GEN_DIR"

DATABROKER_PROTO="../vehicle_data_broker/proto"

if [ ! -d "$DATABROKER_PROTO" ]; then
	echo "Warning! Can't find DataBroker proto dir in: $DATABROKER_PROTO"
	exit 1
fi

# make sure deps are installed
echo "# Installing requirements.txt ..."
pip3 install -q -r requirements-dev.txt
#pip3 install -q -r requirements.txt

set -xe
PROTO_FILES=$(find "$DATABROKER_PROTO" -name '*.proto')

echo "# Generating grpc stubs from: $DATABROKER_PROTO ..."
python3 -m grpc_tools.protoc \
	--python_out="$GEN_DIR" \
	--grpc_python_out="$GEN_DIR" \
	--proto_path="$DATABROKER_PROTO" \
	$PROTO_FILES
#  --mypy_out="$GEN_DIR"
set +x

echo "# Generated files:"
find "$GEN_DIR" -type f -name '*.py'

echo "# Replacing packages in $GEN_DIR"
find "$GEN_DIR" -type f -name '*.py' -print -exec sed -i 's/^from sdv.databroker.v1/from gen_proto.sdv.databroker.v1/g' {} ';'
find "$GEN_DIR" -type f -name '*.pyi' -print -exec sed -i 's/^import sdv.databroker.v1/import gen_proto.sdv.databroker.v1/g' {} ';'
