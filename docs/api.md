# API Documentation

While the bulk of the Dovetec Enterprises platform utilizes Server-Side Rendered (SSR) Django Templates, specific API endpoints have been exposed using Django REST Framework for seamless client integrations.

## Base URL
Local: `http://127.0.0.1:8000/api/`
Production: `https://dovetecenterprises.site/api/`

## Authentication Endpoints

These endpoints are housed under the `home` app routing logic (`home/urls_api.py`).

### 1. User Registration
Creates a new user profile.
- **Endpoint**: `/api/register/`
- **Method**: `POST`
- **Payload** (Expected JSON):
  ```json
  {
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "password": "securepassword123"
  }
  ```
- **Responses**:
  - `201 Created`: User successfully created.
  - `400 Bad Request`: Validation errors on required fields or duplicate email.

### 2. User Login
Authenticates an existing user and retrieves a session or token details.
- **Endpoint**: `/api/login/`
- **Method**: `POST`
- **Payload** (Expected JSON):
  ```json
  {
      "email": "user@example.com",
      "password": "securepassword123"
  }
  ```
- **Responses**:
  - `200 OK`: Context details/tokens if utilizing JWT or DRF session keys.
  - `401 Unauthorized`: Invalid credentials.

*(Note: API capabilities will scale continuously as more apps like `shop` introduce React-driven UI modules. These endpoints are subject to change.)*
