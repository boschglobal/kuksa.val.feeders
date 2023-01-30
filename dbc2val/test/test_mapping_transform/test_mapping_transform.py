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

# The intention of file is to test parsing and transformation for various constructs


from dbcfeederlib import dbc2vssmapper
import os

# read config only once
path = os.path.dirname(os.path.abspath(__file__)) + "/test.json"
mapper : dbc2vssmapper.Mapper = dbc2vssmapper.Mapper(path)

def test_mapping_read():
    dbc_mapping = mapper["S1"]
    # We have 6 VSS signals using S1
    assert len(dbc_mapping) == 6

def test_no_transform_default():
    mapping =  mapper.get_vss_mapping("S1","A.NoTransformDefault")
    assert mapping != None
    assert mapping.interval_ms == 1000
    assert mapping.on_change == False
    # 1000 ms limit default, should not care about values
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 23) == True
    assert mapping.condition_fulfilled(0.02, 23) == False
    assert mapping.condition_fulfilled(1.00, 23) == False
    assert mapping.condition_fulfilled(1.02, 23) == True
    assert mapping.condition_fulfilled(1.50, 23) == False
    assert mapping.condition_fulfilled(2.03, 23) == True
    
    assert mapping.transform_value(23.2) == 23.2

def test_no_transform_interval_500():
    mapping =  mapper.get_vss_mapping("S1","A.NoTransformInterval500")
    assert mapping != None
    assert mapping.interval_ms == 500
    assert mapping.on_change == False
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 23) == True
    assert mapping.condition_fulfilled(0.02, 23) == False
    assert mapping.condition_fulfilled(0.50, 23) == False
    assert mapping.condition_fulfilled(0.52, 23) == True
    assert mapping.condition_fulfilled(1.00, 23) == False
    assert mapping.condition_fulfilled(1.03, 23) == True
    
    assert mapping.transform_value(23.2) == 23.2
    
    
def test_no_transform_on_change_true():
    mapping =  mapper.get_vss_mapping("S1","A.NoTransformOnChangeTrue")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 23) == True
    assert mapping.condition_fulfilled(45.0, 23) == False
    assert mapping.condition_fulfilled(45.0, 46) == True
    assert mapping.condition_fulfilled(48.0, 46) == False
    assert mapping.condition_fulfilled(49.0, 50) == True
    
    assert mapping.transform_value(23.2) == 23.2

def test_no_transform_on_change_false():
    # Should be same as test_no_transform_default
    mapping =  mapper.get_vss_mapping("S1","A.NoTransformOnChangeFalse")
    assert mapping != None
    assert mapping.interval_ms == 1000
    assert mapping.on_change == False
    # 1000 ms limit default, should not care about values
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 23) == True
    assert mapping.condition_fulfilled(0.02, 23) == False
    assert mapping.condition_fulfilled(1.00, 23) == False
    assert mapping.condition_fulfilled(1.02, 23) == True
    assert mapping.condition_fulfilled(1.50, 23) == False
    assert mapping.condition_fulfilled(2.03, 23) == True
    
    assert mapping.transform_value(23.2) == 23.2

    
def test_no_transform_on_change_interval_500():
    # Should be same as test_no_transform_default
    mapping =  mapper.get_vss_mapping("S1","A.NoTransformOnChangeInterval500")
    assert mapping != None
    assert mapping.interval_ms == 500
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 23) == True
    assert mapping.condition_fulfilled(0.02, 23) == False
    # Not sent as condition not fulfilled, reference time kept
    assert mapping.condition_fulfilled(1.00, 23) == False
    assert mapping.condition_fulfilled(1.02, 46) == True
    
    assert mapping.transform_value(23.2) == 23.2

def test_no_transform_always():
    mapping =  mapper.get_vss_mapping("S1","A.NoTransformAlways")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == False
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 23) == True
    assert mapping.condition_fulfilled(0.02, 23) == True
    assert mapping.condition_fulfilled(1.00, 23) == True
    assert mapping.condition_fulfilled(1.02, 23) == True
    assert mapping.condition_fulfilled(1.50, 23) == True
    assert mapping.condition_fulfilled(2.03, 23) == True
    
    assert mapping.transform_value(23.2) == 23.2


