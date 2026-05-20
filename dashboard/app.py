import json
import math
import os
import warnings
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

# ---------------------------------------------------------------------------
# Data loading (module-level — runs once at startup)
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.environ.get("GAIA_DATA_DIR", Path(__file__).parent.parent / "outputs"))
GPKG_PATH = DATA_DIR / "adm2_flood_results.gpkg"
POINTS_PATH = DATA_DIR / "population_points_flood.csv"

gdf = gpd.read_file(GPKG_PATH)
gdf["pct_affected"] = gdf["epop_ave"] / gdf["pop_tot"] * 100
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    gdf["centroid_lat"] = gdf.geometry.centroid.y
    gdf["centroid_lon"] = gdf.geometry.centroid.x
GEOJSON = json.loads(gdf.to_json())

df_pts = pd.read_csv(POINTS_PATH)

RWI_MIN = math.floor(df_pts["rwi"].min())
RWI_MAX = math.ceil(df_pts["rwi"].max())
RWI_PERCENTILES = {p: float(np.percentile(df_pts["rwi"], p)) for p in [5, 10, 25, 50, 75, 95]}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLORSCALES = ["YlOrRd", "Blues", "Viridis", "RdYlGn_r", "Plasma"]
MAP_CENTER = {"lat": -1.83, "lon": -78.18}
MAP_ZOOM = 6

METRIC_LABELS = {
    "epop_ave": "Avg. Affected Pop.",
    "pop_tot": "Total Population",
    "pct_affected": "% Affected",
}

# ---------------------------------------------------------------------------
# Pre-built RWI histogram figure (static — no callback needed)
# ---------------------------------------------------------------------------

def _build_rwi_histogram():
    counts, bin_edges = np.histogram(df_pts["rwi"], bins=40)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bar_width = bin_edges[1] - bin_edges[0]

    shapes = []
    annotations = []
    label_map = {5: "P5", 10: "P10", 25: "P25", 50: "P50", 75: "P75"}
    for p, label in label_map.items():
        x_val = RWI_PERCENTILES[p]
        shapes.append(
            dict(type="line", x0=x_val, x1=x_val, y0=0, y1=1,
                 yref="paper", line=dict(color="#555", width=1, dash="dot"))
        )
        annotations.append(
            dict(x=x_val, y=1, yref="paper", text=label, showarrow=False,
                 font=dict(size=9, color="#555"), xanchor="center", yanchor="bottom")
        )

    fig = go.Figure(
        go.Bar(x=bin_centers, y=counts, width=bar_width,
               marker_color="#4a90d9", marker_line_width=0)
    )
    fig.update_layout(
        height=120,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        shapes=shapes,
        annotations=annotations,
    )
    return fig


RWI_HISTOGRAM_FIG = _build_rwi_histogram()

# ---------------------------------------------------------------------------
# RWI slider marks at percentiles
# ---------------------------------------------------------------------------

RWI_SLIDER_MARKS = {
    round(RWI_PERCENTILES[p], 2): f"P{p}"
    for p in [5, 25, 50, 75, 95]
}

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
)
server = app.server

# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _left_panel():
    return html.Div(
        className="left-panel",
        children=[
            html.Div("View", className="panel-section-title"),
            dbc.RadioItems(
                id="view-toggle",
                options=[
                    {"label": "Aggregated", "value": "aggregated"},
                    {"label": "Disaggregated", "value": "disaggregated"},
                ],
                value="aggregated",
                inline=False,
            ),

            # Metric selector — aggregated view only
            html.Div(
                id="metric-selector-container",
                children=[
                    html.Hr(style={"margin": "12px 0"}),
                    html.Div("Metric", className="panel-section-title"),
                    dbc.RadioItems(
                        id="metric-selector",
                        options=[
                            {"label": "Avg. Affected Pop.", "value": "epop_ave"},
                            {"label": "Total Population", "value": "pop_tot"},
                            {"label": "% Affected", "value": "pct_affected"},
                        ],
                        value="epop_ave",
                        inline=False,
                    ),
                ],
            ),

            html.Hr(style={"margin": "12px 0"}),
            html.Div("Color Scale", className="panel-section-title"),
            dcc.Dropdown(
                id="color-dropdown",
                options=[{"label": cs, "value": cs} for cs in COLORSCALES],
                value="YlOrRd",
                clearable=False,
            ),

            # RWI section — disaggregated view only
            html.Div(
                id="rwi-section",
                style={"display": "none"},
                children=[
                    html.Hr(style={"margin": "12px 0"}),
                    html.Div("RWI Filter", className="panel-section-title"),
                    dcc.Graph(
                        id="rwi-histogram",
                        figure=RWI_HISTOGRAM_FIG,
                        config={"displayModeBar": False},
                        style={"height": "120px"},
                    ),
                    dcc.RangeSlider(
                        id="rwi-slider",
                        min=RWI_MIN,
                        max=RWI_MAX,
                        step=0.05,
                        value=[RWI_MIN, RWI_MAX],
                        marks=RWI_SLIDER_MARKS,
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ],
            ),
        ],
    )


def _map_section():
    return html.Div(
        className="map-container",
        children=[
            dcc.Graph(
                id="main-map",
                config={"scrollZoom": True, "displayModeBar": False},
                style={"height": "calc(100vh - 60px)"},
            ),
            html.Div(
                id="viewport-counter",
                className="viewport-counter",
                children=[
                    html.Div("—", style={"fontSize": "1.4rem", "fontWeight": "700", "lineHeight": "1.2"}),
                    html.Div("people", style={"fontSize": "0.75rem", "color": "#555"}),
                    html.Div("affected/year", style={"fontSize": "0.75rem", "color": "#555"}),
                    html.Div("in viewport", style={"fontSize": "0.75rem", "color": "#555"}),
                ],
            ),
        ],
    )


def _detail_panel():
    return dbc.Collapse(
        id="detail-collapse",
        is_open=False,
        children=dbc.Card(
            className="detail-panel",
            children=dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.H6("Canton Detail", className="mb-0"), width="auto"),
                    dbc.Col(
                        dbc.Button("Close", id="close-detail-btn", color="secondary",
                                   size="sm", className="float-end"),
                        className="text-end",
                    ),
                ], align="center", className="mb-3"),
                html.Div(id="detail-table"),
            ]),
        ),
    )


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

app.layout = dbc.Container(
    fluid=True,
    style={"padding": 0},
    children=[
        # Header
        html.Div(
            className="header-bar",
            children=html.H5(
                "GAIA — Flood Impact Dashboard | Ecuador",
                className="mb-0",
                style={"fontWeight": "600", "letterSpacing": "0.03em"},
            ),
        ),

        # Body: left panel + map side by side
        html.Div(
            style={"display": "flex", "height": "calc(100vh - 60px)"},
            children=[_left_panel(), _map_section()],
        ),

        # Detail panel below
        _detail_panel(),
    ],
)

# ---------------------------------------------------------------------------
# Callback 1 — toggle left-panel section visibility
# ---------------------------------------------------------------------------

@app.callback(
    Output("metric-selector-container", "style"),
    Output("rwi-section", "style"),
    Input("view-toggle", "value"),
    prevent_initial_call=True,
)
def toggle_panel_sections(view):
    if view == "aggregated":
        return {}, {"display": "none"}
    return {"display": "none"}, {}


# ---------------------------------------------------------------------------
# Callback 2 — update map figure
# ---------------------------------------------------------------------------

@app.callback(
    Output("main-map", "figure"),
    Input("view-toggle", "value"),
    Input("metric-selector", "value"),
    Input("color-dropdown", "value"),
    Input("rwi-slider", "value"),
    prevent_initial_call=False,
)
def update_map(view, metric, colorscale, rwi_range):
    layout = go.Layout(
        uirevision="constant",
        margin=dict(l=0, r=0, t=0, b=0),
        mapbox=dict(
            style="carto-positron",
            center=MAP_CENTER,
            zoom=MAP_ZOOM,
        ),
        paper_bgcolor="white",
    )

    if view == "aggregated":
        hover = (
            "<b>%{customdata[0]}</b><br>"
            "Province: %{customdata[1]}<br>"
            "Total pop: %{customdata[2]:,.0f}<br>"
            "Avg. affected: %{customdata[3]:,.0f}<br>"
            "% Affected: %{customdata[4]:.2f}%"
            "<extra></extra>"
        )
        trace = go.Choroplethmapbox(
            geojson=GEOJSON,
            featureidkey="properties.GID_2",
            locations=gdf["GID_2"],
            z=gdf[metric],
            colorscale=colorscale,
            marker_opacity=0.7,
            marker_line_width=0.5,
            marker_line_color="white",
            hovertemplate=hover,
            customdata=gdf[["NAME_2", "NAME_1", "pop_tot", "epop_ave", "pct_affected"]].values,
            colorbar=dict(thickness=14, len=0.5, x=1.0),
        )
    else:
        rwi_min, rwi_max = rwi_range
        mask = (df_pts["rwi"] >= rwi_min) & (df_pts["rwi"] <= rwi_max)
        pts = df_pts[mask]
        hover = (
            "Avg. affected: %{customdata[0]:.2f}<br>"
            "RWI: %{customdata[1]:.3f}<br>"
            "Population: %{customdata[2]:.2f}"
            "<extra></extra>"
        )
        trace = go.Scattermapbox(
            lat=pts["latitude"],
            lon=pts["longitude"],
            mode="markers",
            marker=dict(
                size=4,
                opacity=0.6,
                color=pts["epop_ave"],
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(thickness=14, len=0.5, x=1.0),
            ),
            hovertemplate=hover,
            customdata=pts[["epop_ave", "rwi", "population"]].values,
        )

    return go.Figure(data=[trace], layout=layout)


