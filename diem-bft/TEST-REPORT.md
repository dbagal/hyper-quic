
## 1. Changing quorum size to f instead of 2f+1

Test for Safety violation in DiemBFT

**Changes to DiemBFT:**
```
config.json
------------
FROM

"system": {
    "quorum_size":3
}

TO

"system": {
    "quorum_size":1
}
```

**Test case considered:** *test-case-0*

**Executor log:**

```
2021-11-28 17:44:11,330 : 11-28-2021::17:44:11.330493
################################################################################            
                               TEST-CASE 0             
################################################################################

2021-11-28 17:44:22,824 : 11-28-2021::17:44:22.824207
Liveness verification (
	--------------------
	 cmd: XF5V0BB8EK
	 ts: 11-28-2021::17:44:14.404706
	 response: eb06d665f9a7ce5ed3904e09801b55435095998226d8bf767349fe4bd7b7cba4
	 response-ts: 11-28-2021::17:44:14.970411
	 response-time: 0.565705 secs
	 liveness-maintained: True
	--------------------
)

2021-11-28 17:44:22,824 : 11-28-2021::17:44:22.824776
Liveness verification (
	--------------------
	 cmd: U71KJKNSNX
	 ts: 11-28-2021::17:44:14.487013
	 response: d61b11c9d661bfdead6d60e502b31f6c60aa44cd1b9519d60ae12231d8b8a1ba
	 response-ts: 11-28-2021::17:44:16.075571
	 response-time: 1.588558 secs
	 liveness-maintained: True
	--------------------
)

2021-11-28 17:44:22,825 : 11-28-2021::17:44:22.825151
Liveness verification (
	--------------------
	 cmd: 64QXUXOO3V
	 ts: 11-28-2021::17:44:14.486587
	 response: d61b11c9d661bfdead6d60e502b31f6c60aa44cd1b9519d60ae12231d8b8a1ba
	 response-ts: 11-28-2021::17:44:16.192774
	 response-time: 1.706187 secs
	 liveness-maintained: True
	--------------------
)

2021-11-28 17:44:22,825 : 11-28-2021::17:44:22.825505
Liveness verification (
	--------------------
	 cmd: L4204XH0TW
	 ts: 11-28-2021::17:44:14.681829
	 response: 5e93ea02d7a959bc0eab30173b67400cad1aa3c47612caf7ac8d3f4b38349323
	 response-ts: 11-28-2021::17:44:22.789949
	 response-time: 8.10812 secs
	 liveness-maintained: False
	--------------------
)

2021-11-28 17:44:22,827 : 11-28-2021::17:44:22.827248
Safety verification (
	num-consistent-ledgers: 2, 
	is-safe: False
)
```

## 2. Accepting conflicting votes

Test for Safety violation in DiemBFT

**Changes to DiemBFT**

```
safety.py
---------

FROM 

def safe_to_vote(block_round, qc_round, tc):
    if block_round <= max(Safety.highest_vote_round, qc_round):
        return False
    ...

TO

def safe_to_vote(block_round, qc_round, tc):
    if block_round < max(Safety.highest_vote_round, qc_round):
        return False
    ...
```

**Test case considered:** *test-case-0*

**Executor log:**

```
2021-11-28 17:44:11,330 : 11-28-2021::17:44:11.330493
################################################################################            
                               TEST-CASE 0             
################################################################################

2021-11-28 17:44:22,824 : 11-28-2021::17:44:22.824207
Liveness verification (
	--------------------
	 cmd: XF5V0BB8EK
	 ts: 11-28-2021::17:44:14.404706
	 response: eb06d665f9a7ce5ed3904e09801b55435095998226d8bf767349fe4bd7b7cba4
	 response-ts: 11-28-2021::17:44:14.970411
	 response-time: 0.565705 secs
	 liveness-maintained: True
	--------------------
)

2021-11-28 17:44:22,824 : 11-28-2021::17:44:22.824776
Liveness verification (
	--------------------
	 cmd: U71KJKNSNX
	 ts: 11-28-2021::17:44:14.487013
	 response: d61b11c9d661bfdead6d60e502b31f6c60aa44cd1b9519d60ae12231d8b8a1ba
	 response-ts: 11-28-2021::17:44:16.075571
	 response-time: 1.588558 secs
	 liveness-maintained: True
	--------------------
)

2021-11-28 17:44:22,825 : 11-28-2021::17:44:22.825151
Liveness verification (
	--------------------
	 cmd: 64QXUXOO3V
	 ts: 11-28-2021::17:44:14.486587
	 response: d61b11c9d661bfdead6d60e502b31f6c60aa44cd1b9519d60ae12231d8b8a1ba
	 response-ts: 11-28-2021::17:44:16.192774
	 response-time: 1.706187 secs
	 liveness-maintained: True
	--------------------
)

2021-11-28 17:44:22,825 : 11-28-2021::17:44:22.825505
Liveness verification (
	--------------------
	 cmd: L4204XH0TW
	 ts: 11-28-2021::17:44:14.681829
	 response: 5e93ea02d7a959bc0eab30173b67400cad1aa3c47612caf7ac8d3f4b38349323
	 response-ts: 11-28-2021::17:44:22.789949
	 response-time: 8.10812 secs
	 liveness-maintained: False
	--------------------
)

2021-11-28 17:44:22,827 : 11-28-2021::17:44:22.827248
Safety verification (
	num-consistent-ledgers: 2, 
	is-safe: False
)
```

