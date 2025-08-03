import subprocess

def scan_file_clamav(file_path: str) -> bool:
    try:
        result = subprocess.run(["clamscan", file_path], stdout=subprocess.PIPE)
        return "Infected files: 0" in result.stdout.decode()
    except Exception as e:
        print(f"ClamAV scan failed: {e}")
        return False
