const sodium = require('./vendor/sodium.js')

function utf8Bytes(text) {
  const encoded = unescape(encodeURIComponent(text))
  const bytes = new Uint8Array(encoded.length)

  for (let i = 0; i < encoded.length; i += 1) {
    bytes[i] = encoded.charCodeAt(i)
  }

  return bytes
}

function concatBytes(...arrays) {
  const total = arrays.reduce((sum, item) => sum + item.length, 0)
  const merged = new Uint8Array(total)
  let offset = 0

  arrays.forEach((item) => {
    merged.set(item, offset)
    offset += item.length
  })

  return merged
}

function hkdfSha256(ikm, salt, info, length) {
  const normalizedSalt =
    salt && salt.length
      ? salt
      : new Uint8Array(sodium.crypto_auth_hmacsha256_KEYBYTES)

  const prk = sodium.crypto_auth_hmacsha256(ikm, normalizedSalt)
  const output = new Uint8Array(length)
  const infoBytes = info || new Uint8Array(0)
  let previous = new Uint8Array(0)
  let offset = 0
  let counter = 1

  while (offset < length) {
    previous = sodium.crypto_auth_hmacsha256(
      concatBytes(previous, infoBytes, Uint8Array.of(counter)),
      prk
    )
    const chunk = previous.slice(0, Math.min(previous.length, length - offset))
    output.set(chunk, offset)
    offset += chunk.length
    counter += 1
  }

  sodium.memzero(prk)
  return output
}

function runNamedTest(label, executor) {
  const startedAt = Date.now()

  try {
    executor()
    return {
      label,
      status: 'passed',
      message: `✓ 通过 · ${Date.now() - startedAt}ms`,
    }
  } catch (error) {
    return {
      label,
      status: 'failed',
      message: `✗ 失败 · ${error && error.message ? error.message : String(error)}`,
    }
  }
}

async function runCryptoSmokeTests() {
  await sodium.ready

  return [
    {
      id: 'x25519',
      ...runNamedTest('X25519 + HKDF-SHA256', () => {
        const alice = sodium.crypto_box_keypair()
        const bob = sodium.crypto_box_keypair()
        const sharedOne = sodium.crypto_scalarmult(alice.privateKey, bob.publicKey)
        const sharedTwo = sodium.crypto_scalarmult(bob.privateKey, alice.publicKey)

        if (!sodium.memcmp(sharedOne, sharedTwo)) {
          throw new Error('ECDH shared secret mismatch')
        }

        const derivedKey = hkdfSha256(
          sharedOne,
          sodium.randombytes_buf(sodium.crypto_auth_hmacsha256_KEYBYTES),
          utf8Bytes('ourpresent-smoke-hkdf-v1'),
          32
        )

        if (derivedKey.length !== 32) {
          throw new Error('HKDF output length mismatch')
        }
      }),
    },
    {
      id: 'aead',
      ...runNamedTest('XChaCha20-Poly1305 AEAD', () => {
        const key = sodium.crypto_aead_xchacha20poly1305_ietf_keygen()
        const nonce = sodium.randombytes_buf(
          sodium.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES
        )
        const plaintext = sodium.randombytes_buf(1024)
        const aad = utf8Bytes('ourpresent-smoke-aead')
        const ciphertext = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
          plaintext,
          aad,
          null,
          nonce,
          key
        )
        const decrypted = sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(
          null,
          ciphertext,
          aad,
          nonce,
          key
        )

        if (!sodium.memcmp(plaintext, decrypted)) {
          throw new Error('AEAD roundtrip mismatch')
        }
      }),
    },
    {
      id: 'argon2id',
      ...runNamedTest('Argon2id (t=3, m=64MB)', () => {
        const salt = sodium.randombytes_buf(sodium.crypto_pwhash_SALTBYTES)
        const password = utf8Bytes('ourpresent-smoke-password')
        const derived = sodium.crypto_pwhash(
          32,
          password,
          salt,
          3,
          64 * 1024 * 1024,
          sodium.crypto_pwhash_ALG_ARGON2ID13
        )

        if (derived.length !== 32) {
          throw new Error('Argon2id output length mismatch')
        }
      }),
    },
  ]
}

module.exports = {
  runCryptoSmokeTests,
}
