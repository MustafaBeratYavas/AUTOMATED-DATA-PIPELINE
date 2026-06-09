<div align="center">
  <h1>AUTOMATED DATA PIPELINE</h1>
  <p>
    <strong>Team Members:</strong> Mustafa Berat Yavaş 21058023, Muhammed Kerem Demirbent 21058007 | TEAM 5 - MTM4692<br>
    <strong>Presentation:</strong> <a href="https://drive.google.com/file/d/1uS9x9CMNE9rITLDWj6M9NuajEdZ6dUfH/view?usp=drivesdk">View Presentation</a>
  </p>

  <p>
    <a href="https://www.python.org/">
      <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&amp;logoColor=white" alt="Python" />
    </a>
    <a href="https://seleniumbase.io/">
      <img src="https://img.shields.io/badge/SeleniumBase-4.46%2B-00A98F?logo=selenium&amp;logoColor=white" alt="SeleniumBase" />
    </a>
    <a href="https://flask.palletsprojects.com/">
      <img src="https://img.shields.io/badge/Flask-3.1%2B-000000?logo=flask&amp;logoColor=white" alt="Flask" />
    </a>
    <a href="./LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
    </a>
  </p>
</div>

This repository contains an end-to-end marketplace data pipeline for collecting, normalizing, storing, and visualizing competitive e-commerce pricing data from Akakce. The system uses SeleniumBase-powered browser automation to resolve product pages from a queue of target product codes, validates matched product detail pages before extraction, persists seller-level price snapshots into SQLite, and exposes the collected data through a local Flask dashboard powered by Apache ECharts.

The project is organized around clear runtime boundaries: configuration-driven selectors and delays, a queue-oriented batch processor with retry handling, dedicated services for search, detail parsing, seller extraction, and persistence, plus dashboard services that transform stored rows into marketplace competitiveness, SKU price dispersion, and category coverage views. Selector usage reports are produced during scraper execution so changes in the target marketplace layout can be diagnosed from runtime evidence instead of guesswork.

<details>
<summary><b>Click to expand project structure details</b></summary>

```text
.
|-- .github
|   `-- workflows
|       `-- ci.yml                        # Lint, test, coverage, and type-check workflow
|-- config
|   `-- settings.yaml                     # Runtime configuration for scraping, browser, selectors, and paths
|-- database
|   |-- .gitkeep                          # Keeps the database directory available in fresh clones
|   `-- scraper.db                        # SQLite database for target queue and scraped product rows
|-- logs
|   `-- .gitkeep                          # Keeps the log directory available in fresh clones
|-- src
|   |-- core                              # Configuration, logging, exceptions, and selector usage reporting
|   |-- engine                            # Browser lifecycle and queue-driven batch orchestration
|   |-- models                            # Product DTOs and database row conversion logic
|   |-- services                          # Search, detail scraping, seller extraction, and SQLite access
|   |-- tasks                             # CLI helpers for Chrome profile creation and target seeding
|   |-- utils                             # String normalization, price parsing, and timing helpers
|   |-- web                               # Flask dashboard backend, templates, static assets, and chart data services
|   |-- definitions.py                    # Repository path definitions
|   `-- main.py                           # Scraping pipeline entrypoint
|-- tests
|   |-- integration                       # Browser-facing smoke tests
|   |-- unit                              # Fast unit tests for services, engine, tasks, models, and dashboard
|   |-- conftest.py                       # Shared pytest fixtures and mocks
|   `-- __init__.py
|-- .gitignore                            # Git exclusions for caches, local profiles, logs, and generated files
|-- LICENSE                               # MIT license terms
|-- README.md                             # Project documentation
|-- product_codes.txt                     # Seed list of target product codes
`-- pyproject.toml                        # Project metadata, dependencies, CLI scripts, and tool configuration
```

</details>

<details>
<summary><b>Click to expand technology stack details</b></summary>

