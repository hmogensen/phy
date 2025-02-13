## INSTALLATION

To install this version of the project, do the following (optionally after creating a new conda environment)

```bash
git clone git@github.com:hmogensen/phy.git
cd phy
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
cd ..
git clone git@github.com:hmogensen/phylib.git
cd phylib
pip install -e . --upgrade
```

## COMMANDS

Load customized files from sc-sort
```
phy template-gui params.py --load-graph
```

Show trigger view (only displays if there are triggers in data set)
```
phy template-gui params.py --load-triggers
```

## TROUBLESHOOTING

Clear cache
```
phy template-gui params.py --clear-cache
```

Clear previous widgets and windows settings
```
phy template-gui params.py --clear-state
```

Print debug log
```
phy template-gui params.py --debug
```

Feel free to report bugs or suggest features [here](https://github.com/Neural-basis-of-sensorimotor-control/spike_sorting_hlt/issues)