# GAIA 2.0

**Global Assessment of Impacts and Amenazas** — an open methodology and platform for estimating the annual average impact of natural hazards (floods, earthquakes, wind, etc.) on people, weighted by socioeconomic characteristics.

> Pilot: Ecuador, flood hazard.

---

## What it does

For each hazard and country, GAIA 2.0:
1. Builds a population exposure layer at 100m resolution from open population rasters
2. Assigns socioeconomic vulnerability (Relative Wealth Index) to each population point
3. Samples hazard intensity at each point across multiple return periods
4. Integrates across return periods to compute the **Annual Average affected Population (AAP)**
5. Aggregates results to administrative boundaries for dashboard consumption

---

## Repository structure

```
gaia2/
├── run_floods_ecuador.py       # Main script: Ecuador flood analysis
│
├── methodology/
│   ├── common/
│   │   └── exposure.py         # Population raster → points, RWI assignment
│   └── floods/
│       └── impact.py           # Flood-specific exposure sampling and AAP
│
├── config/
│   └── settings.yaml           # All configurable parameters and paths
│
├── data/
│   └── README.md               # Data sources, licenses, download instructions
│
└── outputs/
    └── README.md               # Output schema (column definitions, CRS, format)
```

---

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/your-org/gaia2.git
cd gaia2
pip install -r requirements.txt
```

---

## Data setup

Data files are **not included** in this repository. See [`data/README.md`](data/README.md) for download instructions and expected directory layout.

---

## Running the analysis

1. Download all required data (see `data/README.md`)
2. Edit `config/settings.yaml` to point to your local data paths
3. Run:

```bash
python run_floods_ecuador.py
# or with a custom config:
python run_floods_ecuador.py --config config/settings.yaml
```

Outputs are written to the directory specified in `config/settings.yaml` (`outputs/` by default).

---

## Team

| Name    | Role                        |
|---------|-----------------------------|
| [You]   | Lead developer, methodology |
| Kenneth | Methodology (earthquakes)   |
| Walter  | GIS dashboard               |

---

## Contributing

- Work on feature branches, never directly on `main`
- One pull request per feature or hazard module
- Document any new data source in `data/README.md`
- Document any output column change in `outputs/README.md`

---

## License

Code: [MIT License](LICENSE)
Methodology: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
