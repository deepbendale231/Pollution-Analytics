from __future__ import annotations

from datetime import datetime

import folium

CATEGORY_COLORS = {
    "Good": "green",
    "Satisfactory": "yellow",
    "Moderate": "orange",
    "Poor": "red",
    "Very Poor": "purple",
    "Severe": "darkred",
}


def create_aqi_map(city_aqi_dict: dict):
    india_map = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="cartodbpositron")

    for city_name, payload in city_aqi_dict.items():
        if not isinstance(payload, dict):
            continue

        aqi = float(payload.get("aqi", 0.0) or 0.0)
        lat = payload.get("lat")
        lon = payload.get("lon")
        category = str(payload.get("category", "Moderate"))
        last_updated = payload.get("last_updated")

        if lat is None or lon is None:
            continue

        color = CATEGORY_COLORS.get(category, "gray")
        radius = max(5, min(30, aqi / 15.0))

        if isinstance(last_updated, datetime):
            updated_text = last_updated.strftime("%Y-%m-%d %H:%M")
        else:
            updated_text = str(last_updated) if last_updated is not None else "N/A"

        popup_html = (
            f"<b>{city_name}</b><br>"
            f"AQI: {aqi:.1f}<br>"
            f"Category: {category}<br>"
            f"Last updated: {updated_text}"
        )

        folium.CircleMarker(
            location=[float(lat), float(lon)],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=2,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=city_name,
        ).add_to(india_map)

    legend_html = """
    <div style="
        position: fixed;
        bottom: 30px;
        right: 20px;
        z-index: 9999;
        background: white;
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        font-size: 13px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    ">
        <div style="font-weight:bold; margin-bottom:6px;">AQI Category</div>
        <div><span style="color:green;">●</span> Good</div>
        <div><span style="color:yellow;">●</span> Satisfactory</div>
        <div><span style="color:orange;">●</span> Moderate</div>
        <div><span style="color:red;">●</span> Poor</div>
        <div><span style="color:purple;">●</span> Very Poor</div>
        <div><span style="color:darkred;">●</span> Severe</div>
    </div>
    """
    india_map.get_root().html.add_child(folium.Element(legend_html))

    return india_map
