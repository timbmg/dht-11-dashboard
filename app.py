import altair as alt
import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query

st.set_page_config(
    page_title="HW7 T&H",
    page_icon="🏡",
    layout="centered",
)

st_supabase_client = st.connection(
    name="supabase",
    type=SupabaseConnection,
    ttl=None,
)

def fetch_data(from_date, to_date):

    return execute_query(
        st_supabase_client.table("dht11")
        .select("*")
        .eq("location", "bedroom")
        .order("created_at", desc=True)
        .gte("created_at", from_date)
        .lte("created_at", to_date),
        ttl="1m",
    ).data

st.title("🌡️ Temperature & Humidity")

date_ranges = ["1h", "6h", "24h", "7d", "30d", "Max", "Custom"]
tabs = st.tabs(date_ranges)

for tab, date_range in zip(tabs, date_ranges):

    with tab:
        data = None
        if date_range == "1h":
            to_date = pd.Timestamp.utcnow()
            from_date = to_date - pd.Timedelta(hours=1)
            data = fetch_data(from_date, to_date)
        elif date_range == "6h":
            to_date = pd.Timestamp.utcnow()
            from_date = to_date - pd.Timedelta(hours=6, minutes=1)
            data = fetch_data(from_date, to_date)
        elif date_range == "24h":
            to_date = pd.Timestamp.utcnow()
            from_date = to_date - pd.Timedelta(hours=24, minutes=1)
            data = fetch_data(from_date, to_date)
        elif date_range == "7d":
            to_date = pd.Timestamp.utcnow()
            from_date = to_date - pd.Timedelta(days=7, minutes=1)
            data = fetch_data(from_date, to_date)
        elif date_range == "30d":
            to_date = pd.Timestamp.utcnow()
            from_date = to_date - pd.Timedelta(days=30, minutes=1)
            data = fetch_data(from_date, to_date)
        elif date_range == "Max":
            from_date = pd.Timestamp("2021-01-01")
            to_date = pd.Timestamp.utcnow()
            data = fetch_data(from_date, to_date)
        elif date_range == "Custom":
            date_from, hour_from = st.columns(2)
            date_to, hour_to  = st.columns(2)
            date_from = date_from.date_input("From Date", pd.Timestamp.utcnow() - pd.Timedelta(days=1), format="DD/MM/YYYY")
            hour_from = hour_from.time_input("From Time", pd.Timestamp.utcnow())
            date_to = date_to.date_input("To Date", pd.Timestamp.utcnow(), format="DD/MM/YYYY")
            hour_to = hour_to.time_input("To Time", pd.Timestamp.utcnow())

            from_date = pd.Timestamp(f"{date_from} {hour_from}")
            to_date = pd.Timestamp(f"{date_to} {hour_to}")

            enabled = from_date < to_date

            st.button(":material/refresh:", key="load_data", type="secondary", disabled=not enabled)
            if st.session_state.get("load_data"):
                data = fetch_data(from_date, to_date)
        else:
            raise ValueError("Invalid date range")

        if data is not None:

            df = pd.DataFrame(data)
            df["created_at"] = pd.to_datetime(df["created_at"])

            latest_temperature = df["temperature"].iloc[0]
            latest_humidity = df["humidity"].iloc[0]

            metric_cols = st.columns(2)
            mean_temp = df["temperature"].mean()
            delta_temp = latest_temperature - mean_temp
            delta_color = "off"
            delta_temp = round(delta_temp, 1)
            metric_cols[0].metric(
                "Temperature",
                f"{latest_temperature} °C",
                delta_temp,
                delta_color,
                help=f"Temperature in Celsius compared to the average temperature in the last {date_range}.",
            )

            mean_humidity = df["humidity"].mean()
            delta_humidity = latest_humidity - mean_humidity
            delta_color = "inverse"
            delta_humidity = round(delta_humidity, 1)
            metric_cols[1].metric(
                "Humidity", f"{latest_humidity} %", delta_humidity, delta_color,
                help=f"Humidity compared to the average humidity in the last {date_range}.",
            )

            base = alt.Chart(df).encode(x=alt.X("created_at:T", title=""))

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
                .properties(width=600, height=400, title="")
            )

            st.altair_chart(chart, use_container_width=True)

            num_measurements = len(df)
            st.subheader("Statistics", divider=True)
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
