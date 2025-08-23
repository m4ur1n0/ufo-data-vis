import pandas as pd
import matplotlib.pyplot as plt


# df = pd.read_csv('./public/data/scrubbed.csv')


# # --- BASIC EXPLORATION ---
# print("First 5 rows:")
# print(df.head(), "\n")

# print("Data info:")
# print(df.info(), "\n")

# print("Summary statistics (numeric columns):")
# print(df.describe(), "\n")

# # Count missing values
# print("Missing values per column:")
# print(df.isna().sum(), "\n")

# # --- BASIC CLEANING ---
# # Strip whitespace from column names
# df.columns = df.columns.str.strip()

# # Convert datetime to proper datetime object
# df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')

# # Convert duration (seconds) to numeric
# df['duration (seconds)'] = pd.to_numeric(df['duration (seconds)'], errors='coerce')

# --- VISUALIZATIONS ---

# # 1. Top 10 UFO shapes
# shape_counts = df['shape'].value_counts().head(10)
# shape_counts.plot(kind='bar', figsize=(8, 5), color='skyblue')
# plt.title("Top 10 UFO Shapes")
# plt.xlabel("Shape")
# plt.ylabel("Number of Sightings")
# plt.xticks(rotation=45)
# plt.tight_layout()
# plt.show()

# plt.figure()

# # 2. Sightings by US state (only rows with valid 2-letter state codes)
# state_counts = df['state'].str.upper().value_counts().head(10)
# state_counts.plot(kind='bar', figsize=(8, 5), color='orange')
# plt.title("Top 10 States by UFO Sightings")
# plt.xlabel("State")
# plt.ylabel("Number of Sightings")
# plt.tight_layout()
# plt.show()

# plt.figure()


# # 3. Duration (seconds) histogram (clipped to avoid extreme outliers)
# df['duration (seconds)'].clip(upper=3600).dropna().hist(bins=50, color='green', figsize=(8, 5))
# plt.title("UFO Sighting Durations (seconds, clipped at 1 hour)")
# plt.xlabel("Duration (seconds)")
# plt.ylabel("Frequency")
# plt.tight_layout()
# plt.show()

# plt.figure()

# # 4. Scatter plot of latitude vs longitude
# plt.figure(figsize=(8, 5))
# plt.scatter(str(df['longitude']), str(df['latitude']), alpha=0.3, s=10, c='purple')
# plt.title("UFO Sightings Map")
# plt.xlabel("Longitude")
# plt.ylabel("Latitude")
# plt.tight_layout()
# plt.show()

# plt.figure()


# # 5. Sightings over time
# df.set_index('datetime').resample('YE').size().plot(figsize=(10, 5), color='red')
# plt.title("UFO Sightings Over Time")
# plt.xlabel("Year")
# plt.ylabel("Number of Sightings")
# plt.tight_layout()
# plt.show()

# plt.figure()



### NOW LOOKING THROUGH WITH ISS DATA



df = pd.read_csv("./public/data/scrubbed_with_iss.csv")


# reports post iss laumch date
iss_launch_date = pd.Timestamp("1988-11-20")
df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

after_launch = df[df["datetime"] >= iss_launch_date]

# drop those without data
has_iss_data = after_launch.dropna(subset=["iss_lat", "iss_lon"])

# of those, how many had ISS visible
iss_visible = has_iss_data[has_iss_data["iss_visible_in_sky"] == True]

# of those visible, how many reported 'light'
visible_light_shape = iss_visible[iss_visible["shape"].str.contains("light", case=False, na=False)]

print("1) ISS data exploration:")
print(f"   After launch: {len(after_launch)} rows")
print(f"   Have ISS data: {len(has_iss_data)} rows")
print(f"   ISS visible: {len(iss_visible)} rows")
print(f"   Visible + 'light' in shape: {len(visible_light_shape)} rows")
print(f"   In summation, {len(iss_visible)} out of the {len(has_iss_data)} we have data about were underneath the path of the ISS. And {len(visible_light_shape)} reported the UFO they saw as being something like 'a streak of light'")

# now top 5 data/city report clusters
df["date_only"] = df["datetime"].dt.date
city_date_counts = df.groupby(["date_only", "city"]).size().reset_index(name="count")
top5_clusters = city_date_counts.sort_values("count", ascending=False).head(10)

print("2) Top 5 Date / City Clusters : ")
print(top5_clusters)
print()

# now the reports that are longer than 10 minutes in duration
long_reports = df[pd.to_numeric(df["duration (seconds)"], errors="coerce") > 600]
print(f"3) Reports of sightings with a duration longer than 10 minutes : {len(long_reports)}")