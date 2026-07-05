import urllib.request
import os
import shutil

USER_AGENT = "gh-ecosystem-intelligence/0.1 (DE Portfolio)"

def download_hour(date_str: str, hour: int, dest_dir: str) -> str:

    day_dir = os.path.join(dest_dir, date_str)
    final_path = os.path.join(day_dir, f"{date_str}-{hour}.json.gz")
    tmp_path = final_path + ".tmp"

    if os.path.exists(final_path):
        return "skipped"

    os.makedirs(day_dir, exist_ok = True)

    url = f"https://data.gharchive.org/{date_str}-{hour}.json.gz"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp_path, "wb") as f:
            shutil.copyfileobj(r, f)
        os.rename(tmp_path, final_path)
        return "downloaded"
    except Exception as e:
        print(f"Failed {url}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return "failed"

def download_range(start_date, end_date, dest_dir):
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    
    date = start
    while date <= end:
        date_str = date.strftime("%Y-%m-%d")

        for hour in range(24):
            status = download_hour(date_str, hour, dest_dir)
            summary[status] += 1
            print(f"[{date_str} {hour:02d}] {status}")
            
        date += timedelta(days=1)



    return summary