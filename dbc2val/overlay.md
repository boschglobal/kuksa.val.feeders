# Use of overlay notes

Generate a json file with annotations - like below if using VSS github repo



```
./vss-tools/vspec2json.py -e dbc --json-pretty --no-uuid -I ./spec ./spec/VehicleSignalSpecification.vspec -o overlay.vspec vss_dbc.json
```

(We could possibly do it from Yaml as well)

Supported scope visible in examples in [overlay.vspec](overlay.vspec)

# Design decisons

* By default log warnings only, info only minimal (like one line per signal sent)
* On info level log short information on every signal sent to kuksa.val
* Keep config file large/complete with short intervals
* Add on_change functionality

## Remaining work and Open Points

* Instance support (depending on vss-tools)
* Coding styles and other things ...
   * Logging debug and f-strings (Use lazy % formatting in logging functions?)

