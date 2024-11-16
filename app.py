import altair as alt
import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query

st.title("Temperature and Humidity Dashboard")

# Data Loading
st_supabase_client = st.connection(
    name="supabase",
    type=SupabaseConnection,
    ttl=None,
)

date_ranges = ["24h", "7d", "30d", "Max"]
tabs = st.tabs(date_ranges)

for tab, date_range in zip(tabs, date_ranges):

    with tab:
        # get the latest measurements based on the selected date range
        # by constraining the created_at column
        if date_range == "24h":
            cut_off_date = pd.Timestamp.utcnow() - pd.Timedelta(days=1)
        elif date_range == "7d":
            cut_off_date = pd.Timestamp.utcnow() - pd.Timedelta(days=7)
        elif date_range == "30d":
            cut_off_date = pd.Timestamp.utcnow() - pd.Timedelta(days=30)
        elif date_range == "Max":
            cut_off_date = pd.Timestamp(0)
        else:
            raise ValueError("Invalid date range")

        rows = execute_query(
            st_supabase_client.table("dht11")
            .select("*")
            .eq("location", "bedroom")
            .order("created_at", desc=True)
            .gt("created_at", cut_off_date),
            ttl="1m",
        )

        df = pd.DataFrame(rows.data)
        df["created_at"] = pd.to_datetime(df["created_at"])

        latest_temperature = df["temperature"].iloc[0]
        latest_humidity = df["humidity"].iloc[0]

        metric_cols = st.columns(2)
        metric_cols[0].metric("Temperature (°C)", latest_temperature)
        metric_cols[1].metric("Humidity (%)", latest_humidity)

        base = alt.Chart(df).encode(x=alt.X("created_at:T", title="Time"))

        hover = alt.selection_point(
            fields=["created_at"],
            nearest=True,
            on="mouseover",
            empty="none",
            clear="mouseout",
        )

        # Create a line for temperature
        min_temp_scale = df["temperature"].min() - 2
        max_temp_scale = df["temperature"].max() + 2
        temperature_line = base.mark_line(color="red", interpolate="monotone").encode(
            y=alt.Y(
                "temperature:Q",
                title="Temperature (°C)",
                axis=alt.Axis(titleColor="red"),
                scale=alt.Scale(domain=[min_temp_scale, max_temp_scale]),
            )
        )

        # Create a line for humidity with a secondary y-axis
        min_humidity_scale = df["humidity"].min() - 5
        max_humidity_scale = df["humidity"].max() + 5
        humidity_line = base.mark_line(color="blue", interpolate="monotone").encode(
            y=alt.Y(
                "humidity:Q",
                title="Humidity (%)",
                axis=alt.Axis(titleColor="blue"),
                scale=alt.Scale(domain=[min_humidity_scale, max_humidity_scale]),
            ),
        )


        # hover_line = (
        #     base.mark_rule(color="gray", strokeDash=[5, 5])
        #     .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        #     .add_params(hover)
        # )

        # Points to show nearest values on hover for temperature and humidity
        # temperature_points = (
        #     base.mark_circle(color="red", size=50)
        #     .encode(
        #         y="temperature:Q",
        #         opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        #     )
        #     .transform_filter(hover)
        # )

        # humidity_points = (
        #     base.mark_circle(color="blue")
        #     .encode(y="humidity:Q", opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        #     .transform_filter(hover)
        # )

        # Tooltip to display temperature and humidity values on hover
        tooltips = (
            base.mark_rule()
            .encode(
                opacity=alt.condition(hover, alt.value(0.1), alt.value(0)),
                tooltip=[
                    alt.Tooltip("created_at:T", title="Time", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("temperature:Q", title="Temperature (°C)"),
                    alt.Tooltip("humidity:Q", title="Humidity (%)"),
                ],
            )
            .add_params(hover)
        )

        # Layer all elements
        chart = (
            alt.layer(
                temperature_line,
                humidity_line,
                # hover_line,
                # temperature_points,
                # humidity_points,
                tooltips,
            )
            .resolve_scale(y="independent")
            .properties(width=600, height=400, title="Temperature and Humidity over Time")
        )

        st.altair_chart(chart, use_container_width=True)

        num_measurements = len(df)
        with st.expander("More Stats"):
            st.write(f"Total Number of Measurements: {len(df)}")
            st.write(
                f"Latest Measurements (UTC): {df['created_at'].max().strftime('%Y-%m-%d %H:%M')}"
            )

            temp_cols = st.columns(3)
            temp_cols[0].metric(
                "Average Temperature (°C)", f"{df['temperature'].mean():.1f}"
            )
            temp_cols[1].metric("Maximum Temperature (°C)", df["temperature"].max())
            temp_cols[2].metric("Minimum Temperature (°C)", df["temperature"].min())
            humi_cols = st.columns(3)
            humi_cols[0].metric("Average Humidity (%)", f"{df['humidity'].mean():.1f}")
            humi_cols[1].metric("Maximum Humidity (%)", df["humidity"].max())
            humi_cols[2].metric("Minimum Humidity (%)", df["humidity"].min())
