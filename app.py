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

# Ensure Optimal column exists
if "Optimal" not in df.columns:
    df["Optimal"] = 0  # 0 = existing, 1 = recommended

# -------------------------
# 2. Sidebar Filters
# -------------------------
st.sidebar.header("Filters")
# city_filter = st.sidebar.multiselect("Select City", df["City"].unique(), df["City"].unique())
charger_filter = st.sidebar.multiselect("Charger Type", df["Charger Type"].unique(), df["Charger Type"].unique())
availability_filter = st.sidebar.multiselect("Availability", df["Availability"].unique(), df["Availability"].unique())
renewable_filter = st.sidebar.multiselect("Renewable Energy Source", df["Renewable Energy Source"].unique(), df["Renewable Energy Source"].unique())

df_filtered = df[
    # (df["City"].isin(city_filter)) &
    (df["Charger Type"].isin(charger_filter)) &
    (df["Availability"].isin(availability_filter)) &
    (df["Renewable Energy Source"].isin(renewable_filter))
]

# -------------------------
# 3. KPIs
# -------------------------
st.title("EV Station Placement Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Stations", len(df_filtered))
col2.metric("Avg Cost (USD/kWh)", round(df_filtered["Cost (USD/kWh)"].mean(), 2))
col3.metric("Avg Daily Usage", round(df_filtered["Usage Stats (avg users/day)"].mean(), 2))
col4.metric("Avg Charging Capacity (kW)", round(df_filtered["Charging Capacity (kW)"].mean(), 2))
col5.metric("Renewable-powered Stations", f"{round(df_filtered['Renewable Energy Source'].value_counts().get('Yes',0)/len(df_filtered)*100,2)}%")

# -------------------------
# 4. Clustered Map
# -------------------------
st.subheader("EV Stations Map (Clustered)")

m = folium.Map(location=[df_filtered["Latitude"].mean(), df_filtered["Longitude"].mean()], zoom_start=6)
marker_cluster = MarkerCluster().add_to(m)

for idx, row in df_filtered.iterrows():
    popup_text = f"""
    <b>Station ID:</b> {row['Station ID']}<br>
    <b>Address:</b> {row['Address']}<br>
    <b>Charger Type:</b> {row['Charger Type']}<br>
    <b>Cost:</b> ${row['Cost (USD/kWh)']}<br>
    <b>Usage:</b> {row['Usage Stats (avg users/day)']} users/day<br>
    <b>Capacity:</b> {row['Charging Capacity (kW)']} kW<br>
    <b>Operator:</b> {row['Station Operator']}<br>
    <b>Optimal:</b> {"Recommended" if row["Optimal"]==1 else "Existing"}
    """
    color = "green" if row["Optimal"]==1 else "blue"
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
m_heat = folium.Map(location=[df_filtered["Latitude"].mean(), df_filtered["Longitude"].mean()], zoom_start=6)
heat_data = [[row["Latitude"], row["Longitude"], row["Usage Stats (avg users/day)"]] for idx, row in df_filtered.iterrows()]
HeatMap(heat_data, radius=15, max_zoom=13).add_to(m_heat)
st_folium(m_heat, width=800, height=500)

# -------------------------
# 6. Scatter Plot: Cost vs Usage vs Distance
# -------------------------
st.subheader("Cost vs Usage vs Distance")
fig_scatter = px.scatter(
    df_filtered,
    x="Cost (USD/kWh)",
    y="Usage Stats (avg users/day)",
    size="Charging Capacity (kW)",
    color="Distance to City (km)",
    hover_name="Station ID",
    hover_data=["Charger Type","Station Operator","Optimal"],
    color_continuous_scale="Viridis",
    size_max=20,
    title="Cost vs Daily Usage (marker size = capacity, color = distance)"
)
st.plotly_chart(fig_scatter)

# -------------------------
# 7. Charger Type Distribution
# -------------------------
st.subheader("Charger Type Distribution")
fig_charger = px.pie(df_filtered, names="Charger Type", title="Proportion of Charger Types")
st.plotly_chart(fig_charger)

# -------------------------
# 8. Operator Analysis
# -------------------------
st.subheader("Stations per Operator")
operator_count = df_filtered.groupby("Station Operator")["Station ID"].count().reset_index()
operator_count.rename(columns={"Station ID":"Station Count"}, inplace=True)
fig_operator = px.bar(operator_count, x="Station Operator", y="Station Count", color="Station Count", title="Number of Stations per Operator")
st.plotly_chart(fig_operator)

# -------------------------
# 9. Recommended Stations Table
# -------------------------
st.subheader("Recommended / Model-Optimal Stations")
optimal_stations = df_filtered[df_filtered["Optimal"]==1]
st.dataframe(optimal_stations[["Station ID","Address","Charger Type","Usage Stats (avg users/day)","Charging Capacity (kW)"]])

# -------------------------
# 10. Download Filtered Data
# -------------------------
st.subheader("Download Filtered Data")
csv = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download CSV",
    data=csv,
    file_name='ev_stations_filtered.csv',
    mime='text/csv',
)