## 3. Not incrementing the rounds on QC

Test for Safety violation in DiemBFT

**Changes to DiemBFT**

```
pacemaker.py
-------------

FROM

def advance_round_on_qc(qc):
        ...
        Pacemaker.current_round = new_round
        Pacemaker.start_timer(new_round)
        ...

TO

def advance_round_on_qc(qc):
        ...
        # Pacemaker.current_round = new_round
        # Pacemaker.start_timer(new_round)
        ...
```

**Test case considered:** *test-case-1*

**Executor log:**

```
2021-11-28 18:43:36,756 : 11-28-2021::18:43:36.756093
################################################################################            
                               TEST-CASE 1             
################################################################################

2021-11-28 18:43:57,466 : 11-28-2021::18:43:57.466182
Liveness violation (
	num-requests-sent: 4, 
	num-responses: 0
)

2021-11-28 18:43:57,472 : 11-28-2021::18:43:57.472497
Empty ledgers, safety cannot be verified
```


## 4. Setting commit-state-id to null in every block

Test for Safety violation in DiemBFT

**Changes to DiemBFT**

```
safety.py
-------------

FROM

def determine_commit_state(block_round, qc):
        if qc.block_round + 1 == block_round and qc.block_id!="#genesis":
            return qc.block_id  # assumed ledger state id to be same as block_id in this implementation
        return None

TO

def determine_commit_state(block_round, qc):
        return None
```

**Test case considered:** *test-case-1*

**Executor log:**

```
2021-11-28 18:43:36,756 : 11-28-2021::18:43:36.756093
################################################################################            
                               TEST-CASE 1             
################################################################################

2021-11-28 18:43:57,466 : 11-28-2021::18:43:57.466182
Liveness violation (
	num-requests-sent: 4, 
	num-responses: 0
)

2021-11-28 18:43:57,472 : 11-28-2021::18:43:57.472497
Empty ledgers, safety cannot be verified
```

## 5. Purposely failing cryto checks

Test for Safety violation in DiemBFT

**Changes to DiemBFT**

```
crypto.py
-------------

FROM

def is_valid(msg, public_key):
    ...

TO

def is_valid(msg, public_key):
    return False
```

**Test case considered:** *test-case-1*

**Executor log:**

```
2021-11-28 18:51:16,441 : 11-28-2021::18:51:16.440969
################################################################################            
                               TEST-CASE 12             
################################################################################

2021-11-28 18:51:37,209 : 11-28-2021::18:51:37.209646
Liveness violation (
	num-requests-sent: 4, 
	num-responses: 0
)

2021-11-28 18:51:37,216 : 11-28-2021::18:51:37.215976
Empty ledgers, safety cannot be verified
```

## 6. Not incrementing the rounds on TC

Test for Safety violation in DiemBFT

**Changes to DiemBFT**

```
pacemaker.py
-------------

FROM

def advance_round_on_tc(tc):
        ...
        Pacemaker.current_round = new_round
        Pacemaker.start_timer(new_round)
        ...

TO

def advance_round_on_tc(tc):
        ...
        # Pacemaker.current_round = new_round
        # Pacemaker.start_timer(new_round)
        ...
```

**Test case considered:** *test-case-7*

**Executor log:**

```
2021-11-29 12:00:08,916 : 11-29-2021::12:00:08.916069
################################################################################            
                               TEST-CASE 7             
################################################################################

2021-11-29 12:00:29,153 : 11-29-2021::12:00:29.153844
Liveness violation (
	num-requests-sent: 4, 
	num-responses: 0
)

2021-11-29 12:00:29,154 : 11-29-2021::12:00:29.154350
Empty ledgers, safety cannot be verified
```