#!/usr/bin/python3

########################################################################
# Copyright (c) 2020 Robert Bosch GmbH
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


#import yaml
import json 
import logging
import sys
from typing import Any
from py_expression_eval import Parser

log = logging.getLogger(__name__)


class VSSObservation:
    """A mapping for a VSS signal"""

    def __init__(self, dbc_name : str, vss_name : str, value : Any, time : float):
        self.dbc_name = dbc_name
        self.vss_name = vss_name
        self.value = value
        self.time = time
        

class VSSMapping:

    parser : Parser = Parser()

    def __init__(self, vss_name : str, transform :dict, interval_ms : int, on_change : bool, datatype: str, description : str):
        self.vss_name = vss_name
        self.transform = transform
        self.interval_ms = interval_ms
        self.on_change = on_change
        self.datatype = datatype
        self.description = description
        self.lastupdate_s : float = 0.0
        # Value stored only for logging purposes
        self.last_value : Any = None
        
    # returns true if element can be updated
    def interval_exceeded(self, time : float):
        diff_ms =( time - self.lastupdate_s) * 1000.0
        #print(f"For {self.vss_name} Comparing {type(diff_ms)} with {self.interval_ms} of type {type(self.interval_ms)}")
        if diff_ms >= self.interval_ms:
            # Interval updated first if value actually can be transformed and change condition considered
            #self.lastupdate_s = time
            log.debug(f"interval_exceeded for {self.vss_name}. Time is {time}")
            return True
        return False
        
    # Check whether there are transforms defined to map DBC signal "signal" to
    # VSS path "target". Returns the (potentially) transformed values
    # For now assumed that both value and transformed value can be of any type
    # e.g. string, int, float, bool
    # (That shall better be tested/investigated later - what types can value actually have?)
    def transform_value(self, value : Any, time : float) -> Any:
    
        if self.transform == None:
            log.debug(f"No mapping to VSS {self.vss_name}, using raw value {value}")
            transformed_value = value
        else:
            #print(f"Transform of type {type(self.transform)}")
            # It is supposed that "verify_transform" already have checked that we have a valid transform, so no need to check it here
            if "mapping" in self.transform:
                tmp = self.transform["mapping"]
                #print(f"Found mapping {tmp} of type {type(tmp)}")
                # Assumed to be a list
                for item in tmp:
                    from_val = item["from"]
                    #print(f"Comparing {from_val} with {value}")
                    if from_val == value:
                         #print(f"Match")
                         new_val = item["to"]
                         transformed_value = new_val
                         break
            else:
                tmp = self.transform["math"]
                #print(f"Found math {tmp} of type {type(tmp)}")
                transformed_value = VSSMapping.parser.parse(tmp).evaluate({"x": value})
                #print(f"Transformed to {transformed_value} of type {type(transformed_value)}")

        if transformed_value == None:
            log.info(f"No mapping to VSS {self.vss_name} found for raw value {value}, returning None to indicate that it shall be ignored!")
        else:
            if self.on_change and (value == self.last_value):
                return None
            self.lastupdate_s = time
            if transformed_value != self.last_value:
                log.info(f"New value {value} for {self.vss_name}")
                self.last_value = transformed_value
        return transformed_value
        
        
class mapper:

    # Where we keep mapping, key is dbc signal name
    mapping : dict[str, list[VSSMapping]] = {}

    def verify_transform(self, expanded_name : str , node : dict):
        if not "transform" in node:
            log.debug(f"No transformation found for {expanded_name}")
            # For now assumed that None is Ok
            return None
        transform = node["transform"]
        #print(f"Transform type {type(transform)}")
        
        has_mapping = False
        
        if not isinstance(transform, dict):
            log.error(f"Transform not dict for {expanded_name}")
            sys.exit(-1)
        if "mapping" in transform:
            tmp = transform["mapping"]
            if not isinstance(tmp, list):
                log.error(f"Transform mapping not list for {expanded_name}")
                sys.exit(-1)
            #print(f"Found mapping {tmp} of type {type(tmp)}")
            for item in tmp:
                if not (("from" in item) and ("to" in item)):
                    log.error(f"Mapping missing to and from in {item} for {expanded_name}")
                    sys.exit(-1)
            has_mapping = True
            
        if "math" in transform:
            if has_mapping:
                log.error(f"Can not have both mapping and math for {expanded_name}")
                sys.exit(-1)
            if not isinstance(transform["math"], str):
                log.error(f"Math must be str for {expanded_name}")
                sys.exit(-1)
        return transform
        
    def analyze_signal(self,expanded_name, node):
        #print(f"About to handle {expanded_name}")
        if "dbc" in node:
          log.info(f"Signal {expanded_name} has dbc!")
          dbc_def = node["dbc"]
          # For now expect that only "signal" must exist
          # For now we do not check transform syntax here - should better be done
          transform = self.verify_transform(expanded_name, dbc_def)
          dbc_name = dbc_def.get("signal", "")
          if dbc_name == "":
            log.error(f"No dbc signal found for {expanded_name}")
            sys.exit(-1)
          on_change : bool = False
          if "on_change" in dbc_def:
             tmp = dbc_def["on_change"]
             if isinstance(tmp,bool):
                 on_change = tmp
             else:
                  log.error(f"Value for on_change ({tmp}) is not bool")
                  sys.exit(-1)
          if "interval_ms" in dbc_def:
              interval = dbc_def["interval_ms"]
              if not isinstance(interval,int):
                  log.error(f"Faulty interval for {expanded_name}")
                  sys.exit(-1)
          else:
              if on_change:
                  log.info(f"Using default interval 0 ms for {expanded_name} as it has on_change condition")
                  interval = 0
              else:
                  log.info(f"Using default interval 1000 ms for {expanded_name}")
                  interval = 1000
          mapping_entry = VSSMapping(expanded_name, transform, interval, on_change, node["datatype"], node["description"])
          if not dbc_name in self.mapping:
              self.mapping[dbc_name] = []
          self.mapping[dbc_name].append(mapping_entry)
    
    def traverse_vss_node(self,name, node,prefix = ""):
        #print(f"Working with node of type {type(node)}")
        
        # Identify if it is a VSS node
        is_signal = False
        is_branch = False
        expanded_name = ""
        if isinstance(node,dict):
           if "type" in node:
               if node["type"] in ["sensor","actuator", "attribute"]:
                   node_type = node["type"];
                   #print(f"Found VSS node {name} of type {node_type}")
                   is_signal = True
               elif node["type"] in ["branch"]:
                   node_type = node["type"];
                   #print(f"Found VSS node  {name}  of type {node_type}")
                   is_branch = True
                   prefix = prefix + name + "."
                   
        #            
        # Assuming it to be a dict
        if is_branch:      
            for item in node["children"].items():
                self.traverse_vss_node(item[0],item[1],prefix)
        elif is_signal:
            #print(f"Signal, so not iterating more")
            expanded_name = prefix + name
            self.analyze_signal(expanded_name, node)
        elif isinstance(node,dict):    
            for item in node.items():
                self.traverse_vss_node(item[0],item[1],prefix)
        #else:
            #print(f"Was something else {node}")

    def __init__(self, input):
        with open(input, "r") as file:
            #self.mapping = yaml.full_load(file)
            jsonmapping = json.load(file)

        # Ambition, try to recreate the mapping to a big extent
        self.traverse_vss_node("",jsonmapping)

        #print(f"Collected mapping {self.mapping}")

    def map(self):
        return self.mapping.items()

    def __contains__(self, key):
        return key in self.mapping.keys()

    def __getitem__(self, item):
        return self.mapping[item]
    