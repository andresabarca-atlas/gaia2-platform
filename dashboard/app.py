import json
import os
import warnings
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

# ---------------------------------------------------------------------------
# Data loading (module-level — runs once at startup)
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.environ.get("GAIA_DATA_DIR", Path(__file__).parent.parent / "outputs"))
GPKG_PATH = DATA_DIR / "adm2_flood_results.gpkg"

gdf = gpd.read_file(GPKG_PATH)
gdf["pct_affected"] = gdf["epop_ave"] / gdf["pop_tot"] * 100

_GPKG_COLS_NEEDED = [
    "GID_2", "NAME_1", "NAME_2", "pop_tot", "epop_ave", "pct_affected",
    "geometry",
]
gdf = gdf[[c for c in _GPKG_COLS_NEEDED if c in gdf.columns]]

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    gdf["centroid_lat"] = gdf.geometry.centroid.y
    gdf["centroid_lon"] = gdf.geometry.centroid.x

gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.001, preserve_topology=True)
GEOJSON = json.loads(gdf.to_json())
gdf = gdf.drop(columns=["geometry"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLORSCALES = ["YlOrRd", "Blues", "Viridis", "RdYlGn_r", "Plasma"]
MAP_CENTER = {"lat": -35.0, "lon": -71.0}
MAP_ZOOM = 4

METRIC_LABELS = {
    "pop_tot":      "Total Population",
    "epop_ave":     "Avg. Affected Pop.",
    "pct_affected": "% Affected",
}

VIEWPORT_CONFIG = {
    "pop_tot":      {"col": "pop_tot",  "label": "people\nin viewport"},
    "epop_ave":     {"col": "epop_ave", "label": "people affected/year\nin viewport"},
    "pct_affected": {"col": None,       "label": None},
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
            html.Div("Metric", className="panel-section-title"),
            dbc.RadioItems(
                id="metric-selector",
                options=[
                    {"label": "Total population",    "value": "pop_tot"},
                    {"label": "Affected population", "value": "epop_ave"},
                    {"label": "% Affected",          "value": "pct_affected"},
                ],
                value="epop_ave",
                inline=False,
            ),

            html.Hr(style={"margin": "12px 0"}),
            html.Div("Color Scale", className="panel-section-title"),
            dcc.Dropdown(
                id="color-dropdown",
                options=[{"label": cs, "value": cs} for cs in COLORSCALES],
                value="YlOrRd",
                clearable=False,
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
                    dbc.Col(html.H6("District Detail", className="mb-0"), width="auto"),
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
                "GAIA — Flood Impact Dashboard | Chile",
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
# Callback 1 — update map figure
# ---------------------------------------------------------------------------

@app.callback(
    Output("main-map", "figure"),
    Input("metric-selector", "value"),
    Input("color-dropdown", "value"),
    prevent_initial_call=False,
)
def update_map(metric, colorscale):
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

    hover = (
        "<b>%{customdata[0]}</b><br>"
        "%{customdata[1]}<br>"
        "Total pop: %{customdata[2]:,.0f}<br>"
        "Affected: %{customdata[3]:,.0f}<br>"
        "% Affected: %{customdata[4]:.2f}%<br>"
        "<extra></extra>"
    )
    customdata_cols = ["NAME_2", "NAME_1", "pop_tot", "epop_ave", "pct_affected"]
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
        customdata=gdf[customdata_cols].values,
        colorbar=dict(thickness=14, len=0.5, x=1.0),
    )

    return go.Figure(data=[trace], layout=layout)


# ---------------------------------------------------------------------------
# Callback 2 — viewport counter
# ---------------------------------------------------------------------------

@app.callback(
    Output("viewport-counter", "children"),
    Input("main-map", "relayoutData"),
    Input("metric-selector", "value"),
    prevent_initial_call=True,
)
def update_viewport_counter(relayout_data, selected_metric):
    cfg = VIEWPORT_CONFIG.get(selected_metric, VIEWPORT_CONFIG["epop_ave"])
    if cfg["col"] is None or cfg["col"] not in gdf.columns:
        return [html.Div("—", style={"fontSize": "1.4rem", "fontWeight": "700",
                                     "lineHeight": "1.2", "color": "#adb5bd"})]

    total = None

    if relayout_data and "mapbox._derived" in relayout_data:
        coords = relayout_data["mapbox._derived"]["coordinates"]
        lon_min = min(c[0] for c in coords)
        lon_max = max(c[0] for c in coords)
        lat_min = min(c[1] for c in coords)
        lat_max = max(c[1] for c in coords)

        mask = (
            (gdf["centroid_lon"] >= lon_min) & (gdf["centroid_lon"] <= lon_max) &
            (gdf["centroid_lat"] >= lat_min) & (gdf["centroid_lat"] <= lat_max)
        )
        total = gdf.loc[mask, cfg["col"]].sum()

    value_text = f"{total:,.0f}" if total is not None else "—"
    label_lines = cfg["label"].split("\n")

    return [
        html.Div(value_text, style={"fontSize": "1.4rem", "fontWeight": "700", "lineHeight": "1.2"}),
        *[html.Div(line, style={"fontSize": "0.75rem", "color": "#555"}) for line in label_lines],
    ]


# ---------------------------------------------------------------------------
# Callback 3 — show detail panel on district click
# ---------------------------------------------------------------------------

@app.callback(
    Output("detail-collapse", "is_open"),
    Output("detail-table", "children"),
    Input("main-map", "clickData"),
    prevent_initial_call=True,
)
def show_detail(click_data):
    if click_data is None:
        return False, []

    point = click_data["points"][0]
    gid2 = point.get("location")
    if gid2 is None:
        return False, []

    row = gdf[gdf["GID_2"] == gid2]
    if row.empty:
        return False, []

    row = row.iloc[0]
    display_cols = [c for c in gdf.columns if c not in ("centroid_lat", "centroid_lon")]

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
# Callback 4 — close detail panel
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
