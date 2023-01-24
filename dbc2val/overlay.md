# Use of overlay notes

* Using json


```
./vss-tools/vspec2json.py -e dbc --json-pretty --no-uuid -I ./spec ./spec/VehicleSignalSpecification.vspec -o overlay.vspec dbc.json
```


                          "transform": {
                            "mapping": [
                              {
                                "from": 0,
                                "to": false
                              },
                              {
                                "from": 1,
                                "to": true
                              }
                            ]
                          }
