import csv
from datetime import datetime, timezone, timedelta
import math
from sgp4.api import Satrec, jday

ZARYA_PATH = "./public/data/zarya.txt"
SCRUBBED_PATH = "./public/data/scrubbed.csv"
OUT_PATH = "./public/data/scrubbed_with_iss.csv"

# parse TLE archive
def parse_tle_epoch(epoch_str):
    year = int(epoch_str[:2])
    year += 1900 if year >= 57 else 2000
    day_of_year = float(epoch_str[2:])
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)

def load_tle_archive(filepath):

    tle_pairs = []
    with open(filepath, 'r') as f:

        lines = f.read().strip().split("\n")
        for i in range(0, len(lines), 2):
            line1 = lines[i].strip()
            line2 = lines[i + 1].strip()

            epoch_str = line1[18:32]
            epoch_dt = parse_tle_epoch(epoch_str)
            tle_pairs.append((epoch_dt, line1, line2))
    
    tle_pairs.sort(key=lambda x: x[0])
    return tle_pairs


def find_best_tle(tle_pairs, target_dt):
    before = [t for t in tle_pairs if t[0] <= target_dt]
    return before[-1] if before else None


def tle_to_latlon(line1, line2, target_dt):
    sat = Satrec.twoline2rv(line1, line2)

    jd, fr = jday(target_dt.year, target_dt.month, target_dt.day, target_dt.hour, target_dt.minute, target_dt.second)
    e, r, v = sat.sgp4(jd, fr)

    if e != 0:
        return None, None
    
    x, y, z = r
    lon = math.degrees(math.atan2(y, x))
    hyp = math.sqrt(x*x + y*y)
    lat = math.degrees(math.atan2(z, hyp))
    return lat, lon


# get distance

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


#main
def process_csv():
    tle_pairs = load_tle_archive(ZARYA_PATH)
    iss_launch = tle_pairs[0][0]  # earliest available TLE epoch

    with open(SCRUBBED_PATH, newline='', encoding='utf-8') as infile, \
         open(OUT_PATH, 'w', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["iss_lat", "iss_lon", "iss_visible_in_sky"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                # Parse datetime in the CSV (assume local time is unknown → treat as UTC)
                dt = datetime.strptime(row["datetime"], "%m/%d/%Y %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                row["iss_lat"] = ""
                row["iss_lon"] = ""
                row["iss_visible_in_sky"] = ""
                writer.writerow(row)
                continue

            # Skip if before ISS launch
            if dt < iss_launch:
                row["iss_lat"] = ""
                row["iss_lon"] = ""
                row["iss_visible_in_sky"] = ""
                writer.writerow(row)
                continue

            # Find best TLE
            best_tle = find_best_tle(tle_pairs, dt)
            if not best_tle:
                row["iss_lat"] = ""
                row["iss_lon"] = ""
                row["iss_visible_in_sky"] = ""
                writer.writerow(row)
                continue

            _, l1, l2 = best_tle
            iss_lat, iss_lon = tle_to_latlon(l1, l2, dt)

            if iss_lat is None:
                row["iss_lat"] = ""
                row["iss_lon"] = ""
                row["iss_visible_in_sky"] = ""
                writer.writerow(row)
                continue

            # Compute visibility (distance threshold ~2000 km)
            if row["latitude"] and row["longitude"]:
                try:
                    report_lat = float(row["latitude"])
                    report_lon = float(row["longitude"])
                    dist_km = haversine(report_lat, report_lon, iss_lat, iss_lon)
                    visible = dist_km <= 2000
                except ValueError:
                    visible = ""
            else:
                visible = ""

            row["iss_lat"] = f"{iss_lat:.6f}"
            row["iss_lon"] = f"{iss_lon:.6f}"
            row["iss_visible_in_sky"] = visible
            writer.writerow(row)

if __name__ == "__main__":
    process_csv()