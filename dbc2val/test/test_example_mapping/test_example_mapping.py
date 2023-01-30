#!/usr/bin/python3

########################################################################
# Copyright (c) 2023 Robert Bosch GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
########################################################################



from dbcfeederlib import dbc2vssmapper
import os

# read config only once
path = os.path.dirname(os.path.abspath(__file__)) + "/../../vss_dbc.json"
mapper : dbc2vssmapper.Mapper = dbc2vssmapper.Mapper(path)

def test_current_gear():
    dbc_mapping = mapper["DI_gear"]
    assert len(dbc_mapping) == 1
    vss_mapping = dbc_mapping[0]
    assert vss_mapping.vss_name == "Vehicle.Powertrain.Transmission.CurrentGear"
    assert isinstance(vss_mapping.transform,dict)
    assert "mapping" in vss_mapping.transform
    mapping_list = vss_mapping.transform["mapping"]
    assert len(mapping_list) == 4
    # And now just check some items
    assert mapping_list[0]["from"] == "DI_GEAR_D"
    assert mapping_list[0]["to"] == 1
    assert mapping_list[1]["from"] == "DI_GEAR_P"
    assert mapping_list[1]["to"] == 0


    # Now test some transforms
    result = vss_mapping.transform_value("DI_GEAR_D")
    assert result == 1
    result = vss_mapping.transform_value("DI_GEAR_R")
    assert result == -1
    
    # For non successful mapping old value shall be kept and None returned
    result = vss_mapping.transform_value("Something undefined")
    assert result == None
    
def test_vehicle_speed():
    dbc_mapping = mapper["DI_uiSpeed"]
    assert len(dbc_mapping) == 1
    vss_mapping = dbc_mapping[0]
    assert vss_mapping.vss_name == "Vehicle.Speed"
    assert vss_mapping.transform == None
    
    # Now test some transforms
    result = vss_mapping.transform_value(25.3)
    assert result == 25.3
    