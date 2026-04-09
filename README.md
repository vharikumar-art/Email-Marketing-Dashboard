# Email Dashboard API

A robust FastAPI-based backend for managing email data, clients, manuscripts, orders, and payments. The system features a multi-tier Role-Based Access Control (RBAC) system with Super Admin, Admin, and User roles.

## Features

- **Multi-tier RBAC**: 
  - **Super Admin**: Highest level of authority (max 2). Can manage Admins and Users.
  - **Admin**: Can manage regular Users.
  - **User**: Standard authenticated access.
- **Entity Management**: CRUD operations for Clients, Manuscripts, Orders, and Payments.
- **Secure Authentication**: JWT-based authentication with bcrypt password hashing.
- **2FA / OTP Verification**: Required only for Admin and Manager roles.
- **Database**: MongoDB for flexible data storage.

## Project Structure

- `main.py`: Main application entry point and API endpoints.
- `auth.py`: Authentication logic and role-based dependencies.
- `schemas.py`: Pydantic models for request/response validation.
- `database.py`: MongoDB connection and collection definitions (including `otps`).
- `config.py`: Environment variable management.
- `.env`: API configuration and secrets.
- `login_system_documentation.txt`: Detailed explanation of the RBAC system.
- `manual_testing_guide.txt`: Step-by-step guide for verifying API endpoints.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd "Email Dashboard"
   ```

2. **Set up virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Configure Environment**:
   Create a `.env` file in the root directory (use `.env.example` as a template if available).
   ```env
   MONGO_URI=your_mongodb_uri
   DB_NAME=your_db_name
   SECRET_KEY=your_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=120
   ```

## Getting Started

1. **Initialize the first Super Admin**:
   The system starts with no users. Use the bootstrap endpoint to create the first Super Admin:
   `POST /init-super-admin`

2. **Run the server**:
   ```bash
   uv run uvicorn main:app --reload
   ```

3. **Access API Documentation**:
   Once the server is running, visit `http://127.0.0.1:8000/docs` for the interactive Swagger documentation.

## Manual Testing

For detailed instructions on how to test each endpoint, refer to [manual_testing_guide.txt](manual_testing_guide.txt).
