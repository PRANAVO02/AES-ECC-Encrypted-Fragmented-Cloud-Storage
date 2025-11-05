import os, shutil, json
import dropbox
from utils.crypto_aes import aes_decrypt
from utils.crypto_ecc import decrypt_aes_key
from config import *

dbx = dropbox.Dropbox(ACCESS_TOKEN)

def download_and_reconstruct():
    """Interactive download and decryption of uploaded files"""

    # --- Step 1: Download encrypted manifest from Dropbox ---
    dropbox_manifest_path = f"{DROPBOX_FOLDER}/manifests.json"
    metadata, res = dbx.files_download(dropbox_manifest_path)
    encrypted_manifest_bytes = res.content

    # --- Step 2: Decrypt manifest using AES key ---
    with open(AES_KEY_FILE, "rb") as f:
        aes_key = f.read()

    manifest_bytes = aes_decrypt(encrypted_manifest_bytes, aes_key)
    registry = json.loads(manifest_bytes)

    if not registry:
        print("📂 No files available for download.")
        return

    # --- Step 3: List uploaded files ---
    print("\n📂 Available files:")
    for i, fname in enumerate(registry.keys(), start=1):
        print(f"{i}. {fname}")

    choice = input("\nEnter filename to download: ").strip()
    if choice not in registry:
        print(f"❌ File '{choice}' not found.")
        return

    manifest = registry[choice]

    # --- Step 4: Decrypt AES key for selected file using ECC ---
    enc_aes_key = bytes.fromhex(manifest["enc_aes_key"])
    ephemeral_pub = bytes.fromhex(manifest["ephemeral_pub"])
    with open(ECC_PRIVATE_KEY_PATH, "rb") as f:
        aes_key = decrypt_aes_key(enc_aes_key, ephemeral_pub, ECC_PRIVATE_KEY_PATH)

    # --- Step 5: Prepare download folder ---
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # --- Step 6: Download and decrypt fragments ---
    fragments = sorted(manifest["fragments"], key=lambda x: x["index"])
    reconstructed = b""

    print("\n⬇️ Downloading and decrypting fragments...")
    for frag in fragments:
        frag_name = frag["name"]
        dropbox_path = f"{DROPBOX_FOLDER}/{frag_name}"
        local_path = os.path.join(DOWNLOAD_FOLDER, frag_name)

        metadata, res = dbx.files_download(dropbox_path)
        with open(local_path, "wb") as f:
            f.write(res.content)

        reconstructed += aes_decrypt(res.content, aes_key)
        print(f"   ✅ Fragment {frag_name} done")

    # --- Step 7: Save reconstructed file ---
    os.makedirs(RECONSTRUCTED_FOLDER, exist_ok=True)
    reconstructed_filename = f"reconstructed_{manifest['original_filename']}"
    reconstructed_path = os.path.join(RECONSTRUCTED_FOLDER, reconstructed_filename)
    with open(reconstructed_path, "wb") as f:
        f.write(reconstructed)

    print(f"\n🎉 File reconstructed successfully: '{reconstructed_path}'")
    return reconstructed_path

# --- Run script interactively ---
if __name__ == "__main__":
    download_and_reconstruct()