| Layer | Technology | Role in the Project |
|:---|:---|:---|
| **Application Runtime** | Python 3.11+ | Main runtime for the scraping pipeline, dashboard backend, CLI commands, and service orchestration |
| **Browser Automation** | SeleniumBase 4.46.5, Selenium 4.40.0 | Chrome automation for Akakce navigation, search interaction, product page loading, and DOM extraction |
| **Configuration** | PyYAML 6.0.3 | Loads `config/settings.yaml` for URLs, browser options, scraping policy, delays, selectors, and local paths |
| **Queue & Persistence** | SQLite3 | Stores queue state, legacy scrape snapshots, normalized dimensions, price observations, SQL views, and status history |
| **Scraping Services** | Python service classes | Separates search resolution, product detail parsing, seller extraction, retry flow, and database writes |
| **Dashboard Backend** | Flask 3.1.2 | Serves the local dashboard, `/health`, and `/api/dashboard-data` endpoints |
| **Dashboard Frontend** | HTML, CSS, JavaScript, Apache ECharts | Renders summary metrics, marketplace competitiveness, SKU price spread, and category coverage charts |
| **CLI Entrypoints** | `pyproject.toml` scripts | Provides `adp`, `adp-scrape`, `adp-seed-targets`, `adp-create-profile`, and `adp-dashboard` commands |
| **Testing** | Pytest, unittest, pytest-cov | Covers queue handling, scraping services, database behavior, dashboard analytics, routes, and browser smoke tests |
| **Code Quality** | Ruff, Pyrefly, GitHub Actions | Runs linting, type analysis, tests, and coverage checks in local development and CI |

</details>

## Table of Contents

