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

"""
Classes for maintaining mapping between dbc and VSS
as well as transforming dbc data to VSS data.
"""

import json
import logging
import sys
from typing import Any
from dataclasses import dataclass

from py_expression_eval import Parser

log = logging.getLogger(__name__)

@dataclass
class VSSObservation:
    """
    A VSSObservation is a container for a single observation/data for a single VSS signal.
    The data contained is the raw data as received on CAN, it has not yet been transformed
    into VSS representation.
    """

    dbc_name : str
    vss_name : str
    raw_value : Any
    time : float


class VSSMapping:
    """A mapping for a VSS signal"""

    parser : Parser = Parser()

    def __init__(self, vss_name : str, transform :dict, interval_ms : int,
                 on_change : bool, datatype: str, description : str):
        self.vss_name = vss_name
        self.transform = transform
        self.interval_ms = interval_ms
        self.on_change = on_change
        self.datatype = datatype
        self.description = description
        self.lastupdate_s : float = 0.0
        # raw value (before transformation) stored for "on_change" condition evaluation.
        self.last_raw_value : Any = None

    def condition_fulfilled(self, time : float, value : Any) -> bool:
        """
        Checks if condition to send signal are fulfilled
        Currently and "and" condition, consisting of possibly both time and value condition
        """
        do_send = True

        if self.interval_ms > 0:
            diff_ms =( time - self.lastupdate_s) * 1000.0
            if diff_ms < self.interval_ms:
                log.debug(f"Interval not exceeded for {self.vss_name}. Time is {time}")
                do_send = False

        if (do_send and self.on_change):
            do_send = self.last_raw_value != value

        if (not do_send) and (self.last_raw_value is None):
            # Always send first time signal is seen
            do_send = True

        if do_send:
            self.lastupdate_s = time
            self.last_raw_value = value

        return do_send

    def transform_value(self, value : Any) -> Any:
        """
        Transforms the given "raw" value to the wanted VSS value.
        For now does not make any type checks
        """
        transformed_value = None
        if self.transform is None:
            log.debug(f"No mapping to VSS {self.vss_name}, using raw value {value}")
            transformed_value = value
        else:
            # It is supposed that "verify_transform" already have checked that
            # we have a valid transform, so no need to check it here
            if "mapping" in self.transform:
                tmp = self.transform["mapping"]
                # Assumed to be a list
                for item in tmp:
                    from_val = item["from"]
                    if from_val == value:
                        new_val = item["to"]
                        transformed_value = new_val
                        break
            else:
                tmp = self.transform["math"]
                try:
                    transformed_value = VSSMapping.parser.parse(tmp).evaluate({"x": value})
                except Exception:
                    # It is assumed that you may consider it ok that transformation fails sometimes,
                    # so giving warning instead of error
                    # This could be e.g. trying to treat a string as int
                    log.warning(f"Transformation failed for value {value} "
                                f"for VSS signal {self.vss_name}, signal ignored!", exc_info=True)

        if transformed_value is None:
            log.info(f"No mapping to VSS {self.vss_name} found for raw value {value},"
                     f"returning None to indicate that it shall be ignored!")
        else:
            log.info(f"New value {transformed_value} for {self.vss_name}")
        return transformed_value


class Mapper:
    """
    The mapper class contain all mappings between dbc and vss.
    It also contain functionality for transforming data
    """

    # Where we keep mapping, key is dbc signal name
    mapping : dict[str, list[VSSMapping]] = {}

    def transform_value(self, vss_observation : VSSObservation) -> Any:
        """
        Find mapping and transform value. Return None if no matching mapping found.
        """
        # If we have an observation we know that a mapping exists
        for vss_signal in self.mapping[vss_observation.dbc_name]:
            if vss_signal.vss_name == vss_observation.vss_name:
                value = vss_signal.transform_value(vss_observation.raw_value)
                log.debug(f"Transformed dbc {vss_observation.dbc_name} to VSS "
                          f"{vss_observation.vss_name}, "
                          f"from raw value {vss_observation.raw_value} to {value}")
                return value

        # Shall never be reached
        return None

    def verify_transform(self, expanded_name : str , node : dict):
        """
        Extracts transformation and checks it seems to be correct
        """
        if not "transform" in node:
            log.debug(f"No transformation found for {expanded_name}")
            # For now assumed that None is Ok
            return None
        transform = node["transform"]

        has_mapping = False

        if not isinstance(transform, dict):
            log.error(f"Transform not dict for {expanded_name}")
            sys.exit(-1)
        if "mapping" in transform:
            tmp = transform["mapping"]
            if not isinstance(tmp, list):
                log.error(f"Transform mapping not list for {expanded_name}")
                sys.exit(-1)
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

    def analyze_signal(self, expanded_name, node):
        """
        Analyzes a signal and add mapping entry if correct mapping found
        """
        if "dbc" in node:
            log.info(f"Signal {expanded_name} has dbc!")
            dbc_def = node["dbc"]
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
                    log.info(f"Using default interval 0 ms for {expanded_name} "
                             f"as it has on_change condition")
                    interval = 0
                else:
                    log.info(f"Using default interval 1000 ms for {expanded_name}")
                    interval = 1000
            mapping_entry = VSSMapping(expanded_name, transform, interval, on_change,
                                       node["datatype"], node["description"])
            if not dbc_name in self.mapping:
                self.mapping[dbc_name] = []
            self.mapping[dbc_name].append(mapping_entry)

    def traverse_vss_node(self,name, node, prefix = ""):
        """
        Traverse a vss node/tree and order all found VSS signals to be analyzed
        so that mapping can be extracted
        """
        is_signal = False
        is_branch = False
        expanded_name = ""
        if isinstance(node,dict):
            if "type" in node:
                if node["type"] in ["sensor","actuator", "attribute"]:
                    is_signal = True
                elif node["type"] in ["branch"]:
                    is_branch = True
                    prefix = prefix + name + "."

        # Assuming it to be a dict
        if is_branch:
            for item in node["children"].items():
                self.traverse_vss_node(item[0],item[1],prefix)
        elif is_signal:
            expanded_name = prefix + name
            self.analyze_signal(expanded_name, node)
        elif isinstance(node,dict):
            for item in node.items():
                self.traverse_vss_node(item[0],item[1],prefix)

    def get_vss_mapping(self, dbc_name : str, vss_name :str) -> VSSMapping:
        """
        Helper method for test purposes
        """
        if dbc_name in self.mapping:
            for mapping in self.mapping[dbc_name]:
                if mapping.vss_name == vss_name:
                    return mapping
        return None


    def __init__(self, filename):
        with open(filename, "r") as file:
            try:
                jsonmapping = json.load(file)
                log.info(f"Reading dbc configurations from {filename}")
            except Exception:
                log.error(f"Failed to read json from {filename}", exc_info=True)
                sys.exit(-1)

        self.traverse_vss_node("",jsonmapping)


    def map(self):
        """ Get access to the map items """
        return self.mapping.items()

    def __contains__(self, key):
        return key in self.mapping.keys()

    def __getitem__(self, item):
        return self.mapping[item]
    