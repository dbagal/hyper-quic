# DiemBFT and Twins testing

## Team Name: CommuterBytes
#### Members:
- Dhaval Bagal
- Sanket Goutam


## Platform
We have implemented DiemBFT and Twins with the following resources.

- Python 3.7+
- Macbook / Unix variant system
- MacOS Catalina / Ubuntu 21.04

## Workload Generation for DiemBFT

DiemBFT can be configured using `config/config.json` file. 
Now run *spawn.py*. Depending on the configuration, appropriate number of replicas and clients are spawned.
Replicas progress upon receiving the first request from the client. 
All clients asynchronously broadcast requests to all the replicas


## Workload Generation for Twins

Twins generator can be configured using `config/twins_config.json`.
Depending on the settings specified in the configuration, appropriate testcases are generated.


## Timeouts

All the timeout values for different cases are defined as below. The values for liveness testing
and pacemaker round timeout is based on the Lemmas described in DiemBFT.

    transmission_time_delta = 0.5 secs
    pacemaker_round_timeout = 5*transmission_delta        (as defined in Section 4.3, DiemBFT)
    liveness_time_bound = 7*transmission_delta            (as defined by Property 4, DiemBFT)

## Bugs and Limitations

We have solved most of the bugs from our Phase 2 submission of DiemBFT
except the ones listed below.

### DiemBFT:

- Sync up implemented, but not working for some edge cases. Sync up is working correctly as evident from the logs, but there are minor bugs or edge cases which cause some issues. We didn't get enough time to analyse the logs and figure out the problems.

## Main Files

All code files related to DiemBFT are inside `src` folder

All code files related to Twins are placed inside `src/twins_testing` folder.
- Test Generator: `src/twins_testing/twins_generator.py`
- Test Executor: `src/twins_testing/twins_executor.py`
- Playground: `src/twins_testing/twins_playground.py`


## Code Size

The following are the LOC values of our codebase. We obtained these numbers using
[CLOC](https://github.com/AlDanial/cloc).

| Category                      | LOC         |
| :---                          |    :----:   |
| Diem Algorithm                |    1031     |
| Diem Other code               |    778      |
| Twins Generator               |    221      |
| Twins Executor                |    223      |
| Twins and Client Playground   |    207      |
| Total                         |    2629     |


## Language Feature Usage
Standard python libraries, dictionary constructs, lists, etc.
class inheritance, static functions, static variables, etc.
Python Multiprocessing, nested functions, hasattr, getattr, list comprehensions

## Contributions
- Dhaval Bagal: Implemented block-tree, safety, pacemaker, ledger, mempool, client, replica, spawnner, all playgrounds (faulty playground, twins-replica-playground, twins-client-playground), twins executor, twins generator, sync up mechanism 
 
- Sanket Goutam: Implemented all crypto checks. Drafted pseudocode for twins generator and executor. Completed all documentation, exploring DistAlgo implementation details, came up with multiple sync up mechanisms, rigorous testing using twins and generation of test reports 

## Other comments
Implemented `ds` package which consists of `Process` class.
This has syntax similar to that of DistAlgo. Basicall, wey built most of the required DistAlgo features from ground-up instead of using DistAlgo owing to the time constraint. 
All replicas and clients inherit the Process class and use its underlying functions for RELIABLE send, RELIABLE multicast and RELIABLE broadcast.