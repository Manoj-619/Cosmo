# API Documentation

## Endpoints

### 1. Chat API

**POST** `/api/zavmo/chat/`

#### Request Headers

- `Authorization: Bearer <JWT_TOKEN>` (required)  
  The JWT token used for authenticating the user.

#### Request Body

```json
{
    "message": "Your message here"  // Optional, used to send a message to the chat
}
```

#### Response

- **201 Created** (on new session creation)

```json
{
    "type": "text",  // Response type
    "message": "Hello! I'm here to assist you.",  // AI's initial message
    "stage": <current_stage_value>  // Numeric value representing the user's current stage
}
```

#### Response

- **200 OK** (on existing session)

```json
{
    "type": "text",  // Response type
    "message": "",  // Empty message for ongoing session
    "stage": <current_stage_value>  // Numeric value representing the user's current stage
}
```

---

### 2. Create_Org API

**POST** `/api/create_org`

#### Description
This API creates a new organisation. It accepts an organisation name in the request body and returns the `org_id` upon successful creation.

#### Headers
```
Content-Type: application/json
```

#### Input
**Request Format:**
```json
{
  "name": "org_name"
}
```

#### Output
**Response Format:**
```json
{ 
  "org_id": 123, 
  "name": "org_name" 
}
```

---

### 3. Create_User API

**POST** `/api/create_user`

#### Description
This API allows clients to create a new user by sending a POST request with the user's details. It returns the user's data upon successful creation or error messages if the input is invalid.

#### Headers
```
Content-Type: application/json
Authorization: Bearer <token> (if required, depending on your app’s auth system)
```

#### Input
**Request Format:**
```json
{
  "username": "john_doe",
  "email": "john.doe@example.com"
}
```

#### Output
**Response Format:**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john.doe@example.com"
}
```

---

### 4. UserProfileView API

**GET** `/api/user_profile`

#### Description
This API retrieves the complete profile data of the authenticated user.

#### Headers
```
Content-Type: application/json
Authorization: Bearer <token>
```

#### Input
No input data is required in the request body. The profile data is fetched based on the authenticated user.

#### Output
**Response Format:**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "Software Developer at Tech Innovators",
  "learning_profile": ""
}
```
