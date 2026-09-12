---
author: Kayra
pubDatetime: 2026-07-11T00:00:00Z
title: "Cryptography Foundations"
slug: "cryptography-foundations"
description: "The cryptography a security tester needs to read code and judge it: encoding vs hashing vs encryption, symmetric and asymmetric, cipher modes and why ECB leaks, padding and the padding oracle, authenticated encryption, secure randomness, and key management."
tags: ["security", "cryptography"]
category: notes
draft: true
featured: false
---

## Introduction

You do not need to implement cryptography to test it, but you do need to read a `Cipher.getInstance` string, a key size, and a random-number call and know whether they are sound. This post covers the model behind those judgments: what the pieces are, how they fail, and why the "correct" answer is what it is.

The single idea that ties most of it together, worth holding from the start: **confidentiality is not integrity.** Encryption that hides data does not, by itself, stop an attacker from tampering with it, and that gap is where a surprising number of real breaks live.

## Encoding, hashing, and encryption are three different things

These get used interchangeably in conversation and they are not the same. Telling them apart is half of reading crypto code correctly.

- **Encoding** is a reversible format change with no secret involved. Base64 and hex turn bytes into text so they survive transport. Anyone can decode them. Encoding provides zero security, so a value "protected" by Base64 is not protected at all.
- **Hashing** is a one-way function. It maps input to a fixed-size digest that you cannot reverse back to the input. You use it to verify (does this password match, has this file changed), never to store something you need to read back. SHA-256 is a current general-purpose hash.
- **Encryption** is reversible, but only with a key. Without the key, the ciphertext is meaningless; with it, you recover the exact plaintext. This is the only one of the three that actually protects a secret you need to read again later.

When you see XOR or Base64 standing in for encryption, or MD5 used to "encrypt" a password, the developer has confused these categories, and that is a finding on its own.

## Symmetric vs asymmetric

There are two families of encryption, used for different jobs.

**Symmetric** encryption uses one key for both encryption and decryption. It is fast, so it protects the actual data: files at rest, database fields, message bodies. AES is the standard symmetric cipher. The hard part is key distribution, since both sides need the same secret key.

**Asymmetric** (public-key) encryption uses a key pair: a public key that encrypts and a private key that decrypts. It is slow, so it is not used to bulk-encrypt data. Its jobs are key exchange (encrypt a symmetric key so it can be shared safely) and signatures (prove who sent something). RSA and elliptic-curve schemes are the common ones.

In practice you see them combined: asymmetric crypto safely delivers a symmetric key, then symmetric crypto does the heavy lifting. That is how TLS works.

## Block ciphers, modes, and why ECB leaks

AES is a **block cipher**: it encrypts data in fixed 16-byte blocks. Real data is longer than one block, so you need a rule for chaining blocks together. That rule is the **mode of operation**, and the mode matters as much as the algorithm.

**ECB** (Electronic Codebook) is the naive mode: encrypt each block independently with the same key. The flaw is that identical plaintext blocks always produce identical ciphertext blocks. Structure in the data leaks straight through the encryption. The famous demonstration is encrypting a bitmap image in ECB mode, where you can still see the picture in the ciphertext. ECB is broken for anything with structure, which is almost everything, and it is disallowed by NIST. Seeing `AES/ECB` in a transformation string is an automatic fail.

**CBC** (Cipher Block Chaining) fixes the leak by XORing each plaintext block with the previous ciphertext block before encrypting, so identical blocks no longer look identical. It needs an **IV** (initialization vector) to seed the first block, and that IV must be random and unique per message. CBC hides structure, but as you will see below, it has its own trap.

**GCM** (Galois/Counter Mode) is the modern default. It encrypts like a stream and also produces an authentication tag. That tag is the difference between confidentiality alone and confidentiality plus integrity, which is the next section.

## Padding, and the standards that name it

A block cipher works on whole 16-byte blocks, but your plaintext is rarely an exact multiple of 16. You pad the last block out to a full block before encrypting.

**PKCS** stands for "Public-Key Cryptography Standards," a numbered set of specifications. Two of them come up constantly:

- **PKCS#7** is the padding rule for block ciphers. To add N bytes of padding, you write the value N, N times. Three bytes short of a block becomes `03 03 03`. On decryption you read the last byte, expect that many identical bytes, and strip them. (PKCS#5 is the same scheme historically fixed to 8-byte blocks; you will see the names used loosely.)
- **PKCS#1** is the RSA standard, and its **v1.5** padding is the old scheme for RSA encryption.

Padding is not exotic, but it is exactly where two classic attacks live, because the act of checking padding after decryption can leak information.

## Confidentiality is not integrity: authenticated encryption

This is the core idea. A cipher mode falls into one of two groups.

**Unauthenticated modes** (AES-CBC, AES-CTR) provide confidentiality only. They scramble the data but do nothing to detect tampering. If an attacker flips bits in the ciphertext, decryption still runs and returns some plaintext. The receiver has no built-in way to know the ciphertext was modified in transit or at rest.

**Authenticated modes** (AES-GCM, ChaCha20-Poly1305, the family called AEAD for Authenticated Encryption with Associated Data) provide confidentiality plus integrity. Alongside the ciphertext they produce an **authentication tag**, a MAC computed over the data. On decryption the tag is verified first. If a single bit changed, verification fails and decryption is rejected outright: you get an error, not garbage plaintext. That rejection is what shuts down the attacks below before they can start.

