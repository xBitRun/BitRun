/**
 * Transport Encryption Utility
 *
 * Uses Web Crypto API (RSA-OAEP + AES-GCM) to encrypt sensitive data
 * before transmitting to the server. The server's RSA public key is
 * fetched once and cached. A per-message AES key is generated,
 * used to encrypt the payload, then the AES key itself is encrypted
 * with the RSA public key.
 *
 * Wire format (base64-encoded):
 *   [RSA-encrypted AES key (256 bytes)] + [AES-GCM nonce (12 bytes)] + [AES-GCM ciphertext]
 */

import { api } from './api/client';

let cachedPublicKey: CryptoKey | null = null;
let isEnabled: boolean | null = null;

/**
 * Fetch the server's RSA public key and import it for encryption.
 * Returns null if transport encryption is not enabled on the server.
 */
async function getServerPublicKey(): Promise<CryptoKey | null> {
  if (cachedPublicKey) return cachedPublicKey;

  try {
    const response = await api.get<{
      public_key: string;
      algorithm: string;
      key_size: number;
    }>('/crypto/public-key');

    const pem = response.public_key;

    // Parse PEM to ArrayBuffer
    const pemBody = pem
      .replace(/-----BEGIN PUBLIC KEY-----/, '')
      .replace(/-----END PUBLIC KEY-----/, '')
      .replace(/\s/g, '');
    const binaryDer = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));

    // Import as CryptoKey
    cachedPublicKey = await crypto.subtle.importKey(
      'spki',
      binaryDer.buffer,
      {
        name: 'RSA-OAEP',
        hash: 'SHA-256',
      },
      false,
      ['encrypt']
    );

    isEnabled = true;
    return cachedPublicKey;
  } catch {
    // Server returned 400 (not enabled) or other error
    isEnabled = false;
    return null;
  }
}

/**
 * Check whether transport encryption is available.
 */
export async function isTransportEncryptionEnabled(): Promise<boolean> {
  if (isEnabled !== null) return isEnabled;
  await getServerPublicKey();
  return isEnabled ?? false;
}

/**
 * Encrypt a plaintext string using the server's public key.
 *
 * Format: base64(RSA_encrypted_AES_key + AES_GCM_nonce + AES_GCM_ciphertext)
 *
 * Returns the encrypted string, or the original plaintext if encryption
 * is not enabled (graceful degradation).
 */
export async function encryptForTransport(plaintext: string): Promise<string> {
  const rsaKey = await getServerPublicKey();
  if (!rsaKey) {
    // Transport encryption not enabled — send plaintext
    return plaintext;
  }

  const encoder = new TextEncoder();
  const data = encoder.encode(plaintext);

  // Generate a random AES-256 key
  const aesKey = await crypto.subtle.generateKey(
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt']
  );

  // Generate a random 12-byte nonce for AES-GCM
  const nonce = crypto.getRandomValues(new Uint8Array(12));

  // Encrypt the data with AES-GCM
  const aesCiphertext = new Uint8Array(
    await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: nonce },
      aesKey,
      data
    )
  );

  // Export the raw AES key bytes
  const rawAesKey = new Uint8Array(await crypto.subtle.exportKey('raw', aesKey));

  // Encrypt the AES key with the server's RSA public key
  const encryptedAesKey = new Uint8Array(
    await crypto.subtle.encrypt(
      { name: 'RSA-OAEP' },
      rsaKey,
      rawAesKey
    )
  );

  // Concatenate: encryptedAesKey + nonce + aesCiphertext
  const combined = new Uint8Array(
    encryptedAesKey.length + nonce.length + aesCiphertext.length
  );
  combined.set(encryptedAesKey, 0);
  combined.set(nonce, encryptedAesKey.length);
  combined.set(aesCiphertext, encryptedAesKey.length + nonce.length);

  // Encode as base64
  return btoa(String.fromCharCode(...combined));
}

/**
 * Encrypt multiple fields in an object.
 * Only encrypts the specified field names; other fields pass through.
 */
export async function encryptFields<T extends object>(
  data: T,
  fieldNames: string[]
): Promise<T> {
  const enabled = await isTransportEncryptionEnabled();
  if (!enabled) return data;

  const result = { ...data } as Record<string, unknown>;
  for (const field of fieldNames) {
    const value = result[field];
    if (typeof value === 'string' && value.length > 0) {
      result[field] = await encryptForTransport(value);
    }
  }
  return result as T;
}
