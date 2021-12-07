from collections import defaultdict

import main
import messages
import block_tree
import ledger
import utils


class SyncUp:

    under_progress = False
    timer = dict()
    block_sync_responses = defaultdict(list)
    ledger_sync_responses = defaultdict(int)
    ledger_cmds_hbq = dict()
    blocks_hbq = dict()
    missing_rounds_already_requested = set()

    @staticmethod
    def sync_up_ancestors(meta_data):
        
        # create a list of rounds missing at the validator in its block tree
        missing_rounds = []
        for r in meta_data.branch:
            # if round r is missing and if it is not already sent as a part of some earlier sync request, then only add it
            if r not in block_tree.BlockTree.pending_block_tree.keys() and r not in SyncUp.missing_rounds_already_requested:
                missing_rounds += [r,]
                SyncUp.missing_rounds_already_requested.add(r)

        # if some rounds are missing or if the ledger is not up-to-date request a sync-up
        # remember that a follower's root round is one less than the leader in happy path
        if  block_tree.BlockTree.root_round < meta_data.root_round and \
            (len(missing_rounds)>0 or (meta_data.root_round - block_tree.BlockTree.root_round)>1):
            
            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Sync up needed (\n\tmissing-rounds: {missing_rounds}, \
                    \n\tblock-tree-rounds: {list(block_tree.BlockTree.pending_block_tree.keys())}\
                    \n\troot-round: {block_tree.BlockTree.root_round}\
                    \n\tleader-root-round: {meta_data.root_round},\
                    \n\tlog-index: {ledger.Ledger.log_index}\n)"
            )

            sync_request = messages.SyncRequest(
                sync_data=messages.SyncData(
                    missing_rounds = missing_rounds,
                    log_index = ledger.Ledger.log_index,
                    root_round = block_tree.BlockTree.root_round
                ),
                sender = main.Main._replica.replica_id
            )

            # set under_progress flag denoting that the syncing up is in progress
            SyncUp.under_progress = True
            
            main.Main._replica.broadcast(sync_request)

    
    @staticmethod
    def process_sync_request(sync_request):
        """  
        @function:
        - if a sync request arrives at a validator, this function deals with it
        - get the log chunk if the validator is up-to-date with the desired chunk
        """
        log_chunk = []

        # if requester's ledger is lagging behind send the latest log chunk which is absent at the requestwr
        if (block_tree.BlockTree.root_round - sync_request.sync_data.root_round)>1:
            log_chunk = ledger.Ledger.get_log_chunk(sync_request.sync_data.log_index)
            
            # for each command in the log chunk assign what index it is at, at this particular validator
            if len(log_chunk)>0:
                indices = list(range(
                        sync_request.sync_data.log_index, 
                        sync_request.sync_data.log_index + len(log_chunk)
                    )
                )
                log_chunk = list(zip(indices, log_chunk))

        # get the blocks associated with the missing rounds in the request if they're present at the validator
        missing_blocks = []
        for r in sync_request.sync_data.missing_rounds:
            block = block_tree.BlockTree.pending_block_tree.get(r, None)
            if block is not None:
                missing_blocks += [block]

        # send the sync response back to the requester
        main.Main._replica.send(
            messages.SyncResponse(
                id = sync_request.id,
                sync_data=messages.SyncData(
                    missing_blocks = missing_blocks,
                    log_chunk = log_chunk
                ),
                sender = main.Main._replica.replica_id
            ),
            send_to = sync_request.sender
        )


    @staticmethod
    def process_sync_response(sync_response):
        
        # sync up the missing blocks
        for block_node in sync_response.sync_data.missing_blocks:

            # collect responses for every block to form consensus on every block
            SyncUp.block_sync_responses[block_node.block.id] += [block_node]

            # process the block only if it is certified by a weak certificate of f+1 
            if len(SyncUp.block_sync_responses[block_node.block.id]) == main.Main._replica.system_config.num_byzantine + 1:
                
                # if parent block of the block is present in the block tree, only then process the block
                if block_tree.BlockTree.pending_block_tree.get(block_node.block.high_qc.block_round, None) is not None: 
                    
                    block_tree.BlockTree.add_missing_block(block_node)
                    SyncUp.missing_rounds_already_requested.remove(block_node.block.round)

                    # for all the block's children, process them if they're in the hold-back-queue
                    for child_round in block_node.children_rounds:
                        if child_round not in block_tree.BlockTree.pending_block_tree and \
                            child_round in SyncUp.blocks_hbq:
                            block_node = SyncUp.blocks_hbq[child_round]
                            block_tree.BlockTree.add_missing_block(block_node)
                            SyncUp.missing_rounds_already_requested.remove(block_node.block.round)
                            del SyncUp.blocks_hbq[child_round]
                else:
                    # otherwise wait for f+1 consensus on the parent block and until then preserve it in a hold-back-queue
                    SyncUp.blocks_hbq[block_node.block.round] = block_node

        # sync up the ledger with commands if it is missing any
        for i,cmd in sync_response.sync_data.log_chunk:

            # collect responses for individual commands to form consensus on its position in the log
            SyncUp.ledger_sync_responses[(cmd,i)] += 1

            # update the log with the command once it has collected f+1 weak certificate
            if SyncUp.ledger_sync_responses[(cmd,i)] == main.Main._replica.system_config.num_byzantine + 1:
                
                # if global position of the command in the log is equal to the validator's log index,
                # process the command and write the command to the ledger 
                if i==ledger.Ledger.log_index:
                    ledger.Ledger.write_to_log(cmd)
                    k = i+1
                    while k in SyncUp.ledger_cmds_hbq.keys():
                        ledger.Ledger.write_to_log(SyncUp.ledger_cmds_hbq[k])
                        del SyncUp.ledger_cmds_hbq[k]
                        k += 1
                else:
                    # otherwise, hold it in the hold back queue until all commands above this command are updated in the ledger
                    SyncUp.ledger_cmds_hbq[i] = cmd

        # sync up is complete, when all missing blocks and the missing commands in the ledger has been updated
        if len(SyncUp.ledger_cmds_hbq)==0 and len(SyncUp.blocks_hbq)==0 and \
            all(
                [
                    len(responses)>=(main.Main._replica.system_config.num_byzantine + 1) 
                    for responses in SyncUp.block_sync_responses.values()
                ]
            ) and \
            all(
                [
                    response_count>=(main.Main._replica.system_config.num_byzantine + 1) 
                    for response_count in SyncUp.ledger_sync_responses.values()
                ]
            ):

            SyncUp.under_progress = False