If you must use an unauthenticated mode like CBC, you get integrity back by adding a MAC yourself. **Encrypt-then-MAC** is the correct construction: encrypt the plaintext, then compute a MAC over the ciphertext and IV, and on the receiving side verify the MAC before you decrypt anything. The order matters. Verifying first means tampered ciphertext is thrown out before it ever reaches the decryption or padding logic.

## The padding oracle: how CBC gets broken

CBC has a specific structural property. During decryption, flipping a bit in ciphertext block N flips the same bit in plaintext block N+1 in a predictable way, while turning block N itself into noise. The ciphertext is **malleable**: an attacker can make controlled edits without the key.

Now combine that malleability with padding. After CBC decrypts, the code checks that the PKCS#7 padding is well-formed before using the result. The attack works like this:

1. The attacker has no key, but they can send ciphertext to the app and observe how it responds.
2. They tamper with a ciphertext byte and resend. The app decrypts, checks the padding, and reacts.
3. If the app reveals whether padding was valid, through a different error message, a different response, or even a measurable timing difference, the attacker now has a yes-or-no **oracle**.
4. Working one byte at a time, they adjust the ciphertext and watch for "padding valid." Each valid result leaks one byte of the underlying plaintext. Around 256 guesses per byte, and they recover the entire message without ever learning the key.

That is a padding oracle attack. Two conditions must both hold: a malleable unauthenticated mode (CBC with PKCS#7), and the application leaking padding validity. Break either condition and the attack dies. Authenticated encryption breaks the first (a tampered ciphertext fails the tag check and never reaches padding). Uniform error handling breaks the second. This is why the guidance is always AES-GCM, or CBC only when paired with Encrypt-then-MAC.

## RSA padding: PKCS#1 v1.5 vs OAEP

RSA has the same story in its own dialect. Raw RSA is deterministic and leaks information, so you pad before encrypting, and the padding scheme decides whether RSA is safe.

- **PKCS#1 v1.5** is the old RSA padding. It is vulnerable to **Bleichenbacher's attack**, which is RSA's version of a padding oracle: if the system reveals whether the decrypted padding was well-formed, an attacker recovers the plaintext through many crafted queries. Discouraged since the late 1990s and disallowed by current standards.
- **OAEP** (Optimal Asymmetric Encryption Padding) is the modern replacement. It is randomized and mixed with a hash so that padding-validity leaks give the attacker nothing useful.

So RSA with PKCS#1 v1.5 is a finding, and OAEP is what you want to see.

## Randomness: not all random is random enough

Cryptography leans on unpredictable values everywhere: keys, IVs, nonces, salts, session tokens. If an attacker can predict those, the strongest algorithm around them is worthless.

A regular **PRNG** (pseudorandom number generator) like `java.util.Random`, `Math.random()`, or C's `rand()` is built for speed and statistical spread, not secrecy. Many use a simple linear formula, so an attacker who observes enough output can compute the internal state and predict every future value. Fine for shuffling a list, fatal for generating a key.

A **CSPRNG** (cryptographically secure PRNG) is built so that observing output tells you nothing about future output. `SecureRandom` on Android and `SecRandomCopyBytes` or `arc4random` on iOS are the ones to use in any security context. One trap: seeding a CSPRNG with a fixed value makes it deterministic and therefore predictable, which defeats the whole point. Secure randomness means a secure generator and no hardcoded seed.

## Key management: the key is the secret, so protect the key

The algorithm is public. The key is the only secret, so key handling is often where things actually break, and it is a separate concern from whether the algorithm is strong.

- **Key size:** the key must be long enough that brute force is infeasible. Current floors for sensitive data are 256-bit for AES and 2048-bit (moving toward more) for RSA. A short key undermines a perfect algorithm.
- **Key derivation:** when a key comes from a password, you cannot use the password directly. A **KDF** (key derivation function) like PBKDF2, scrypt, or Argon2 stretches it with many iterations and a unique salt, so that guessing passwords becomes slow and precomputed tables do not help. A weak iteration count is a common finding.
- **Key storage:** the strongest key is worthless if it sits next to the data it protects. Keys hardcoded in the app, or written to plain preferences or files, can be lifted by decompiling the app. Keys belong in the platform keystore (Android KeyStore, iOS Keychain), which stores them outside the app's reach.
- **Hardware backing:** the strongest option keeps the key inside dedicated secure hardware (Android StrongBox, iOS Secure Enclave) where the raw key never enters normal memory at all. The app asks the hardware to encrypt or sign, and only the result comes back. Even a fully compromised app cannot extract the key.

A useful boundary when you report: "is the data encrypted and is the key in the keystore" is a storage question, while "is the key long enough, generated well, and used correctly" is a key-management question. An app can encrypt with flawless AES-256 and still fail because it hardcoded the key.

## How this maps to what you flag

Almost every crypto finding is one of these foundations violated:

- Encoding or hashing used where encryption was needed (XOR, Base64, MD5 to "protect" a secret).
- A broken algorithm or mode (DES, RC4, AES-ECB).
- Confidentiality without integrity (CBC or PKCS#1 v1.5 with no authentication, opening a padding oracle).
- Predictable randomness (a non-crypto PRNG, or a CSPRNG with a fixed seed).
- Poor key management (short keys, weak KDF settings, hardcoded or plaintext-stored keys).

Once you can name which of these a piece of code violates, the rest is mechanical: read the transformation string, the key size, and the randomness source at each call site, and check them against the rules above.
