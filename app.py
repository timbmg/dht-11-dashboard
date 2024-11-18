import altair as alt
import pandas as pd
import streamlit as st
import re
import requests
from st_supabase_connection import SupabaseConnection, execute_query
from streamlit_autorefresh import st_autorefresh
from streamlit_push_notifications import send_alert, send_push

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

# settings

LAT = 49.879244743989915
LON = 8.667196238775123

default_enable_auto_refresh = False
default_enable_notifications = False
default_enable_notification_sound = False
default_display_temp = True
default_display_humidty = True
default_display_sunrise_sunset = False
default_min_temp_threshold = 15
default_max_temp_threshold = 25
default_min_humid_threshold = 0
default_max_humid_threshold = 65
sound_path = "https://cdn.pixabay.com/audio/2022/12/12/audio_e6f0105ae1.mp3"
refresh_interval = 60
start_of_recording_date = "2024-11-12"


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


@st.cache_data
def get_sunrise_sunset_data(
    date_start: str, date_end: str, timezone="UTC"
) -> pd.DataFrame:
    # assert date is in YYYY-MM-DD format
    regex = re.compile(r"\d{4}-\d{2}-\d{2}")
    assert regex.match(date_start) and regex.match(date_end), "Invalid date format."

    url = f"""
    https://api.sunrisesunset.io/json?
    timezone={timezone}
    &lat={LAT}
    &lng={LON}
    &date_start={date_start}
    &date_end={date_end}
    """
    response = requests.get(url)

    if response.status_code == 200:
        raw_results = response.json()["results"]
        df = pd.DataFrame(raw_results)
        # convert 12-hour time to 24-hour time
        keys_to_convert = list(df.columns)
        keys_to_keep = ["date", "timezone", "day_length", "utc_offset"]
        keys_to_convert = [key for key in keys_to_convert if key not in keys_to_keep]
        for key in keys_to_convert:
            df[key] = pd.to_datetime(df[key], format="%I:%M:%S %p").dt.strftime(
                "%H:%M:%S"
            )

        # merge time columns with date
        for key in keys_to_convert:
            df[key] = df["date"] + " " + df[key]

        # round to nearest minute
        for key in keys_to_convert:
            df[key] = pd.to_datetime(df[key]).dt.round("1min")

        # set timezone
        for key in keys_to_convert:
            df[key] = df[key].dt.tz_localize("UTC").dt.tz_convert(timezone)

        return df

    else:
        raise ValueError("Failed to fetch sunrise/sunset data.")


st.title("🌡️ Temperature & Humidity")