def test_mapping_math():
    mapping =  mapper.get_vss_mapping("S2","A.Math")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 26) == True
    assert mapping.transform_value(26) == 5
    assert mapping.condition_fulfilled(0.02, 26) == False
    # As +26 and -26 are different raw values they are considered
    # different, even if they are transformed to the same value
    assert mapping.condition_fulfilled(0.03, -26) == True
    assert mapping.transform_value(-26) == 5
    
    # Error handling - value not supported
    # It is a different raw value, so initial condition is fulfilled
    assert mapping.condition_fulfilled(0.05, "Sebastian") == True
    # But shall result in None, so not being sent
    assert mapping.transform_value("Sebastian") == None
    
    # But that means also that if -26 is received again it is considered as a new value
    assert mapping.condition_fulfilled(0.06, -26) == True
    assert mapping.transform_value(-26) == 5


def test_mapping_string_int():
    mapping =  mapper.get_vss_mapping("S3","A.MappingStringInt")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, "DI_GEAR_P") == True
    assert mapping.transform_value("DI_GEAR_P") == 0
    assert mapping.condition_fulfilled(0.02, "DI_GEAR_P") == False
    # As "DI_GEAR_P" and "DI_GEAR_INVALID" are different raw values they are considered
    # different, even if they are transformed to the same value
    assert mapping.condition_fulfilled(0.03, "DI_GEAR_INVALID") == True
    assert mapping.transform_value("DI_GEAR_INVALID") == 0
    assert mapping.condition_fulfilled(0.04, "DI_GEAR_R") == True
    assert mapping.transform_value("DI_GEAR_R") == -1
    
    # Error handling - value not supported
    # It is a different raw value, so initial condition is fulfilled
    assert mapping.condition_fulfilled(0.05, "Sebastian") == True
    # But shall result in None, so not being sent
    assert mapping.transform_value("Sebastian") == None
    
    # But that means also that if "DI_GEAR_R" is received again it is considered as a new value
    assert mapping.condition_fulfilled(0.06, "DI_GEAR_R") == True
    assert mapping.transform_value("DI_GEAR_R") == -1


def test_mapping_string_string():
    mapping =  mapper.get_vss_mapping("S4","A.MappingStringString")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, "schwarz") == True
    assert mapping.transform_value("schwarz") == "black"
    assert mapping.condition_fulfilled(0.02, "schwarz") == False
    assert mapping.condition_fulfilled(0.04, "weiss") == True
    assert mapping.transform_value("weiss") == "white"
    
    # Error handling - value not supported
    # It is a different raw value, so initial condition is fulfilled
    assert mapping.condition_fulfilled(0.05, "blau") == True
    # But shall result in None, so not being sent
    assert mapping.transform_value("blau") == None
    
    # But that means also that if "weiss" is received again it is considered as a new value
    assert mapping.condition_fulfilled(0.06, "weiss") == True
    assert mapping.transform_value("weiss") == "white"


def test_mapping_int_int():
    mapping =  mapper.get_vss_mapping("S5","A.MappingIntInt")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 3) == True
    assert mapping.transform_value(3) == 7
    assert mapping.condition_fulfilled(0.02, 3) == False
    assert mapping.condition_fulfilled(0.04, 4) == True
    assert mapping.transform_value(4) == 4
    
    # Error handling - value not supported
    # It is a different raw value, so initial condition is fulfilled
    assert mapping.condition_fulfilled(0.05, 6) == True
    # But shall result in None, so not being sent
    assert mapping.transform_value(6) == None
    
    # But that means also that if 4 is received again it is considered as a new value
    assert mapping.condition_fulfilled(0.06, 4) == True
    assert mapping.transform_value(4) == 4

def test_mapping_int_duplicate():
    mapping =  mapper.get_vss_mapping("S5","A.MappingIntIntDuplicate")
    assert mapping != None
    assert mapping.interval_ms == 0
    assert mapping.on_change == True
    # First shall always be sent
    assert mapping.condition_fulfilled(0.01, 3) == True
    # For duplicated mappings we do not state which one that will be used, both are OK
    assert (mapping.transform_value(3) == 7) or (mapping.transform_value(3) == 8)
    assert mapping.condition_fulfilled(0.02, 3) == False
    assert mapping.condition_fulfilled(0.04, 4) == True
    assert mapping.transform_value(4) == 4
    
    # Error handling - value not supported
    # It is a different raw value, so initial condition is fulfilled
    assert mapping.condition_fulfilled(0.05, 6) == True
    # But shall result in None, so not being sent
    assert mapping.transform_value(6) == None
    
    # But that means also that if 4 is received again it is considered as a new value
    assert mapping.condition_fulfilled(0.06, 4) == True
    assert mapping.transform_value(4) == 4
    