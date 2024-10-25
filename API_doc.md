# API Documentation

## Table of Contents
- [Endpoints](#endpoints)
  - [1. Create Org](#1-create-organization)
  - [2. Sync User](#2-sync-user)
  - [3. User Profile](#3-user-profile)
  - [4. Chat View](#4-chat)

## Authentication
Most endpoints require authentication using a JWT token in the Authorization header:
```
Authorization: Bearer <JWT_TOKEN>
```

## Endpoints

### 1. Create Organization
This API creates a new organisation.

**Endpoint:** `POST /api/org/create/`

**Request Body:**
```json
{
  "org_id": "org_id",
  "org_name": "org_name"
}
```

**Response:**
```json
{
  "org_id": 123,
  "org_name": "org_name"
}
```

### 2. Sync User
Creates a new user or returns existing user data.

**Endpoint:** `POST /api/user/sync/`

**Request Body:**
```json
{
  "org_id": "org_id",
  "email": "name@example.com"
}
```

**Response:**
- Returns user data 

### 3. User Profile
Retrieves user profile data and all 4D sequences.

**Endpoint:** `GET /api/user/profile`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
None required

**Response:**
- Returns user profile data and 4D sequences (format not specified in original documentation)

### 4. Chat View
Handles chat interactions 

**Endpoint:** `POST /api/zavmo/chat/`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Request Body:**
```json
{
    "message": "Your message here"
}
```

**Response - New Session (201 Created):**
```json
{
    "type": "text",
    "message": "Hello! I'm here to assist you.",
    "stage": "<current_stage_value>"
}
```

**Response - Existing Session (200 OK):**
```json
{
    "type": "text",
    "message": "",
    "stage": "<current_stage_value>"
}
```