- [Database Design & SQL Implementation](#database-design--sql-implementation)
- [Executive Conclusion & Business Impact](#executive-conclusion--business-impact)
- [Dependencies](#dependencies)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Limitations & Disclaimers](#limitations--disclaimers)
- [License](#license)

## Database Design & SQL Implementation

The application uses SQLite as both the scraping queue store and the local pricing warehouse. The schema keeps the original append-only `products` table for backward-compatible dashboard reads, while also maintaining a normalized relational model for SQL reporting, joins, aggregate queries, and auditability.

| Table / View | Purpose | Key SQL Concepts |
|:---|:---|:---|
| `target_products` | Queue of product codes waiting to be scraped | Primary key, unique constraint, queue status updates |
| `target_status_history` | Audit trail for target status transitions | Foreign key, trigger-populated history |
| `products` | Append-only scraped offer snapshots used by the dashboard | Primary key, insert statements, historical rows |
| `product_catalog` | Product dimension table keyed by product code | Primary key, unique constraint, upsert behavior |
| `marketplaces` | Marketplace/seller dimension table | Primary key, unique marketplace names |
| `price_observations` | Normalized fact table for seller-level price observations | Foreign keys to products, product catalog, and marketplaces |
| `v_product_offer_history` | Joined product, marketplace, and price history | SQL view, joins |
| `v_marketplace_price_summary` | Marketplace-level listing and price summary | SQL view, `GROUP BY`, `COUNT`, `MIN`, `AVG`, `MAX` |
| `v_product_price_spread` | Product-level marketplace price spread | SQL view, aggregate functions |

Core relationships:

- `price_observations.product_id` references `product_catalog.id`.
- `price_observations.marketplace_id` references `marketplaces.id`.
- `price_observations.legacy_product_id` references `products.id`.
- `target_status_history.target_product_id` references `target_products.id`.

The scraping flow writes each extracted offer into `products` and mirrors the same row into the normalized schema inside the same database transaction. This keeps the existing dashboard stable while enabling SQL-focused demonstrations with joins, aggregate views, foreign keys, and trigger-backed queue history.

## Executive Conclusion & Business Impact

This project turns marketplace product pages into a structured local dataset that can be used to monitor competitive pricing, seller availability, and category-level listing coverage. Instead of relying on manual checks or one-off browser searches, the pipeline creates a repeatable workflow: seed target product codes, process them through a controlled scraping queue, persist seller-level price snapshots, and review the results through an interactive dashboard.

From a business perspective, the main value is operational visibility. The dashboard helps identify which marketplaces are consistently price-competitive, which SKUs have the widest seller price gaps, and where category coverage is concentrated or missing. From an engineering perspective, the queue model, retry handling, configuration-driven selectors, and selector usage reports make the system easier to maintain when marketplace pages change.

- **Competitive Price Visibility:** Seller-level price rows make it possible to compare marketplace offers for the same SKU and identify the lowest-price sellers at a point in time.
- **SKU Price Dispersion:** The dashboard highlights products with the widest gap between minimum, median, and maximum marketplace prices, helping surface SKUs that require closer commercial review.
- **Marketplace Coverage:** Category and marketplace heatmaps show where listing density is strong or weak, making coverage gaps easier to spot.
- **Reliable Batch Processing:** Target products are processed through a SQLite-backed queue with retry and failure states, reducing the risk of losing progress during scraper or browser errors.
- **Maintainable Scraping Operations:** Centralized selectors, configurable delays, and selector usage reports help diagnose DOM changes without scattering scraping assumptions across the codebase.

## Dependencies

To ensure reproducibility and isolate project dependencies, use a virtual environment before installing the package. The project dependencies are declared in `pyproject.toml`, which is the source of truth for both runtime and development installs.

### Step 1 - Create Virtual Environment:

```bash
python -m venv .venv
```

### Step 2 - Activate Virtual Environment:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Step 3 - Upgrade pip:

```bash
python -m pip install --upgrade pip
```

### Step 4 - Install Project Dependencies:

Install only the runtime dependencies:

```bash
python -m pip install -e .
```

Install the development dependencies for testing, linting, coverage, and type analysis:

```bash
python -m pip install -e ".[dev]"
```

*Runtime dependencies: `seleniumbase`, `selenium`, `PyYAML`, `Flask`.*

*Development dependencies: `pytest`, `pytest-cov`, `ruff`, `pyrefly`.*

## Quickstart

### Prerequisites

* **Python:** Python 3.11 or later available on your `PATH`.
* **Google Chrome:** A recent stable version of Google Chrome is required for SeleniumBase browser automation.

### 1. Web Extraction

The web extraction workflow prepares a reusable Chrome profile, loads product
codes from `product_codes.txt`, and executes the scraping pipeline. Validated
product details and seller-level price snapshots are persisted into
`database/scraper.db`.

#### Step 1 - Create Browser Profile:

```bash
python -m src.tasks.create_profile
```

#### Step 2 - Seed Product Targets:

```bash
python -m src.tasks.seed_targets --file product_codes.txt
```

#### Step 3 - Run Scraping Pipeline:

```bash
python -m src.main
```

### 2. Local Dashboard

After product snapshots are available, start the local dashboard to inspect
summary metrics, marketplace competitiveness, SKU price dispersion, and
category coverage charts.

```bash
python -m src.web.app
```

The dashboard runs at:

```text
http://127.0.0.1:5000
```

### 3. Quality Checks

Run the unit test suite before changing scraper behavior, persistence logic, or
dashboard calculations.

```bash
python -m pytest
```

## Configuration

Runtime behavior is centralized in [`config/settings.yaml`](./config/settings.yaml). The scraper reads this file through the `Config` service, so target URLs, browser settings, queue behavior, timing delays, DOM selectors, database location, and log output can be adjusted without changing the service code.

The most important sections are:

| Section | Key Parameters | Description |
|:---|:---|:---|
| `app` | `name`, `version`, `env` | Application metadata used during startup logging and environment identification |
| `urls` | `base`, `search` | Akakce base URL and Google fallback search URL |
| `paths` | `database`, `logs_dir` | Local SQLite database path and log directory |
| `observability.selector_usage` | `enabled`, `output_dir`, `report_prefix` | Selector usage report settings written after scraper execution |
| `browser` | `headless`, `start_maximized`, `page_load_timeout`, `implicit_wait`, `user_agent`, `user_data_dir`, `profile_name` | SeleniumBase Chrome runtime and persistent profile settings |
| `scraping` | `retries`, `search_engine_fallback`, `google_query_format`, `html_source_count_threshold`, `search_input_validation_attempts`, `detail_delay_probability`, `no_result_terms` | Retry limits, fallback behavior, search validation, and no-result detection rules |
| `delays` | `typing`, `pre_enter`, `post_search`, `page_switch`, `google_switch`, `base_navigation`, `post_detail` | Randomized wait ranges used to pace browser interactions and page transitions |
| `selectors.search_*` | `search_input`, `search_result_item`, `search_result_title`, `search_no_result` | Akakce search page selectors |
| `selectors.product.*` | `title`, `category_crumb`, `price`, `sellers_list`, `sellers_list_item`, `sellers_alt_item`, `seller_price`, `seller_name_wrapper` | Product detail and seller-list selectors |
| `selectors.google.*` | `result_link` | Google fallback result link selector |

When Akakce changes its page structure, update the relevant selector values in `settings.yaml` first. After the next scraping execution, inspect the generated selector usage report under the configured log directory to see which selectors were queried, matched, missed, or left unused.

## Limitations & Disclaimers

> **Important:** This section defines the operational, data-quality, and compliance boundaries of the marketplace metrics produced by this project.

### Responsible Automation and Access Boundaries

- **Educational and portfolio scope:** This project is intended for academic research, data engineering practice, and portfolio demonstration. It should be used responsibly and in accordance with applicable website policies, Terms of Service, and local regulations.
- **No access-control bypassing:** Browser automation, persistent profiles, randomized delays, and CAPTCHA-related browser hooks must not be treated as mechanisms for bypassing authentication, rate limits, anti-bot systems, or other access restrictions.
- **Browser session sensitivity:** The persistent Chrome profile configured through `.browser_profile` may contain cookies, preferences, or session state. Treat it as local runtime data and do not commit, publish, or share it.
- **Execution reliability:** Automated browser workflows can encounter CAPTCHAs, temporary blocks, rate limits, expired sessions, layout experiments, slow rendering, or network instability. Retry handling and randomized delays improve resilience, but they do not guarantee uninterrupted extraction.

### Data Scope and Snapshot Interpretation

- **Point-in-time observations:** Prices, seller names, product availability, and category signals are captured as snapshots from the moment of scraping. They should not be interpreted as live market truth after the run has completed.
- **Seed-list coverage:** The collected dataset is only as broad as `product_codes.txt` and the successfully processed queue records. Category-level or marketplace-level conclusions should not be generalized beyond the active target list without expanding and validating the seed universe.
- **Local database context:** `database/scraper.db` is a local SQLite database used by both the scraper and dashboard. Treat its contents as environment-specific runtime data unless you intentionally version a reviewed snapshot.
- **Incomplete market visibility:** The pipeline stores visible offers that can be extracted from the rendered product page. Listings may still be missed because of dynamic rendering, regional availability, failed retries, hidden seller data, unavailable price signals, or page instability.

### Product Matching and Extraction Limitations

- **SKU validation dependency:** The scraper validates product detail pages against the requested product code before extracting seller rows. Close variants or unrelated fallback results can still appear during search, and unverified matches should be reviewed through logs and database output.
- **Selector and layout dependency:** Extraction depends on Akakce's current page structure and the selectors configured in `config/settings.yaml`. Layout changes, class-name changes, lazy loading, or selector drift may require configuration updates or extraction logic changes.
- **Seller identity normalization:** Seller names are captured from visible page text or image metadata when available. Marketplace naming differences, missing labels, or layout variants can affect seller consistency.
- **Price signal quality:** Wide spreads, unusually high prices, zero values, or missing prices are review signals, not automatic proof of scraper failure. They may reflect low stock, reseller behavior, bundles, stale listings, variant ambiguity, or real marketplace fragmentation.

### Intended Use

- **Decision-support use case:** The project supports pricing intelligence exploration, data-quality review, and marketplace monitoring workflows. It should not be used for automated commercial decision-making without human validation.
- **Manual review requirement:** High-impact conclusions should be checked against fresh scraper runs, source product pages, application logs, selector usage reports, and the dashboard output.
- **Configuration responsibility:** Users who change target products, selectors, browser settings, persistence rules, or dashboard logic should rerun the test suite and inspect generated runtime outputs before relying on the resulting metrics.

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for full terms.

Copyright © 2026 **Mustafa Berat Yavaş** & **Muhammed Kerem Demirbent**
