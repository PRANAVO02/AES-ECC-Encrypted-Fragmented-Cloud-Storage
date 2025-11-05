import os, uuid, json
import dropbox
from utils.crypto_aes import aes_encrypt
from utils.crypto_ecc import encrypt_aes_key
from utils.file_handler import split_file
from utils.metadata import load_registry, save_registry
from config import *

# Initialize Dropbox
dbx = dropbox.Dropbox(ACCESS_TOKEN)

def encrypt_and_upload_web(file_path):
    filename = os.path.basename(file_path)
    os.makedirs(FRAGMENT_FOLDER, exist_ok=True)

    # Read file
    with open(file_path, "rb") as f:
        data = f.read()

    # Split into fragments
    fragments = split_file(data, FRAGMENT_SIZE)
    fragments_meta = []

    # Load AES key
    with open(AES_KEY_FILE, "rb") as f:
        aes_key = f.read()

    # Encrypt AES key using ECC
    enc_aes_key, ephemeral_pub_bytes = encrypt_aes_key(aes_key, ECC_PUBLIC_KEY_PATH)

    # Encrypt fragments and upload
    for idx, fragment in enumerate(fragments):
        encrypted_fragment = aes_encrypt(fragment, aes_key)
        frag_name = f"{uuid.uuid4().hex}.frag"
        local_path = os.path.join(FRAGMENT_FOLDER, frag_name)
        with open(local_path, "wb") as f:
            f.write(encrypted_fragment)

        dropbox_path = f"{DROPBOX_FOLDER}/{frag_name}"
        with open(local_path, "rb") as f:
            dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

        fragments_meta.append({"index": idx, "name": frag_name})

    # Manifest entry
    manifest_entry = {
        "original_filename": filename,
        "total_fragments": len(fragments_meta),
        "fragments": fragments_meta,
        "enc_aes_key": enc_aes_key.hex(),
        "ephemeral_pub": ephemeral_pub_bytes.hex()
    }

    # Load registry, update and save
    registry = load_registry()
    registry[filename] = manifest_entry
    save_registry(registry)

    # Encrypt entire manifest
    with open("manifests.json", "rb") as f:
        manifest_bytes = f.read()
    encrypted_manifest = aes_encrypt(manifest_bytes, aes_key)

    # Upload encrypted manifest to Dropbox
    dbx.files_upload(encrypted_manifest, f"{DROPBOX_FOLDER}/manifests.json", mode=dropbox.files.WriteMode.overwrite)

    return filename
