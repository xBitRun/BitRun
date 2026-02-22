"""
Hyperliquid utilities.

Contains standalone helper functions for Hyperliquid.
The actual trading adapter is now provided by CCXTTrader.
"""

from eth_account import Account


def mnemonic_to_private_key(mnemonic: str, account_index: int = 0) -> str:
    """
    Derive private key from mnemonic phrase using standard Ethereum derivation path.

    Uses BIP-44 derivation path: m/44'/60'/0'/0/{account_index}
    This is the standard path used by MetaMask and most Ethereum wallets.

    Args:
        mnemonic: 12 or 24 word mnemonic phrase
        account_index: Account index in derivation path (default 0 for first account)

    Returns:
        Private key as hex string with 0x prefix

    Raises:
        ValueError: If mnemonic is invalid
    """
    # Enable unaudited HD wallet features
    Account.enable_unaudited_hdwallet_features()

    try:
        # Normalize mnemonic (strip whitespace, lowercase)
        mnemonic = " ".join(mnemonic.strip().lower().split())

        # Validate word count
        word_count = len(mnemonic.split())
        if word_count not in (12, 24):
            raise ValueError(f"Mnemonic must be 12 or 24 words, got {word_count}")

        # Derive account using standard Ethereum path
        # m/44'/60'/0'/0/account_index
        account = Account.from_mnemonic(
            mnemonic, account_path=f"m/44'/60'/0'/0/{account_index}"
        )

        return account.key.hex()

    except Exception as e:
        if "mnemonic" in str(e).lower() or "word" in str(e).lower():
            raise ValueError(f"Invalid mnemonic phrase: {e}")
        raise ValueError(f"Failed to derive private key from mnemonic: {e}")
