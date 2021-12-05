import os
import aes
import random

class Crypto():

    @staticmethod
    def generate_partial_key(public_key, private_key, other_party_public_key):
        partial_key = public_key ** private_key
        partial_key = partial_key % other_party_public_key
        return partial_key


    @staticmethod
    def generate_key(partial_key, private_key, other_party_public_key):
        full_key = partial_key ** private_key
        full_key = full_key % other_party_public_key
        return full_key


    @staticmethod
    def encrypt(message, key):
        key = bytes(key)[0:32]
        nonce = os.urandom(16)
        cipher_text = aes.AES(key).encrypt_ctr(bytes(message, "utf-8"), nonce)
        return nonce, cipher_text


    @staticmethod
    def decrypt(cipher_text, nonce, key):
        key = bytes(key)[0:32]
        plain_text = aes.AES(key).decrypt_ctr(cipher_text, nonce)
        return plain_text


    @staticmethod
    def get_prime_number(n):
        k = int((n - 2) / 2)
        a = [0] * (k + 1)
        for i in range(1, k + 1):
            j = i 
            while((i + j + 2 * i * j) <= k):
                a[i + j + 2 * i * j] = 1
                j += 1

        primes = []
        if (n > 2):
            primes += [2]
        for i in range(1, k + 1):
            if (a[i] == 0):
                primes += [2 * i + 1]

        return random.choice(primes)


if __name__=="__main__":

    client_private = Crypto.get_prime_number(1000)
    server_private = Crypto.get_prime_number(1000)
    client_public = Crypto.get_prime_number(1000)
    server_public = Crypto.get_prime_number(1000)

    print(f"Keys:")
    print(f"Server (\n\tpublic: {server_public}, \n\tprivate: {server_private} \n)\n")
    print(f"Client (\n\tpublic: {client_public}, \n\tprivate: {client_private} \n)\n")

    server_response = "Hello client, how are you?"
    client_response = "Hello server, how are you?"

    partial_key = Crypto.generate_partial_key(server_public, server_private, client_public)
    client_key = Crypto.generate_key(partial_key, client_private, server_public)
    server_key = Crypto.generate_key(partial_key, server_private, client_public)

    print(f"Partial key: {partial_key}")
    print(f"Key generated at client: {client_key}")
    print(f"Key generated at server: {server_key}\n")

    nonce, encrypted_msg = Crypto.encrypt(server_response, server_key)
    print(f"Server: Sending {encrypted_msg} to client")
    decrypted_msg = Crypto.decrypt(encrypted_msg, nonce, client_key)
    print(f"Client: Got {decrypted_msg} from server\n")

    nonce, encrypted_msg = Crypto.encrypt(client_response, client_key)
    print(f"Client: Sending {encrypted_msg} to server")
    decrypted_msg = Crypto.decrypt(encrypted_msg, nonce, server_key)
    print(f"Server: Got {decrypted_msg} from client")