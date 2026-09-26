# Dovetec Enterprises System Architecture

This document describes the high-level architecture of the Dovetec Enterprises Web Platform.

## Overview

The platform uses a monolithic architecture built upon the Django web framework. It follows the standard MVT (Model-View-Template) pattern, utilizing Django Templates for server-side rendering while also exposing specific endpoints via Django REST Framework (DRF) for React/client-side integrations where necessary.

## Apps and Responsibilities

Our Django project (`dovetecenterprises`) delegates logic into modular applications:

### 1. `home` App
The `home` app acts as the core of user interactions, authentication, and content creation.
- **User Management**: Custom `User` model, `Profile` enhancements, OTP verifications.
- **Blogging Engine**: Models like `Article`, `Tag`, `Comment`, `Reply`, `Like`, `Dislike` facilitate full-fledged content creation. Integration with `django-froala-editor` allows rich text editing.
- **Newsletters & Jobs**: Houses logic for Subscriptions, Newsletters (email campaigns), and Job postings.

### 2. `shop` App
Handles the E-commerce logic.
- **Catalog**: `Product`, `Category`, `Keyword` for faceted search.
- **Checkout Flow**: `Cart`, `CartItem`, `Order`, `Payment`. Manages stock constraints and processing logic mockups.

### 3. `adverts` App
Manages localized lead generation and specific advertisement endpoints.

### 4. `community` App
Structures the forums and general discussions for users on the platform.

### 5. `app` App
General static routing, landing pages, and auxiliary app components not tied strictly to the domain objects above.

## Data Layer
- **SQLite3** is used for internal/local development.
- **PostgreSQL** is correctly abstracted using `dj-database-url` in production configurations.
- Media handling falls back to standard filesystem upload (`/media/` and `/staticfiles/`), but typically maps onto cloud storage configurations via Vercel during production.

## Deployment Strategy
The main configurations reside in `vercel.json` pointing Vercel to `wsgi.py`. The project uses the `@vercel/python` builder runtime.

## Schema Highlights
- Most key models (`Article`, `Comment`, `Reply`, `Profile`) use an override to auto-generate an MD5 `hashed_id` for use in obfuscated URLs.
- Soft-deletes are heavily used (e.g., `is_deleted` on Comments) to preserve historical context.
