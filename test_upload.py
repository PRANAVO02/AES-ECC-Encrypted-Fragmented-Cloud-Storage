
import os
import uuid
import json
import time
import dropbox
from utils.crypto_aes import aes_encrypt
from utils.crypto_ecc import encrypt_aes_key
from utils.file_handler import split_file
from utils.metadata import load_registry, save_registry
from config import *

# Initialize Dropbox
dbx = dropbox.Dropbox(ACCESS_TOKEN)

# Function to choose fragment size dynamically
def get_fragment_size(file_size_bytes):
    MB = 1024 * 1024
    if file_size_bytes < 10 * MB:
        return 1 * MB       # Small files → 1MB
    elif file_size_bytes < 100 * MB:
        return 5 * MB       # Medium files → 5MB
    elif file_size_bytes < 1024 * MB:   # Less than 1GB
        return 10 * MB      # Large files → 10MB
    else:
        return 20 * MB      # Very large files → 20MB

def encrypt_and_upload(file_path):
    overall_start = time.perf_counter()

    filename = os.path.basename(file_path)
    os.makedirs(FRAGMENT_FOLDER, exist_ok=True)

    # Read file
    read_start = time.perf_counter()
    with open(file_path, "rb") as f:
        data = f.read()
    read_time = time.perf_counter() - read_start
    original_size = len(data)

    # Choose fragment size dynamically
    fragment_size = get_fragment_size(original_size)
    print(f"Using fragment size: {fragment_size / (1024*1024)} MB")

    # Split file
    split_start = time.perf_counter()
    fragments = split_file(data, fragment_size)
    split_time = time.perf_counter() - split_start

    fragments_meta = []

    # Load AES key
    with open(AES_KEY_FILE, "rb") as f:
        aes_key = f.read()

    # Encrypt AES key using ECC public key (measure)
    ecc_start = time.perf_counter()
    enc_aes_key, ephemeral_pub_bytes = encrypt_aes_key(aes_key, ECC_PUBLIC_KEY_PATH)
    ecc_time = time.perf_counter() - ecc_start

    # Per-fragment stats
    encrypt_times = []
    upload_times = []
    frag_sizes_post_enc = []
    total_uploaded_bytes = 0

    for idx, fragment in enumerate(fragments):
        # AES encryption timing
        et0 = time.perf_counter()
        encrypted_fragment = aes_encrypt(fragment, aes_key)
        et1 = time.perf_counter()
        encrypt_times.append(et1 - et0)

        # Save locally
        frag_name = f"{uuid.uuid4().hex}.frag"
        local_path = os.path.join(FRAGMENT_FOLDER, frag_name)
        with open(local_path, "wb") as f:
            f.write(encrypted_fragment)

        # Upload timing
        ut0 = time.perf_counter()
        with open(local_path, "rb") as f:
            data_to_upload = f.read()
            dbx.files_upload(data_to_upload, f"{DROPBOX_FOLDER}/{frag_name}", mode=dropbox.files.WriteMode.overwrite)
        ut1 = time.perf_counter()
        upload_times.append(ut1 - ut0)

        frag_sizes_post_enc.append(len(data_to_upload))
        total_uploaded_bytes += len(data_to_upload)

        fragments_meta.append({"index": idx, "name": frag_name, "enc_size": len(data_to_upload)})
        print(f"Uploaded fragment {idx+1}/{len(fragments)}: {frag_name}  (enc {len(data_to_upload)} bytes)")

    # Save manifest
    manifest = {
        "original_filename": filename,
        "original_size": original_size,
        "total_fragments": len(fragments_meta),
        "fragment_size": fragment_size,
        "fragments": fragments_meta,
        "enc_aes_key": enc_aes_key.hex(),
        "ephemeral_pub": ephemeral_pub_bytes.hex()
    }

    # Update registry
    registry = load_registry()
    registry[filename] = manifest
    save_registry(registry)

    # Upload registry/manifest
    with open("manifests.json", "rb") as f:
        manifest_bytes = f.read()
        dbx.files_upload(manifest_bytes, f"{DROPBOX_FOLDER}/manifests.json", mode=dropbox.files.WriteMode.overwrite)

    total_time = time.perf_counter() - overall_start

    # Compute basic stats
    avg_encrypt = sum(encrypt_times) / len(encrypt_times) if encrypt_times else 0
    avg_upload = sum(upload_times) / len(upload_times) if upload_times else 0
    total_fragments = len(fragments_meta)

    # Throughput metrics (MB/s)
    upload_throughput_mb_s = (original_size / (1024*1024)) / total_time if total_time > 0 else 0
    enc_upload_throughput_mb_s = (total_uploaded_bytes / (1024*1024)) / total_time if total_time > 0 else 0

    print("\n✅ File uploaded with AES-ECC hybrid encryption.")
    print("\n=== Performance Summary (Upload) ===")
    print(f"File: {filename}")
    print(f"Original size: {original_size} bytes ({original_size/1024/1024:.2f} MB)")
    print(f"Fragments: {total_fragments} (fragment_size={fragment_size} bytes)")
    print(f"Read time: {read_time:.4f} s")
    print(f"Split time: {split_time:.4f} s")
    print(f"ECC (AES-key encrypt) time: {ecc_time:.4f} s")
    print(f"Total AES fragment encryption time (sum): {sum(encrypt_times):.4f} s")
    print(f" Avg encrypt per fragment: {avg_encrypt:.6f} s")
    print(f"Total fragment upload time (sum): {sum(upload_times):.4f} s")
    print(f" Avg upload per fragment: {avg_upload:.6f} s")
    print(f"Total uploaded bytes (fragments only): {total_uploaded_bytes} bytes ({total_uploaded_bytes/1024/1024:.2f} MB)")
    print(f"Manifest size: {len(manifest_bytes)} bytes")
    print(f"End-to-end total time: {total_time:.4f} s")
    print(f"Effective upload throughput (original file): {upload_throughput_mb_s:.4f} MB/s")
    print(f"Effective upload throughput (uploaded bytes incl. IVs): {enc_upload_throughput_mb_s:.4f} MB/s")

if __name__ == "__main__":
    file_path = input("Enter file path to upload: ").strip()
    encrypt_and_upload(file_path)
