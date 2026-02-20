# ev_dashboard_portfolio.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium

# -------------------------
# 1. Load Data
# -------------------------
df = pd.read_csv("detailed_ev_charging_stations.csv")

# -------------------------
# Recommendation Model (Scoring Based)
# -------------------------

# Normalize numerical features
usage_score = df["Usage Stats (avg users/day)"] / df["Usage Stats (avg users/day)"].max()
distance_score = 1 - (df["Distance to City (km)"] / df["Distance to City (km)"].max())
renewable_score = df["Renewable Energy Source"].apply(lambda x: 1 if x == "Yes" else 0)

# Weighted scoring model
df["Recommendation Score"] = (
    0.5 * usage_score +
    0.3 * distance_score +
    0.2 * renewable_score
)

# Top 25% as recommended
threshold = df["Recommendation Score"].quantile(0.75)
df["Optimal"] = (df["Recommendation Score"] >= threshold).astype(int)

# -------------------------
# 2. Sidebar Filters
# -------------------------
st.sidebar.header("Filters")

address_filter = st.sidebar.multiselect(
    "Select Address",
    sorted(df["Address"].unique())
)

charger_filter = st.sidebar.multiselect(
    "Charger Type",
    sorted(df["Charger Type"].unique())
)

availability_filter = st.sidebar.multiselect(
    "Availability",
    sorted(df["Availability"].unique())
)

renewable_filter = st.sidebar.multiselect(
    "Renewable Energy Source",
    sorted(df["Renewable Energy Source"].unique())
)

# Apply filters
df_filtered = df.copy()

if address_filter:
    df_filtered = df_filtered[df_filtered["Address"].isin(address_filter)]

if charger_filter:
    df_filtered = df_filtered[df_filtered["Charger Type"].isin(charger_filter)]

if availability_filter:
    df_filtered = df_filtered[df_filtered["Availability"].isin(availability_filter)]

if renewable_filter:
    df_filtered = df_filtered[df_filtered["Renewable Energy Source"].isin(renewable_filter)]

# -------------------------
# 3. KPIs
# -------------------------
st.title("EV Station Placement Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Stations", len(df_filtered))

if not df_filtered.empty:
    col2.metric("Avg Cost (USD/kWh)", round(df_filtered["Cost (USD/kWh)"].mean(), 2))
    col3.metric("Avg Daily Usage", round(df_filtered["Usage Stats (avg users/day)"].mean(), 2))
    col4.metric("Avg Charging Capacity (kW)", round(df_filtered["Charging Capacity (kW)"].mean(), 2))

    renewable_percent = round(
        df_filtered["Renewable Energy Source"].value_counts().get("Yes", 0)
        / len(df_filtered) * 100,
        2
    )
    col5.metric("Renewable-powered Stations", f"{renewable_percent}%")
else:
    col2.metric("Avg Cost (USD/kWh)", "-")
    col3.metric("Avg Daily Usage", "-")
    col4.metric("Avg Charging Capacity (kW)", "-")
    col5.metric("Renewable-powered Stations", "-")
    st.warning("No data available for selected filters.")

if df_filtered.empty:
    st.stop()

# -------------------------
# 4. Clustered Map
# -------------------------
st.subheader("EV Stations Map (Clustered)")

m = folium.Map(
    location=[df_filtered["Latitude"].mean(), df_filtered["Longitude"].mean()],
    zoom_start=6
)

marker_cluster = MarkerCluster().add_to(m)

for _, row in df_filtered.iterrows():

    popup_text = f"""
    <b>Station ID:</b> {row['Station ID']}<br>
    <b>Address:</b> {row['Address']}<br>
    <b>Charger Type:</b> {row['Charger Type']}<br>
    <b>Cost:</b> ${row['Cost (USD/kWh)']}<br>
    <b>Usage:</b> {row['Usage Stats (avg users/day)']} users/day<br>
    <b>Capacity:</b> {row['Charging Capacity (kW)']} kW<br>
    <b>Operator:</b> {row['Station Operator']}<br>
    <b>Recommendation Score:</b> {round(row['Recommendation Score'],2)}<br>
    <b>Status:</b> {"Recommended" if row["Optimal"] == 1 else "Existing"}
    """

    color = "green" if row["Optimal"] == 1 else "blue"

    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=popup_text
    ).add_to(marker_cluster)

st_folium(m, width=800, height=500)

# -------------------------
# 5. Usage Heatmap
# -------------------------
st.subheader("Usage Heatmap")

m_heat = folium.Map(
    location=[df_filtered["Latitude"].mean(), df_filtered["Longitude"].mean()],
    zoom_start=6
)

heat_data = [
    [row["Latitude"], row["Longitude"], row["Usage Stats (avg users/day)"]]
    for _, row in df_filtered.iterrows()
]

HeatMap(heat_data, radius=15, max_zoom=13).add_to(m_heat)
st_folium(m_heat, width=800, height=500)

# -------------------------
# 6. Scatter Plot
# -------------------------
st.subheader("Cost vs Usage vs Distance")

fig_scatter = px.scatter(
    df_filtered,
    x="Cost (USD/kWh)",
    y="Usage Stats (avg users/day)",
    size="Charging Capacity (kW)",
    color="Recommendation Score",
    hover_name="Station ID",
    hover_data=["Address", "Charger Type", "Station Operator", "Optimal"],
    color_continuous_scale="Viridis",
    size_max=20
)

st.plotly_chart(fig_scatter, use_container_width=True)

# -------------------------
# 7. Charger Type Distribution
# -------------------------
st.subheader("Charger Type Distribution")

fig_charger = px.pie(
    df_filtered,
    names="Charger Type"
)

st.plotly_chart(fig_charger, use_container_width=True)

# -------------------------
# 8. Operator Analysis
# -------------------------
st.subheader("Stations per Operator")

operator_count = (
    df_filtered.groupby("Station Operator")["Station ID"]
    .count()
    .reset_index(name="Station Count")
)

fig_operator = px.bar(
    operator_count,
    x="Station Operator",
    y="Station Count",
    color="Station Count"
)

st.plotly_chart(fig_operator, use_container_width=True)

# -------------------------
# 9. Recommended Stations Table
# -------------------------
# Recompute threshold based on filtered data
st.subheader("Recommended / Model-Optimal Stations")

# Select top 25% within filtered data (at least 1 row)
top_n = max(1, int(len(df_filtered) * 0.25))

optimal_stations = df_filtered.nlargest(
    top_n,
    "Recommendation Score"
)

st.dataframe(
    optimal_stations[
        ["Station ID", "Address", "Charger Type",
         "Usage Stats (avg users/day)",
         "Charging Capacity (kW)",
         "Recommendation Score"]
    ]
)

# -------------------------
# 10. Download Filtered Data
# -------------------------
st.subheader("Download Filtered Data")

csv = df_filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download CSV",
    data=csv,
    file_name="ev_stations_filtered.csv",
    mime="text/csv",
)
