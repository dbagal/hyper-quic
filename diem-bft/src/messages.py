import utils
import crypto
import safety
import main

class Messages:
    VOTE_MSG = 0
    QC = 1
    TIMEOUT_MSG = 2
    TC = 3
    PROPOSAL_MSG = 4
    CLIENT_REQUEST = 5
    CLIENT_RESPONSE = 6
    SYNC_REQUEST = 7
    SYNC_RESPONSE = 8

    type = {
        VOTE_MSG: "vote-msg",
        QC: "qc",
        TIMEOUT_MSG: "timeout-msg",
        TC: "tc",
        PROPOSAL_MSG: "proposal-msg",
        CLIENT_REQUEST: "client-request",
        CLIENT_RESPONSE: "client-response",
        SYNC_REQUEST: "sync-request",
        SYNC_RESPONSE: "sync-response",
    }

    index = {v:k for k,v in type.items()}


class VoteMsg:

    def __init__(self, block_id, block_round, parent_block_id, parent_block_round, 
                exec_state_id, commit_state_id, high_commit_qc, sender, meta_data, log=True):
        
        self.type = Messages.VOTE_MSG
        self.id = utils.get_id()

        # vote info
        self.block_id = block_id
        self.block_round = block_round
        self.parent_block_id = parent_block_id
        self.parent_block_round = parent_block_round
        self.exec_state_id = exec_state_id

        # ledger commit info
        self.commit_state_id = commit_state_id
        self.vote_info_hash = crypto.Crypto.hash( 
                                data=(
                                    self.block_id,
                                    self.block_round,
                                    self.parent_block_id,
                                    self.parent_block_round,
                                    self.exec_state_id,
                                )
                            )

        self.high_commit_qc = high_commit_qc
        self.sender = sender
        self.meta_data = meta_data
        self.signature = crypto.Crypto.sign(
                            data=(
                                self.commit_state_id,
                                self.vote_info_hash
                            ), 
                            private_key=safety.Safety.private_key
                        )
        if log:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"VOTE-MSG created (\n{self.log()}\n)"
            )            
        

    def log(self):
        if self.high_commit_qc is None: high_commit_qc_id = None
        else: high_commit_qc_id = self.high_commit_qc.id

        return utils.get_string_representation({
            "id": self.id,
            "sender": self.sender,
            "block-id": self.block_id,
            "block-round": self.block_round,
            "parent-block-id": self.parent_block_id,
            "parent-block-round": self.parent_block_round,
            "exec-state-id": self.exec_state_id,
            "commit-state-id": self.commit_state_id,
            "high-commit-qc": high_commit_qc_id,
            "meta-data-branch": self.meta_data.branch,
            "meta-data-root-round": self.meta_data.root_round,
            "meta-data-log-index": self.meta_data.log_index
        })



class QC:
    
    def __init__(self, block_id, block_round, parent_block_id, parent_block_round, 
                exec_state_id, commit_state_id, vote_info_hash, signatures, signers, sender, log=True) -> None:
        
        self.type = Messages.QC
        self.id = utils.get_id()

        # vote info
        self.block_id = block_id
        self.block_round = block_round
        self.parent_block_id = parent_block_id
        self.parent_block_round = parent_block_round
        self.exec_state_id = exec_state_id

        # ledger commit info
        self.commit_state_id = commit_state_id
        self.vote_info_hash = vote_info_hash

        self.signatures = signatures
        self.signers = signers
        self.sender = sender
        self.signature = crypto.Crypto.sign(
                            data=self.signatures, 
                            private_key=safety.Safety.private_key
                        )
        
        if log:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"QC formed (\n{self.log()}\n)"
            ) 
        

    def log(self):
        return utils.get_string_representation(
            {
                "id": self.id,
                "sender": self.sender,
                "block-id": self.block_id,
                "block-round": self.block_round,
                "parent-block-id": self.parent_block_id,
                "parent-block-round": self.parent_block_round,
                "exec-state-id": self.exec_state_id,
                "commit-state-id": self.commit_state_id,
                "signers": utils.formatted_list_string(self.signers)
            }
        )



class TimeoutMsg:

    def __init__(self, current_round, high_qc, last_tc, high_commit_qc, sender, meta_data, log=True) -> None:
        self.type = Messages.TIMEOUT_MSG
        self.id = utils.get_id()
        self.sender = sender 

        # timeout info
        self.current_round = current_round
        self.high_qc = high_qc

        self.high_commit_qc = high_commit_qc
        self.last_tc = last_tc

        self.meta_data = meta_data

        self.signature = crypto.Crypto.sign(
                            data = (
                                        self.current_round, 
                                        self.high_qc.block_round
                                    ),
                            private_key = safety.Safety.private_key
                        )

        if log:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"TIMEOUT-MSG created (\n{self.log()}\n)"
            ) 


    def log(self):
        if self.last_tc is None: last_tc_id = None
        else: last_tc_id = self.last_tc.id 

        if self.high_commit_qc is None: high_commit_qc_id = None
        else: high_commit_qc_id = self.high_commit_qc.id

        return utils.get_string_representation(
            {
                "id": self.id,
                "sender": self.sender,
                "for-round":self.current_round,
                "high-qc": self.high_qc.id,
                "high-commit-qc": high_commit_qc_id,
                "last-tc": last_tc_id,
                "meta-data-branch": self.meta_data.branch,
                "meta-data-root-round": self.meta_data.root_round,
                "meta-data-log-index": self.meta_data.log_index
            }
        )
        

