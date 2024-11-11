from supabase import Client, create_client
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st


url: str = st.secrets["supabase_url"]
key: str = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

response = supabase.table("dht11").select("*").eq("location", "bedroom").execute()
df = pd.DataFrame(response.data)
df["created_at"] = pd.to_datetime(df["created_at"])
st.write("Number of Measurements: ", len(df))
# print(f"Number of Measurements: {len(df)}")
# print(df.head(2))

fig, ax1 = plt.subplots(figsize=(6 * 1.3, 6))

# First y-axis for temperature
ax1.plot(df["created_at"], df["temperature"], color="tab:red", label="Temperature (°C)")
ax1.set_xlabel("Created At")
ax1.set_ylabel("Temperature (°C)", color="tab:red")
ax1.tick_params(axis="y", labelcolor="tab:red")

# Second y-axis for humidity
ax2 = ax1.twinx()
ax2.plot(df["created_at"], df["humidity"], color="tab:blue", label="Humidity (%)")
ax2.set_ylabel("Humidity (%)", color="tab:blue")
ax2.tick_params(axis="y", labelcolor="tab:blue")

ax1.xaxis.set_major_locator(
    mdates.AutoDateLocator()
)  # Automatically set locator based on data range
ax1.xaxis.set_major_formatter(
    mdates.DateFormatter("%Y-%m-%d %H:%M")
)  # Show full timestamp
fig.autofmt_xdate()  # Rotate date labels for readability

# Title and layout
fig.suptitle("Temperature and Humidity Over Time")
fig.tight_layout()

st.pyplot(fig)
# plt.show()