with st.expander("Settings", expanded=False):
    # toggle for auto refresh
    auto_refresh = st.checkbox(
        "Auto Refresh",
        value=default_enable_auto_refresh,
        help=f"Refresh every {refresh_interval} seconds.",
    )

    # toggle for notifications
    notifications_toggle = st.checkbox(
        "Notifications",
        value=default_enable_notifications,
        help="Receive notifications when the temperature or humidity exceeds the threshold.",
    )
    if notifications_toggle:
        enable_sound = st.checkbox(
            "Enable Sound",
            value=default_enable_notification_sound,
            help="Play a sound when a notification is received.",
        )
        temp_slider = st.slider(
            "Temperature Threshold",
            min_value=0,
            max_value=40,
            value=(default_min_temp_threshold, default_max_temp_threshold),
        )
        humid_slider = st.slider(
            "Humidity Threshold",
            min_value=0,
            max_value=100,
            value=(default_min_humid_threshold, default_max_humid_threshold),
        )

    display_temperature = st.checkbox(
        "Display Temperature",
        value=default_display_temp,
        help="Display temperature measurements.",
    )

    display_humidity = st.checkbox(
        "Display Humidity",
        value=default_display_humidty,
        help="Display humidity measurements.",
    )

    display_sunrise_sunset = st.checkbox(
        "Display Sunrise & Sunset",
        value=default_display_sunrise_sunset,
        help="Display vertical lines for sunrise and sunset times.",
    )


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
            from_date = pd.Timestamp(start_of_recording_date)
            to_date = pd.Timestamp.utcnow()
            data = fetch_data(from_date, to_date)
        elif date_range == "Custom":
            date_from, hour_from = st.columns(2)
            date_to, hour_to = st.columns(2)
            date_from = date_from.date_input(
                "From Date",
                pd.Timestamp.utcnow() - pd.Timedelta(days=1),
                format="DD/MM/YYYY",
            )
            hour_from = hour_from.time_input("From Time", pd.Timestamp.utcnow())
            date_to = date_to.date_input(
                "To Date", pd.Timestamp.utcnow(), format="DD/MM/YYYY"
            )
            hour_to = hour_to.time_input("To Time", pd.Timestamp.utcnow())

            from_date = pd.Timestamp(f"{date_from} {hour_from}")
            to_date = pd.Timestamp(f"{date_to} {hour_to}")

            enabled = from_date < to_date

            st.button(
                ":material/refresh:",
                key="load_data",
                type="secondary",
                disabled=not enabled,
            )
            if st.session_state.get("load_data"):
                data = fetch_data(from_date, to_date)
        else:
            raise ValueError("Invalid date range")

        if data is not None:

            df = pd.DataFrame(data)
            df["created_at"] = pd.to_datetime(df["created_at"])

            # resample data to 1 minute intervals and use the latest value
            df = df.resample("1T", on="created_at").last().reset_index()

            latest_temperature = df["temperature"].iloc[0]
            latest_humidity = df["humidity"].iloc[0]

            if notifications_toggle:
                temp_too_low = latest_temperature < temp_slider[0]
                temp_too_high = latest_temperature > temp_slider[1]
                if (temp_too_low or temp_too_high) and not st.session_state.get(
                    "temp_alert_send", False
                ):
                    send_push(
                        title=f"{'Low' if temp_too_low else 'High'} Temperature Alert",
                        body=f"⚠️ Current Temperature is {latest_temperature} °C",
                        sound_path=(sound_path if enable_sound else None),
                    )
                    st.session_state["temp_alert_send"] = True
                else:
                    st.session_state["temp_alert_send"] = False

                humi_too_low = latest_humidity < humid_slider[0]
                humi_too_high = latest_humidity > humid_slider[1]
                if (humi_too_low or humi_too_high) and not st.session_state.get(
                    "humid_alert_send", False
                ):
                    # send_alert(
                    #     message=f"⚠️ Humidity is {latest_humidity} %",
                    # )
                    send_push(
                        title=f"{'Low' if temp_too_low else 'High'} Humidity Alert",
                        body=f"⚠️ Humidity is {latest_humidity} %",
                        sound_path=(sound_path if enable_sound else None),
                    )
                    st.session_state["humid_alert_send"] = True
                else:
                    st.session_state["humid_alert_send"] = False

            metric_cols = st.columns(2)
            mean_temp = df["temperature"].mean()
            delta_temp = latest_temperature - mean_temp
            delta_color = "off"
            delta_temp = round(delta_temp, 1)
            metric_cols[0].metric(
                "Temperature",
                f"{latest_temperature} °C",
                f"{delta_temp} °C",
                delta_color,
                help=f"Temperature in Celsius compared to the average temperature in the last {date_range}.",
            )

            mean_humidity = df["humidity"].mean()
            delta_humidity = latest_humidity - mean_humidity
            delta_color = "inverse"
            delta_humidity = round(delta_humidity, 1)
            metric_cols[1].metric(
                "Humidity",
                f"{latest_humidity} %",
                f"{delta_humidity} %",
                delta_color,
                help=f"Humidity compared to the average humidity in the last {date_range}.",
            )

            # get the earliest sunrise and latest sunset
            df_sunrise_sunset = get_sunrise_sunset_data(
                date_start=from_date.strftime("%Y-%m-%d"),
                date_end=to_date.strftime("%Y-%m-%d"),
            )

            # find the closest measuremet in df to sunrise and sunset and set them to 1
            # else set them to 0
            df["sunrise_sunset"] = 0
            for index, row in df_sunrise_sunset.iterrows():
                sunrise = row["sunrise"]
                sunset = row["sunset"]
                df.loc[
                    (df["created_at"] - sunrise).abs().idxmin(),
                    ["sunrise_sunset", "sunrise_sunset_type"],
                ] = [1, "Sunrise"]
                df.loc[
                    (df["created_at"] - sunset).abs().idxmin(),
                    ["sunrise_sunset", "sunrise_sunset_type"],
                ] = [1, "Sunset"]
            # remove the first sunset, sunrise indicators from the measurement
            # sunrise_sunset column as they are not accurate
            df["sunrise_sunset"] = df["sunrise_sunset"].shift(-1)
            df["sunrise_sunset_type"] = df["sunrise_sunset_type"].shift(-1)

            base = alt.Chart(df).encode(x=alt.X("created_at:T", title=""))

            # show vertical lines for sunrise and sunset times, i.e. when sunrise and sunset are 1
            sunrise_sunset = (
                base.mark_rule(strokeDash=[5, 5])
                .encode(
                    x="created_at:T",
                    color=alt.Color(
                        "sunrise_sunset_type:N",
                        scale=alt.Scale(range=["orange", "purple"]),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("sunrise_sunset_type:N", title="Event"),
                        alt.Tooltip(
                            "created_at:T", title="Time", format="%Y-%m-%d %H:%M"
                        ),
                    ],
                )
                .transform_filter("datum.sunrise_sunset == 1")
            )
            # make the vertical lines into arrows for sunrise and sunset times
            sunrise_sunset = sunrise_sunset.transform_calculate(
                y="datum.sunrise_sunset_type == 'Sunrise' ? 0 : 400"
            )

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
            temperature_line = base.mark_line(
                color="red", interpolate="monotone"
            ).encode(
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
                        alt.Tooltip(
                            "created_at:T", title="Time", format="%Y-%m-%d %H:%M"
                        ),
                        alt.Tooltip("temperature:Q", title="Temperature (°C)"),
                        alt.Tooltip("humidity:Q", title="Humidity (%)"),
                    ],
                )
                .add_params(hover)
            )

            # Layer all elements
            layers = []
            if display_temperature:
                layers.append(temperature_line)
            if display_humidity:
                layers.append(humidity_line)
            if display_temperature or display_humidity:
                layers.append(tooltips)
            if display_sunrise_sunset:
                layers.append(sunrise_sunset)
            chart = (
                alt.layer(*layers)
                .resolve_scale(y="independent")
                .properties(width=600, height=400, title="")
            )

            st.altair_chart(chart, use_container_width=True)

            num_measurements = len(df)
            st.subheader("Statistics", divider=True)
            general_cols = st.columns(3)
            general_cols[0].metric("Measurements", num_measurements)
            general_cols[1].metric(
                "Latest Measurements (UTC)",
                df["created_at"].max().strftime("%H:%M %d/%m"),
            )

            temp_cols = st.columns(3)
            temp_cols[0].metric(
                "Average Temperature", f"{df['temperature'].mean():.1f}°C"
            )
            temp_cols[1].metric("Maximum Temperature", f"{df['temperature'].max()} °C")
            temp_cols[2].metric("Minimum Temperature", f"{df['temperature'].min()} °C")
            humi_cols = st.columns(3)
            humi_cols[0].metric(
                "Average Humidity (%)", f"{df['humidity'].mean():.1f} %"
            )
            humi_cols[1].metric("Maximum Humidity (%)", f"{df['humidity'].max()} %")
            humi_cols[2].metric("Minimum Humidity (%)", f"{df['humidity'].min()} %")

            with st.expander("Raw Data", expanded=False):
                st.header("Measurements")
                st.write(df)
                st.header("Sunrise & Sunset")
                st.write(df_sunrise_sunset)
if auto_refresh:
    # refresh every 60 seconds
    st_autorefresh(interval=refresh_interval * 1000, key="autorefresh")
