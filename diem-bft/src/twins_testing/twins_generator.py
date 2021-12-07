from copy import deepcopy
import itertools
import random
import os, sys
import json
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(os.path.join(parent_dir, "src"))
import config


class TwinsGenerator:

    def __init__(self, nodes, compromised_nodes) -> None:

        # ids of all validators and the compromised validators in the system
        self.nodes = nodes
        self.compromised_nodes = compromised_nodes

        current_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(parent_dir, "config", "twins_config.json")

        with open(config_path, "r") as fp:
            configuration = json.load(fp)
        self.config = TwinsGenerator.Config(configuration["generator"])
        self.intra_partition_msg_loss_candidates = {"vote-msg", "proposal-msg"}


    class Config:
        def __init__(self, kwargs) -> None:
            for property, value in kwargs.items():
                setattr(self, property, value)
        
    
    class PropertyNotFoundError(Exception):
        # raised when a desired property is not present in the configuration specified by the user
        def __init__(self, prop):
            msg = f"'{prop}' not set in configuration"
            super().__init__(msg)


    def partition_in_k_subsets(self, set, k):
        """  
        @params:
        - set:              list of elements which needs to be partitioned into k groups
        - k:                number of groups
        - min_subset_size:  minimum number of elements that atleast one group in the partition needs to have      
        
        @returns:
        - partitions => [
            [[e1, e2], [e3]],
            [[e1], [e1, e2]], 
            ...
        ]

        @references:
        - https://github.com/asonnino/twins-generator/blob/master/generator.py
        """
        def stirling2(n, k):
            assert n > 0 and k > 0
            if k == 1:
                return [
                    [[x for x in range(n)]]
                ]
            elif k == n:
                return [
                    [[x] for x in range(n)]
                ]
            else:
                s_n1_k1 = stirling2(n-1, k-1)
                tmp = stirling2(n-1, k)

                for i in range(len(s_n1_k1)):
                    s_n1_k1[i].append([n-1])
                
                k_s_n1_k = []
                for _ in range(k):
                    k_s_n1_k += deepcopy(tmp)
                for i in range(len(tmp)*k):
                    k_s_n1_k[i][i // len(tmp)] += [n-1]

                partitions = s_n1_k1 + k_s_n1_k
                return partitions

        partitions = stirling2(len(set), k)

        partitions = [
                [
                    [set[idx] for idx in subset] 
                    for subset in partition
                ] 
                for partition in partitions
            ]

        return partitions


    def add_twins(self, partitions):
        """  
        @params:
        - partitions:   python list of the following form => [
                            [[e1, e2], [e3]],
                            [[e1], [e1, e2]], 
                            ...
                        ]
        @function:
        - determines node acting as twins for the compromised nodes
        - based on the 'allow_twins_in_same_partition' policy, the partitions are filtered
        """
        twins = dict()
        for cnode in self.compromised_nodes:
            i = self.nodes.index(cnode)
            twin_i = (i+1)%len(self.nodes)
            twins[cnode] = self.nodes[twin_i]

        
        if not self.config.allow_twins_in_same_partition:

            # drop all network partitions containing both twins in the same partition
            filtered_partitions = []
            for nw_partition in partitions:
                drop = False
                for partition_subset in nw_partition: 
                    for cnode, twin in twins.items():
                        if cnode in partition_subset and twin in partition_subset:
                            drop = True
                            break
                    if drop: break
                if not drop:
                    filtered_partitions += [nw_partition]
        else:
            filtered_partitions = partitions

        return twins, filtered_partitions


    def project_num_test_cases(self, num_parts, num_leaders, num_rounds):
        """  
        @params:
        - num_parts:    number of all possible partitions
        - num_leaders:  number of validators which are allowed to be the leader
        - num_rounds:   number of rounds for which twins should emulate the protocol

        @function:
        - calculate the number of test cases that will be generated with the given input
        """           
        num_leader_partition_comb = num_leaders * num_parts
        num_round_scenario_mappings = num_leader_partition_comb**num_rounds
        return num_round_scenario_mappings


    def liveness_assured_filtering(self, test_cases, num_byzantine):
        """  
        @function:
        - if there is a sequence of alternating qc and tc, then liveness is blocked
        - to avoid this, there should be atleast 2 consecutive rounds with a 2f+1 quorum to
            ensure 2 consecutive qcs are formed and the block is committed
        """
        def liveness_assured(test_case, quorum_size):
            partitions = [case[1] for case in test_case]
            prev_size = len(max(partitions[0], key=len))
            consecutive_quorums_found = False
            for i in range(1, len(partitions)):
                partition = partitions[i]
                max_subset_size = len(max(partition, key=len))
                if max_subset_size == prev_size==quorum_size:
                    consecutive_quorums_found = True
                    break
                prev_size = max_subset_size
            return consecutive_quorums_found

        qsize = 2*num_byzantine + 1
        
        return [test_case for test_case in test_cases if liveness_assured(test_case, qsize)]


    def generate_test_cases(self):
        """  
        @function:
        - generate test cases

        @format:
        - test_cases = [
            [ l1, [[e1], [e2,e3, e1']] ] // round 0
            [ l4, [[e2, e1'], [e3, e1]] ] // round 1
            ...
        ]
        """
        num_byzantine = (len(self.nodes)-1)//3

        # get all configuration information and raise an error if user hasn't specified a configuration property
        try:
            num_partition_sets = self.config.num_partition_sets
            elect_faulty_leaders_only = self.config.elect_faulty_leaders_only
            num_partition_sets = self.config.num_partition_sets
            num_test_cases_upper_bound = self.config.num_test_cases_upper_bound
            enumeration_order = self.config.enumeration_order
            num_rounds = self.config.num_rounds
        except AttributeError as e:
            args = e.args
            prop = args.split("'")[-2]
            raise TwinsGenerator.PropertyNotFoundError(prop)

        # generate partitions of the following form:  [
        #    [[e1, e2], [e3]],
        #    [[e1], [e1, e2]], 
        #    ...
        # ]
        partitions = self.partition_in_k_subsets(
                        self.nodes, 
                        k=num_partition_sets
                    )

        # add twins to appropriate sets in every partition
        twins, partitions = self.add_twins(partitions)
        
        # specify validators who are allowed to be a leader in the testcases generated by twins
        if elect_faulty_leaders_only == True: 
            leader_candidates = self.compromised_nodes
        else: 
            leader_candidates = self.nodes

        # create all possible combinations assigning each leader to each partition i.e take a cross-product
        scenarios = list(itertools.product(leader_candidates, partitions))

        num_test_cases_projected = self.project_num_test_cases(
                                        num_parts = len(partitions), 
                                        num_leaders = len(leader_candidates), 
                                        num_rounds = num_rounds
                                    )
        print(f"\nTotal number of test cases without pruning: {num_test_cases_projected}")
        
        # in case there are insufficient scenarios for 'num_rounds' rounds, 
        # repeat the scenarios in a round robin fashion to fill up the test-case for 'num_rounds' rounds
        def repeat_scenarios(test_case, target_num_rounds):
            extended_test_case = [None,]*target_num_rounds
            j = 0
            for i in range(target_num_rounds):
                extended_test_case[i] = test_case[j]
                j = (j+1)%len(test_case)
            return extended_test_case

        test_cases=[]

        # apply enumeration ordering only if the projected number of test cases exceed the bound 
        # given in the configuration
        if num_test_cases_projected > num_test_cases_upper_bound:
            if enumeration_order == "deterministic":
                # reduce the number of rounds, 
                # take cross-product of the scenarios with themselves for the reduced number of rounds
                r = num_rounds-1
                while True:
                    num_test_cases_projected = self.project_num_test_cases(
                                        num_parts = len(partitions), 
                                        num_leaders = len(leader_candidates), 
                                        num_rounds = r
                                    )
                    if num_test_cases_projected > num_test_cases_upper_bound:
                        r-=1
                    else:
                        break
                test_cases_for_reduced_rounds = list(itertools.product(scenarios, repeat=r))
                
                # repeat the scenarios in a round robin fashion to fill up the test-case for 'num_rounds' rounds
                for test_case in test_cases_for_reduced_rounds:
                    test_cases += [repeat_scenarios(test_case, num_rounds)]

            elif enumeration_order == "randomized":
                num_scenarios_to_consider_per_round = []
                num_test_cases = 1
                num_scenarios = len(scenarios)

                # find the number of scenarios to consider per round for the cross-product
                # taking cross-product of the scenarios with themselves for 'num_rounds' times gives us the test_cases
                for i in range(num_rounds):
                    running_num = num_test_cases*num_scenarios
                    # if number of test cases is exceeding the upper bound, 
                    # reduce the number of scenarios to consider for the cross product for this round
                    if running_num>=num_test_cases_upper_bound:
                        while running_num>num_test_cases_upper_bound:
                            num_scenarios -= 1
                            running_num = num_test_cases*num_scenarios
                    num_test_cases = running_num
                    num_scenarios_to_consider_per_round += [num_scenarios]

                # for every round, consider a random subset of the scenarios for the cross-product
                scenario_list = []
                for n in num_scenarios_to_consider_per_round:
                    random.shuffle(scenarios)
                    scenario_list += [scenarios[0:n]]
                test_cases = itertools.product(*scenario_list)

        else:
            test_cases = list(itertools.product(scenarios, repeat=num_rounds)) 

        print(f"\nTotal number of test cases with pruning: {len(test_cases)}")

        test_cases = self.liveness_assured_filtering(test_cases, num_byzantine)

        print(f"\nTotal number of test cases after liveness assured filtering: {len(test_cases)}\n")
        
        path = os.path.dirname(os.path.abspath(__file__))
        self.write_test_cases(raw_test_cases=test_cases, twins=twins, path=path)


    def intra_partition_loss_schedule(self, num_rounds):
        def random_subset(_set):
            out = set()
            for elem in _set:       
                if random.randint(0, 1) == 0:
                    out.add(elem)

            if len(out)==0:
                i = random.randint(0, 1)
                out.add(list(_set)[i])
            return out
        
        return [
            list(random_subset(self.intra_partition_msg_loss_candidates))
            for _ in range(num_rounds)
        ]


    def write_test_cases(self, raw_test_cases, twins, path):
        """  
        @params:
        - raw_test_cases:   list of test cases with each test case having the following form 
                            [
                                [ l1, [[e1], [e2,e3, e1']] ] // round 0
                                [ l4, [[e2, e1'], [e3, e1]] ] // round 1
                                ...
                            ]
        - path:             path to save the test_cases.json file containing all the generated test_cases

        @format:
        - {
            "test-case-0": {
                "num-rounds": 10,
                "nodes": [
                    "r1@localhost:8000:8001",
                    "r2@localhost:8002:8003",
                    "r3@localhost:8004:8005",
                    "r4@localhost:8006:8007"
                ],
                "compromised_nodes": [
                    "r4@localhost:8006:8007"
                ],
                "twins": {
                    "r4@localhost:8006:8007": "r1@localhost:8000:8001"
                },
                "0": {
                    "leader": "r4@localhost:8006:8007",
                    "partition": [
                        [
                            "r1@localhost:8000:8001",
                            "r2@localhost:8002:8003",
                            "r3@localhost:8004:8005"
                        ],
                        [
                            "r4@localhost:8006:8007"
                        ]
                    ],
                    "msg-lost": []
            },

            "test_case_1": {
                    ...
            }
        }
        """
        processed_test_cases = {
            "num-testcases": len(raw_test_cases)
        }

        for i,test_case in enumerate(raw_test_cases):
            msg_loss_schedule = self.intra_partition_loss_schedule(self.config.num_rounds)
            processed_test_case = {
                "num-rounds": self.config.num_rounds, 
                "nodes": list(self.nodes), 
                "compromised-nodes":self.compromised_nodes,
                "twins": twins
            }
            for j in range(len(test_case)):
                leader = raw_test_cases[i][j][0]
                partition = raw_test_cases[i][j][1]
                # start with first round
                bft_round = j
                processed_test_case[bft_round] = {
                    "leader": leader,
                    "partition": partition,
                    "msgs-lost": msg_loss_schedule[j]
                }
            processed_test_cases["test-case-"+str(i)] = processed_test_case
            
        with open(os.path.join(path, "test_cases.json"), 'w', encoding='utf-8') as f:
            json.dump(processed_test_cases, f, ensure_ascii=False, indent=4)


if __name__=="__main__":
    system_config = config.SystemConfig()
    nodes = system_config.replica_id_set
    cnodes = [nodes[-1]]
    generator = TwinsGenerator(nodes, cnodes)
    generator.generate_test_cases()
    
