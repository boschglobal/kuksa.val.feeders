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
import transforms.mapping
import transforms.math
import logging
import sys
from typing import Any

log = logging.getLogger(__name__)


class VSSObservation:
    """A mapping for a VSS signal"""
    vss_name : str
    dbc_name : str
    value : Any

    def __init__(self, dbc_name : str, vss_name : str, value : Any):
        self.dbc_name = dbc_name
        self.vss_name = vss_name
        self.value = value
        
        

class VSSMapping:
    """A mapping for a VSS signal"""
    vss_name : str
    # transform may be None
    transform: dict
    
    interval_ms : int
    lastupdate_s : float = 0.0
    datatype: str
    description : str

    def __init__(self, vss_name : str, transform :dict, interval_ms : int, datatype: str, description : str):
        self.vss_name = vss_name
        self.transform = transform
        self.interval_ms = interval_ms
        self.datatype = datatype
        self.description = description
        
        
    # returns true if element can be updated
    def interval_exceeded(self, time : float):
        diff_ms =( time - self.lastupdate_s) * 1000.0
        print(f"For {self.vss_name} Comparing {type(diff_ms)} with {self.interval_ms} of type {type(self.interval_ms)}")
        if diff_ms >= self.interval_ms:
            self.lastupdate_s = time
            log.info(f"interval_exceeded for {self.vss_name}. Time is {time}")
            return True
        return False
        
class mapper:

    # Where we keep mapping, key is dbc signal name
    mapping : dict[str, list[VSSMapping]] = {}

    def verify_transform(self, expanded_name : str , node : dict):
        if not "transform" in node:
            log.debug(f"No transformation found for {expanded_name}")
            # For now assumed that None is Ok
            return None
        transform = node["transform"]
        print(f"Transform type {type(transform)}")
        return transform
        
    def analyze_signal(self,expanded_name, node):
        #print(f"About to handle {expanded_name}")
        if "dbc" in node:
          print(f"Signal {expanded_name} has dbc!")
          dbc_def = node["dbc"]
          # For now expect that only "signal" must exist
          # For now we do not check transform syntax here - should better be done
          transform = self.verify_transform(expanded_name, dbc_def)
          dbc_name = dbc_def.get("signal", "")
          if dbc_name == "":
            log.error(f"No dbc signal found for {expanded_name}")
            sys.exit(-1)
          if "interval_ms" in dbc_def:
              interval = dbc_def["interval_ms"]
              if not isinstance(interval,int):
                  log.error(f"Faulty interval for {expanded_name}")
                  sys.exit(-1)
          else:
              log.error(f"Using default interval 1000 ms for {expanded_name}")
              interval = 1000
          mapping_entry = VSSMapping(expanded_name, transform, interval,node["datatype"], node["description"])
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

        #json_string = json.dumps(jsonmapping) 
        #print(json_string)
        
        
        # Full mapping means that if there is no mapping we ignore it
        # Partial mapping means if no mapping found we use raw value
        # Still needed? If so we need to find out syntax.
        self.transforms = {}
        self.transforms["fullmapping"] = transforms.mapping.mapping(
            discard_non_matching_items=True
        )
        self.transforms["partialmapping"] = transforms.mapping.mapping(
            discard_non_matching_items=False
        )
        self.transforms["math"] = transforms.math.math()

        # Ambition, try to recreate the mapping to a big extent
        self.traverse_vss_node("",jsonmapping)

        print(f"Collected mapping {self.mapping}")

    def map(self):
        return self.mapping.items()


    # Check whether there are transforms defined to map DBC signal "signal" to
    # VSS path "target". Returns the (potentially) transformed values
    def transform(self, signal, target, value):
        if (
            "transform" not in self.mapping[signal]["targets"][target].keys()
        ):  # no transform defined, return as is
            return value
        for transform in self.mapping[signal]["targets"][target]["transform"]:
            if transform in self.transforms.keys():  # found a known transform and apply
                value = self.transforms[transform].transform(
                    self.mapping[signal]["targets"][target]["transform"][transform],
                    value,
                )
            else:
                log.warning(
                    f"Warning: Unknown transform {transform} for {signal}->{target}"
                )
        return value

    def __contains__(self, key):
        return key in self.mapping.keys()

    def __getitem__(self, item):
        return self.mapping[item]
    