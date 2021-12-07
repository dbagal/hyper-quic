import pickle
import base64
import nacl.encoding
import nacl.hash
from nacl.bindings.utils import sodium_memcmp
from nacl.signing import SigningKey, VerifyKey
import messages


class Crypto:

    hash_algo = nacl.hash.sha256

    @staticmethod
    def hash(data):
        hash_digest = None
        msg = pickle.dumps(data)
        hash_digest = Crypto.hash_algo(msg, encoder=nacl.encoding.HexEncoder)
        return hash_digest.decode()


    @staticmethod
    def sign(data, private_key):
        data = Crypto.hash(data).encode()
        private_key = nacl.signing.SigningKey(base64.b64decode(private_key.encode()), 
                                                encoder=nacl.encoding.HexEncoder)
        signed_data = private_key.sign(data)
        return signed_data


    @staticmethod
    def msg_integrity_check(received_msg, msg_digest):
        received_msg_digest = Crypto.hash_algo(received_msg, encoder=nacl.encoding.HexEncoder)
        if sodium_memcmp(received_msg_digest, msg_digest):
            return True
        return False


    @staticmethod
    def generate_keys():
        private_key_object = SigningKey.generate()
        public_key_bytes = private_key_object.verify_key.encode()
        private_key = base64.b64encode(private_key_object.encode(encoder=nacl.encoding.HexEncoder)).decode()
        public_key = base64.b64encode(public_key_bytes).decode()
        return (private_key, public_key)


    @staticmethod
    def verify(signed_data, public_key_base64):
        public_key = VerifyKey(base64.b64decode(public_key_base64.encode()))
        try:
            hashed_data = public_key.verify(signed_data.message, signed_data.signature)
            return hashed_data.decode()
        except:
            return None


    @staticmethod
    def is_valid(msg, public_key):
        hashed_data_received = Crypto.verify(msg.signature, public_key)
        if msg.type == messages.Messages.VOTE_MSG:
            data_to_hash=(
                msg.commit_state_id,
                msg.vote_info_hash
            )
        elif msg.type == messages.Messages.QC:
            data_to_hash=msg.signatures
        
        elif msg.type == messages.Messages.TIMEOUT_MSG:
            data_to_hash = (
                msg.current_round, 
                msg.high_qc.block_round
            )
        
        elif msg.type == messages.Messages.TC:
            data_to_hash=msg.signatures

        elif msg.type == messages.Messages.PROPOSAL_MSG:
            data_to_hash = msg.block.id

        elif msg.type == messages.Messages.CLIENT_REQUEST:
            data_to_hash=msg.transaction

        elif msg.type == messages.Messages.CLIENT_RESPONSE:
            data_to_hash=msg.ledger_state_hash

        elif msg.type == messages.Messages.SYNC_REQUEST:
            data_to_hash = msg.sync_data

        elif msg.type == messages.Messages.SYNC_RESPONSE:
            data_to_hash = msg.sync_data

        if Crypto.hash(data=data_to_hash)==hashed_data_received:
            return True
        
        return False
      