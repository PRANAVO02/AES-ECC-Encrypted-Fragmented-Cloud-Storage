import matplotlib.pyplot as plt

# Data
file_sizes = [1, 100, 500]  # in MB
upload_time = [4.1446, 149.9806, 715.7653]  # in seconds
download_time = [3.9443, 93.0743, 472.7407]  # in seconds
upload_speed = [0.2413, 0.6668, 0.6986]  # in MB/s
download_speed = [0.2535, 1.0744, 1.0577]  # in MB/s

# --------- Graph 1: Time ---------
plt.figure(figsize=(10,5))
plt.plot(file_sizes, upload_time, marker='o', label='Upload Time (s)')
plt.plot(file_sizes, download_time, marker='o', label='Download & Reconstruct Time (s)')
plt.title('Upload vs Download Time')
plt.xlabel('File Size (MB)')
plt.ylabel('Time (s)')
plt.xticks(file_sizes)
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.show()

# --------- Graph 2: Speed ---------
plt.figure(figsize=(10,5))
plt.plot(file_sizes, upload_speed, marker='o', label='Upload Speed (MB/s)')
plt.plot(file_sizes, download_speed, marker='o', label='Download Speed (MB/s)')
plt.title('Upload vs Download Speed')
plt.xlabel('File Size (MB)')
plt.ylabel('Speed (MB/s)')
plt.xticks(file_sizes)
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.show()
