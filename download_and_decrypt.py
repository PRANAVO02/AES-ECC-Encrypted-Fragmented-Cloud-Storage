import os, shutil, json
import dropbox
from utils.crypto_aes import aes_decrypt
from utils.crypto_ecc import decrypt_aes_key
from config import *

dbx = dropbox.Dropbox(ACCESS_TOKEN)

def decrypt_and_reconstruct_web(filename):
    """
    Decrypt and reconstruct a file (non-interactive) for Flask.
    Returns the path of reconstructed file.
    """
    # Download encrypted manifest
    metadata, res = dbx.files_download(f"{DROPBOX_FOLDER}/manifests.json")
    encrypted_manifest_bytes = res.content

    # Decrypt manifest
    with open(AES_KEY_FILE, "rb") as f:
        aes_key = f.read()
    manifest_bytes = aes_decrypt(encrypted_manifest_bytes, aes_key)
    registry = json.loads(manifest_bytes)

    if filename not in registry:
        raise Exception(f"File '{filename}' not found")

    manifest = registry[filename]

    # Decrypt AES key using ECC
    enc_aes_key = bytes.fromhex(manifest["enc_aes_key"])
    ephemeral_pub = bytes.fromhex(manifest["ephemeral_pub"])
    with open(ECC_PRIVATE_KEY_PATH, "rb") as f:
        aes_key = decrypt_aes_key(enc_aes_key, ephemeral_pub, ECC_PRIVATE_KEY_PATH)

    # Prepare download folder
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # Download and decrypt fragments
    fragments = sorted(manifest["fragments"], key=lambda x: x["index"])
    reconstructed = b""
    for frag in fragments:
        frag_name = frag["name"]
        metadata, res = dbx.files_download(f"{DROPBOX_FOLDER}/{frag_name}")
        reconstructed += aes_decrypt(res.content, aes_key)

    # Save reconstructed file
    os.makedirs(RECONSTRUCTED_FOLDER, exist_ok=True)
    reconstructed_filename = f"reconstructed_{manifest['original_filename']}"
    reconstructed_path = os.path.join(RECONSTRUCTED_FOLDER, reconstructed_filename)
    with open(reconstructed_path, "wb") as f:
        f.write(reconstructed)

    return reconstructed_path
