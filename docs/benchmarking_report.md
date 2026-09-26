# Benchmarking Report

This report outlines the baseline performance metrics of the Dovetec Enterprises Web Platform endpoints.

## Infrastructure

- **Environment**: Local Development
- **Database**: SQLite3
- **Server**: Django Development Server (`manage.py runserver`)
- **Methodology**: 10 sequential GET requests per tested endpoint.
- **Date**: 2026-04-03

## Results

### 1. `/` (Homepage)
- **Status**: `200 OK`
- **Average Latency**: `48.54 ms`
- **Max Latency**: `101.43 ms` (Initial cold start/template caching)
- **Min Latency**: `25.87 ms`

### 2. `/shop/` (Product Listing)
- **Status**: `200 OK`
- **Average Latency**: `41.27 ms`
- **Max Latency**: `50.48 ms`
- **Min Latency**: `27.57 ms`

### 3. `/about/` (Static Template)
- **Status**: `200 OK`
- **Average Latency**: `35.73 ms`
- **Max Latency**: `51.42 ms`
- **Min Latency**: `26.82 ms`

## Analysis

The application performs very cleanly under minimal load. The first request to a server page generally incurs a ~50ms overhead as templates are compiled and read from disk, dropping to ~25ms-35ms once cached in memory within the server cycle.

### Optimization Recommendations

1. **Production Caching**: Since these routes are read-heavy, applying page caching (`@cache_page` or utilizing Vercel's Edge Network) will drastically reduce response times for static templates like `/about/`.
2. **Database Constraints**: The `/shop/` page queries are fast in SQLite, but as the `Product` catalog grows, ensure `.select_related()` and `.prefetch_related()` are implemented in the `shop` ORM queries (specifically around the `Category` foreign key mapping) to prevent N+1 query bottlenecks on PostgreSQL.
