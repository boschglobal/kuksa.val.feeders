# Use of overlay notes

Generate a json file with annotations - like this if using VSS github repo

(We could possibly do it from Yaml as well)


```
./vss-tools/vspec2json.py -e dbc --json-pretty --no-uuid -I ./spec ./spec/VehicleSignalSpecification.vspec -o overlay.vspec dbc.json
```


Supported scope visible in examples in [overlay.vspec](overlay.vspec)

## Remaining work and Open Points

* What is our ambition with the default config? Would it be reasonable to change update interval to something slower to be able to follow printouts
* What is our logging ambition
* Instance support (depending on vss-tools)
* Check of dbc-config when reading to give errors then instead of later
* Testing - we need some converter unit tests, should be achievable
* Coding styles and other things ...

