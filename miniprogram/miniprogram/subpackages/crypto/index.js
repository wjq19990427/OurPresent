import { xchacha20poly1305 } from '@noble/ciphers/chacha.js'
import { argon2id } from '@noble/hashes/argon2.js'
import { hkdf } from '@noble/hashes/hkdf.js'
import { sha256 } from '@noble/hashes/sha2.js'

const X25519_BYTES = 32
const X25519_FIELD = BigInt(
  '0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffed'
)
const X25519_A24 = 121665n
const X25519_BASE_POINT = Uint8Array.of(9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
const XCHACHA20_KEY_BYTES = 32
const XCHACHA20_NONCE_BYTES = 24
const HKDF_SHA256_KEY_BYTES = 32
const ARGON2ID_SALT_BYTES = 16
const ARGON2ID_OUTPUT_BYTES = 32
const ARGON2ID_OPSLIMIT = 3
const ARGON2ID_MEMLIMIT_KIB = 64 * 1024

function utf8Bytes(text) {
  const encoded = unescape(encodeURIComponent(text))
  const bytes = new Uint8Array(encoded.length)

  for (let i = 0; i < encoded.length; i += 1) {
    bytes[i] = encoded.charCodeAt(i)
  }

  return bytes
}

function requestWxRandomBytes(length) {
  if (typeof wx === 'undefined' || typeof wx.getRandomValues !== 'function') {
    return Promise.reject(new Error('wx.getRandomValues is unavailable'))
  }

  return new Promise((resolve, reject) => {
    wx.getRandomValues({
      length,
      success: (res) => {
        if (!res || !res.randomValues) {
          reject(new Error('wx.getRandomValues returned no randomValues'))
          return
        }

        resolve(new Uint8Array(res.randomValues))
      },
      fail: (error) => {
        const message =
          error && error.errMsg ? error.errMsg : 'wx.getRandomValues failed'
        reject(new Error(message))
      },
    })
  })
}

function bytesEqual(left, right) {
  if (left.length !== right.length) {
    return false
  }

  let diff = 0
  for (let i = 0; i < left.length; i += 1) {
    diff |= left[i] ^ right[i]
  }

  return diff === 0
}

function wipe(bytes) {
  bytes.fill(0)
}

function modField(value) {
  const remainder = value % X25519_FIELD
  return remainder >= 0n ? remainder : remainder + X25519_FIELD
}

function bytesToNumberLE(bytes) {
  let value = 0n

  for (let i = bytes.length - 1; i >= 0; i -= 1) {
    value = (value << 8n) | BigInt(bytes[i])
  }

  return value
}

function numberToBytesLE(value) {
  const bytes = new Uint8Array(X25519_BYTES)
  let remaining = modField(value)

  for (let i = 0; i < X25519_BYTES; i += 1) {
    bytes[i] = Number(remaining & 255n)
    remaining >>= 8n
  }

  return bytes
}

function modPow(base, exponent) {
  let result = 1n
  let power = modField(base)
  let remaining = exponent

  while (remaining > 0n) {
    if (remaining & 1n) {
      result = modField(result * power)
    }
    power = modField(power * power)
    remaining >>= 1n
  }

  return result
}

function clampX25519Scalar(secret) {
  if (!(secret instanceof Uint8Array) || secret.length !== X25519_BYTES) {
    throw new Error('X25519 secret key must be 32 bytes')
  }

  const scalar = new Uint8Array(secret)
  scalar[0] &= 248
  scalar[31] &= 127
  scalar[31] |= 64
  return bytesToNumberLE(scalar)
}

function decodeX25519Point(point) {
  if (!(point instanceof Uint8Array) || point.length !== X25519_BYTES) {
    throw new Error('X25519 public key must be 32 bytes')
  }

  const masked = new Uint8Array(point)
  masked[31] &= 127
  return modField(bytesToNumberLE(masked))
}

function x25519ScalarMult(secret, point) {
  const scalar = clampX25519Scalar(secret)
  const u = decodeX25519Point(point)
  let x2 = 1n
  let z2 = 0n
  let x3 = u
  let z3 = 1n
  let swap = 0n

  for (let t = 254n; t >= 0n; t -= 1n) {
    const bit = (scalar >> t) & 1n
    swap ^= bit

    if (swap) {
      const tx = x2
      x2 = x3
      x3 = tx
      const tz = z2
      z2 = z3
      z3 = tz
    }

    swap = bit

    const a = modField(x2 + z2)
    const aa = modField(a * a)
    const b = modField(x2 - z2)
    const bb = modField(b * b)
    const e = modField(aa - bb)
    const c = modField(x3 + z3)
    const d = modField(x3 - z3)
    const da = modField(d * a)
    const cb = modField(c * b)

    x3 = modField((da + cb) * (da + cb))
    z3 = modField(u * modField((da - cb) * (da - cb)))
    x2 = modField(aa * bb)
    z2 = modField(e * modField(aa + X25519_A24 * e))
  }

  if (swap) {
    const tx = x2
    x2 = x3
    x3 = tx
    const tz = z2
    z2 = z3
    z3 = tz
  }

  const shared = modField(x2 * modPow(z2, X25519_FIELD - 2n))
  if (shared === 0n) {
    throw new Error('invalid private or public key received')
  }

  return numberToBytesLE(shared)
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
  const [
    aliceSecret,
    bobSecret,
    hkdfSalt,
    aeadKey,
    aeadNonce,
    plaintext,
    argonSalt,
  ] = await Promise.all([
    requestWxRandomBytes(32),
    requestWxRandomBytes(32),
    requestWxRandomBytes(HKDF_SHA256_KEY_BYTES),
    requestWxRandomBytes(XCHACHA20_KEY_BYTES),
    requestWxRandomBytes(XCHACHA20_NONCE_BYTES),
    requestWxRandomBytes(1024),
    requestWxRandomBytes(ARGON2ID_SALT_BYTES),
  ])

  return [
    {
      id: 'x25519',
      ...runNamedTest('X25519 + HKDF-SHA256', () => {
        const alicePublic = x25519ScalarMult(aliceSecret, X25519_BASE_POINT)
        const bobPublic = x25519ScalarMult(bobSecret, X25519_BASE_POINT)
        const sharedOne = x25519ScalarMult(aliceSecret, bobPublic)
        const sharedTwo = x25519ScalarMult(bobSecret, alicePublic)

        if (!bytesEqual(sharedOne, sharedTwo)) {
          throw new Error('X25519 shared secrets differ')
        }

        const derived = hkdf(
          sha256,
          sharedOne,
          hkdfSalt,
          utf8Bytes('ourpresent-smoke-x25519'),
          HKDF_SHA256_KEY_BYTES
        )
        if (derived.length !== HKDF_SHA256_KEY_BYTES) {
          throw new Error('HKDF output length mismatch')
        }

        wipe(sharedOne)
        wipe(sharedTwo)
        wipe(derived)
      }),
    },
    {
      id: 'aead',
      ...runNamedTest('XChaCha20-Poly1305 AEAD', () => {
        const cipher = xchacha20poly1305(aeadKey, aeadNonce)
        const ciphertext = cipher.encrypt(plaintext)
        const decrypted = cipher.decrypt(ciphertext)

        if (!bytesEqual(plaintext, decrypted)) {
          throw new Error('AEAD decrypted plaintext mismatch')
        }
      }),
    },
    {
      id: 'argon2id',
      ...runNamedTest('Argon2id (t=3, m=64MB)', () => {
        const derived = argon2id(utf8Bytes('ourpresent-miniprogram'), argonSalt, {
          t: ARGON2ID_OPSLIMIT,
          m: ARGON2ID_MEMLIMIT_KIB,
          p: 1,
          dkLen: ARGON2ID_OUTPUT_BYTES,
        })

        if (derived.length !== ARGON2ID_OUTPUT_BYTES) {
          throw new Error('Argon2id output length mismatch')
        }

        wipe(derived)
      }),
    },
  ]
}

export { runCryptoSmokeTests }