# ---------------------------------------------------------------------------
# Callback 3 — viewport counter
# ---------------------------------------------------------------------------

@app.callback(
    Output("viewport-counter", "children"),
    Input("main-map", "relayoutData"),
    Input("view-toggle", "value"),
    Input("rwi-slider", "value"),
    prevent_initial_call=True,
)
def update_viewport_counter(relayout_data, view, rwi_range):
    total = None

    if relayout_data and "mapbox._derived" in relayout_data:
        coords = relayout_data["mapbox._derived"]["coordinates"]
        lon_min = min(c[0] for c in coords)
        lon_max = max(c[0] for c in coords)
        lat_min = min(c[1] for c in coords)
        lat_max = max(c[1] for c in coords)

        if view == "aggregated":
            mask = (
                (gdf["centroid_lon"] >= lon_min) & (gdf["centroid_lon"] <= lon_max) &
                (gdf["centroid_lat"] >= lat_min) & (gdf["centroid_lat"] <= lat_max)
            )
            total = gdf.loc[mask, "epop_ave"].sum()
        else:
            rwi_min, rwi_max = rwi_range
            mask = (
                (df_pts["longitude"] >= lon_min) & (df_pts["longitude"] <= lon_max) &
                (df_pts["latitude"] >= lat_min) & (df_pts["latitude"] <= lat_max) &
                (df_pts["rwi"] >= rwi_min) & (df_pts["rwi"] <= rwi_max)
            )
            total = df_pts.loc[mask, "epop_ave"].sum()

    if total is None:
        value_text = "—"
    else:
        value_text = f"{total:,.0f}"

    return [
        html.Div(value_text, style={"fontSize": "1.4rem", "fontWeight": "700", "lineHeight": "1.2"}),
        html.Div("people", style={"fontSize": "0.75rem", "color": "#555"}),
        html.Div("affected/year", style={"fontSize": "0.75rem", "color": "#555"}),
        html.Div("in viewport", style={"fontSize": "0.75rem", "color": "#555"}),
    ]


# ---------------------------------------------------------------------------
# Callback 4 — show detail panel on canton click
# ---------------------------------------------------------------------------

@app.callback(
    Output("detail-collapse", "is_open"),
    Output("detail-table", "children"),
    Input("main-map", "clickData"),
    State("view-toggle", "value"),
    prevent_initial_call=True,
)
def show_detail(click_data, view):
    if click_data is None or view != "aggregated":
        return False, []

    point = click_data["points"][0]
    gid2 = point.get("location")
    if gid2 is None:
        return False, []

    row = gdf[gdf["GID_2"] == gid2]
    if row.empty:
        return False, []

    row = row.iloc[0]
    display_cols = [c for c in gdf.columns if c != "geometry"]

    rows = []
    for col in display_cols:
        val = row[col]
        if isinstance(val, float):
            formatted = f"{val:,.2f}"
        elif isinstance(val, (int, np.integer)):
            formatted = f"{val:,}"
        else:
            formatted = str(val)
        rows.append(html.Tr([html.Td(col, style={"fontWeight": "500"}), html.Td(formatted)]))

    table = dbc.Table(
        [html.Thead(html.Tr([html.Th("Field"), html.Th("Value")])),
         html.Tbody(rows)],
        bordered=True, hover=True, size="sm", responsive=True,
    )
    return True, table


# ---------------------------------------------------------------------------
# Callback 5 — close detail panel
# ---------------------------------------------------------------------------

@app.callback(
    Output("detail-collapse", "is_open", allow_duplicate=True),
    Input("close-detail-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_detail(_n):
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
