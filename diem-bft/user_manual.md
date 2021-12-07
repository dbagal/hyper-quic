# User Manual for executing DiemBFT and Twins

Source code                 : `src/`
Config (Diem and Twins)     : `config/`
Logs                        : `logs/`
Block Tree logs             : `logs/block-trees/`
Ledgers                     : `ledger/`
Twins logs                  : `logs/twins/`
Twins generator test cases  : `src/twins_testing/test_cases.json`

## Configuration

Configure the required parameters in `config/config.json` for diembft and `config/twins_config.json` for twins generator

## Running DiemBFT
```
python3 spawn.py
```

## Running Twins

Generate test cases using 
```
python twins_generator.py
```

Run executor to run random n testcases from the generated testcases.
```
python twins_executor.py
```
