import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query


st_supabase_client = st.connection(
    name="supabase",
    type=SupabaseConnection,
    ttl=None,
)

rows = execute_query(
    st_supabase_client.table("dht11").select("*").eq("location", "bedroom"),
    ttl="10m",
)

df = pd.DataFrame(rows.data)
df["created_at"] = pd.to_datetime(df["created_at"])
st.write(f"Number of Measurements: {len(df)}")
st.write(f"Latest Measurements (UTC): {df['created_at'].max()}")

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