class TC:
    
    def __init__(self, current_round, high_qc_rounds, signatures, signers, log=True) -> None:
        self.type = Messages.TC
        self.id = utils.get_id()
        self.current_round = current_round
        self.high_qc_rounds = high_qc_rounds
        self.signatures = signatures
        self.signers = signers
        self.signature = crypto.Crypto.sign(
                            data=self.signatures, 
                            private_key=safety.Safety.private_key
                        )

        if log:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"TC formed (\n{self.log()}\n)"
            ) 


    def log(self):
        return utils.get_string_representation(
            {
                "id": self.id,
                "for-round":self.current_round,
                "high-qc-rounds": utils.formatted_list_string(self.high_qc_rounds)
            }
        )


class MetaData:

    def __init__(self, **params) -> None:
        for param, val in params.items():
            setattr(self, param, val)


class ProposalMsg:
    
    def __init__(self, block, last_tc, high_commit_qc, meta_data, log=True) -> None:
        self.type = Messages.PROPOSAL_MSG
        self.id = utils.get_id()
        self.block = block
        self.last_tc = last_tc
        self.high_commit_qc = high_commit_qc
        self.meta_data = meta_data
        self.sender = self.block.author
        
        self.signature = crypto.Crypto.sign(
                            data = self.block.id,
                            private_key = safety.Safety.private_key
                        )

        if log:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"PROPOSAL-MSG created (\n{self.log()}\n)"
            ) 


    def log(self):
        if self.last_tc is None: last_tc_id = None
        else: last_tc_id = self.last_tc.id 

        if self.high_commit_qc is None: high_commit_qc_id = None
        else: high_commit_qc_id = self.high_commit_qc.id

        return utils.get_string_representation(
            {
                "id": self.id,
                "block-author": self.block.author,
                "block-id": self.block.id,
                "block-round": self.block.round,
                "payload": utils.formatted_list_string([payload.transaction for payload in self.block.payload]),
                "high-qc": self.block.high_qc.id,
                "high-commit-qc": high_commit_qc_id,
                "last-tc": last_tc_id,
                "meta-data-branch": self.meta_data.branch,
                "meta-data-root-round": self.meta_data.root_round,
                "meta-data-log-index": self.meta_data.log_index
            }
        )


class ClientRequest:

    def __init__(self, txn, sender, sender_key, log=True) -> None:
        self.type = Messages.CLIENT_REQUEST
        self.id = utils.get_id()
        self.transaction = txn
        self.sender = sender
        self.sender_key = sender_key 
        self.signature = crypto.Crypto.sign(data = self.transaction, private_key = self.sender_key)
        
        if log:
            utils.log(
                id = self.sender,
                msg = f"CLIENT-REQUEST created (\n{self.log()}\n)"
            ) 

    def log(self):
        _, ts, cmd =  utils.get_transaction_components(self.transaction)
        return utils.get_string_representation(
            {
                "id": self.id,
                "sender": self.sender,
                "timestamp": ts,
                "command": cmd
            }
        )



class ClientResponse:

    def __init__(self, client_request_id, ledger_state_hash, sender, log=True) -> None:
        self.type = Messages.CLIENT_RESPONSE
        self.ledger_state_hash = ledger_state_hash
        self.sender = sender
        self.signature = crypto.Crypto.sign(data = self.ledger_state_hash, private_key = safety.Safety.private_key)
        self.id = client_request_id

        if log:
            utils.log(
                id = self.sender,
                msg = f"CLIENT-RESPONSE created (\n{self.log()}\n)"
            ) 


    def log(self) -> str:
        return utils.get_string_representation(
            {
                "id": self.id,
                "ledger-state-hash": self.ledger_state_hash,
                "sender": self.sender
            }
        )


class SyncData:

    def __init__(self, **params) -> None:
        for param, val in params.items():
            setattr(self, param, val)


class SyncRequest:

    def __init__(self, sync_data, sender, log=True) -> None:
        self.type = Messages.SYNC_REQUEST
        self.id = utils.get_id()
        self.sync_data = sync_data
        self.sender = sender

        self.signature = crypto.Crypto.sign(
            data = self.sync_data, 
            private_key = safety.Safety.private_key
        )
        
        if log:
            utils.log(
                id = self.sender,
                msg = f"SYNC-REQUEST created (\n{self.log()}\n)"
            ) 

    def log(self) -> str:
        return utils.get_string_representation(
            {
                "id": self.id,
                "sender": self.sender,
                "missing-rounds": self.sync_data.missing_rounds,
                "log-index": self.sync_data.log_index
            }
        )


class SyncResponse:

    def __init__(self, id, sync_data, sender, log=True) -> None:
        self.type = Messages.SYNC_RESPONSE
        self.id = id
        self.sync_data = sync_data
        self.sender = sender

        self.signature = crypto.Crypto.sign(
            data = self.sync_data, 
            private_key = safety.Safety.private_key
        )
        if log:
            utils.log(
                id = self.sender,
                msg = f"SYNC-RESPONSE created (\n{self.log()}\n)"
            ) 


    def log(self) -> str:
        return utils.get_string_representation(
            {
                "id": self.id,
                "sender": self.sender,
                #"log_chunk": utils.formatted_list_string(self.sync_data.log_chunk),
                "missing-blocks": utils.formatted_list_string([
                    b.block.id for b in self.sync_data.missing_blocks
                ])
            }
        )