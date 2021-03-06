__author__ = 'shane'

# N id the size of the seed array for KSA
N = 256

def ksa(k):
    """

    :param k: the byte array key (IV prepended to the secret key)
    :return: a pseudo random permutation of [0, 1, 2,..., 255]
    """
    s = [i for i in range(N)]
    j = 0
    for i in range(N):
        j = (j + s[i] + k[i % len(k)]) % N
        # Swap(s[i], s[j])
        temp = s[i]
        s[i] = s[j]
        s[j] = temp
    return s


def prga(s, data_length):
    """

    :param s: a pseudo random permutation of [0, 1, 2,..., 255] generated by ksa
    :param data_length: length of the packet data (message + checksum) in bytes
    :return: key stream to XOR the packet data with
    """
    z = []
    i = 0
    j = 0
    for x in range(data_length):
        i = (i+1) % N
        j = (j + s[i+1]) % N
        # Swap(s[i], s[j])
        temp = s[i]
        s[i] = s[j]
        s[j] = temp
        z.append(s[(s[i] + s[j]) % N])
    return z


def rc4(key, plaintext):
    key_stream = prga(ksa(key), len(plaintext))
    ciphertext = []
    for byte, k in zip(plaintext, key_stream):
        ciphertext.append(byte ^ k)
    return ciphertext


def crc32(data):
    # http://www.ross.net/crc/download/crc_v3.txt
    return


def make_wep(wep_key, data):
    # Calculate CRC-32
    # Choose IV
    # Encrypt with RC4
    return