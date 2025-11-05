# download.py
import os
import json
import shutil
import time
import dropbox
from utils.crypto_aes import aes_decrypt
from utils.crypto_ecc import decrypt_aes_key
from utils.metadata import load_registry
from config import *

dbx = dropbox.Dropbox(ACCESS_TOKEN)

def download_and_reconstruct(filename_choice):
    overall_start = time.perf_counter()

    # Load registry
    registry = load_registry()
    if not registry:
        print("📂 No files available for download.")
        return False

    if filename_choice not in registry:
        print(f"❌ File '{filename_choice}' not found.")
        return False

    manifest = registry[filename_choice]

    # Prepare download folder
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # Decrypt AES key using ECC (measure)
    enc_aes_key = bytes.fromhex(manifest["enc_aes_key"])
    ephemeral_pub = bytes.fromhex(manifest["ephemeral_pub"])

    ecc_start = time.perf_counter()
    aes_key = decrypt_aes_key(enc_aes_key, ephemeral_pub, ECC_PRIVATE_KEY_PATH)
    ecc_time = time.perf_counter() - ecc_start

    # Download & decrypt fragments
    fragments = sorted(manifest["fragments"], key=lambda x: x["index"])
    reconstructed = b""

    download_times = []
    decrypt_times = []
    downloaded_bytes = 0

    print("\n⬇️ Downloading and decrypting fragments...")
    for frag in fragments:
        frag_name = frag["name"]
        dropbox_path = f"{DROPBOX_FOLDER}/{frag_name}"
        local_path = os.path.join(DOWNLOAD_FOLDER, frag_name)

        # Download timing
        dt0 = time.perf_counter()
        metadata, res = dbx.files_download(dropbox_path)
        dt1 = time.perf_counter()
        download_times.append(dt1 - dt0)

        content = res.content
        downloaded_bytes += len(content)

        with open(local_path, "wb") as f:
            f.write(content)

        # Decrypt timing
        dec0 = time.perf_counter()
        try:
            fragment_plain = aes_decrypt(content, aes_key)
        except Exception as e:
            print(f"❌ Decryption failed for fragment {frag_name}: {e}")
            return False
        dec1 = time.perf_counter()
        decrypt_times.append(dec1 - dec0)

        reconstructed += fragment_plain
        print(f"   ✅ Fragment {frag_name} done (download {len(content)} bytes)")

    # Save reconstructed file
    os.makedirs(RECONSTRUCTED_FOLDER, exist_ok=True)
    reconstructed_filename = f"reconstructed_{manifest['original_filename']}"
    reconstructed_path = os.path.join(RECONSTRUCTED_FOLDER, reconstructed_filename)
    with open(reconstructed_path, "wb") as f:
        f.write(reconstructed)

    total_time = time.perf_counter() - overall_start

    # Stats
    avg_download = sum(download_times) / len(download_times) if download_times else 0
    avg_decrypt = sum(decrypt_times) / len(decrypt_times) if decrypt_times else 0
    original_size = manifest.get("original_size", len(reconstructed))
    download_throughput_mb_s = (original_size / (1024*1024)) / total_time if total_time > 0 else 0
    raw_download_throughput_mb_s = (downloaded_bytes / (1024*1024)) / total_time if total_time > 0 else 0

    print("\n🎉 File reconstructed successfully:", reconstructed_path)
    print("\n=== Performance Summary (Download & Reconstruct) ===")
    print(f"File: {manifest['original_filename']}")
    print(f"Original size (manifest): {original_size} bytes ({original_size/1024/1024:.2f} MB)")
    print(f"Fragments: {len(fragments)}")
    print(f"AES-key ECC decrypt time: {ecc_time:.4f} s")
    print(f"Total download time (sum): {sum(download_times):.4f} s")
    print(f" Avg download per fragment: {avg_download:.6f} s")
    print(f"Total AES fragment decrypt time (sum): {sum(decrypt_times):.4f} s")
    print(f" Avg decrypt per fragment: {avg_decrypt:.6f} s")
    print(f"Total downloaded bytes (fragments): {downloaded_bytes} bytes ({downloaded_bytes/1024/1024:.2f} MB)")
    print(f"End-to-end total time (download+decrypt+merge): {total_time:.4f} s")
    print(f"Effective reconstruction throughput (original file): {download_throughput_mb_s:.4f} MB/s")
    print(f"Effective reconstruction throughput (downloaded bytes): {raw_download_throughput_mb_s:.4f} MB/s")

    return True

if __name__ == "__main__":
    registry = load_registry()
    if not registry:
        print("📂 No files available for download.")
        exit()

    print("\n📂 Available files:")
    for i, fname in enumerate(registry.keys(), start=1):
        print(f"{i}. {fname}")

    choice = input("\nEnter filename to download: ").strip()
    download_and_reconstruct(choice)
