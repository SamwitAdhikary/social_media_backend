# Usage Guide

This guide provides detailed examples of how to interact with the Django Social Media Backend API. All examples assume the API is running at `http://localhost:8000`.

---

## 🔗 Base URL
```bash
http://localhost:8000/api/
```
For WebSocket endpoints, the URL is:
```bash
ws://localhost:8000/ws/<path>/?token=<JWT_ACCESS_TOKEN>
```

---

## 🛂 Authentication
All protected endpoints require a Bearer JWT in the `Authorization` header:
```makefile
Authorization: Bearer <ACCESS_TOKEN>
```

You obtain tokens via **Login** endpoint.

---

## 1. Accounts
### 1.1 Register New User
Request
```bash
curl -X POST http://localhost:8000/api/accounts/register/ \
-H "Content-Type: application/json" \
-d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "Secret123!"
}'
```
Response
```json
{
  "message": "Registration successful. An OTP has been sent to your email for verification.",
  "user_id": 2,
  "token": {
    "refresh": "<REFRESH_TOKEN>",
    "access": "<ACCESS_TOKEN>"
  }
}
```

### 1.2 Verify Email OTP
Request
```bash
curl -X POST http://localhost:8000/api/accounts/verify-email-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "otp": "123456"
  }'
```
Response
```json
{
    "message": "Email verified successfully"
}
```

### 1.3 Login & Obtain JWT
Request
```bash
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "Secret123!"
  }'
```
Response
```json
{
  "token": {
    "refresh": "<REFRESH_TOKEN>",
    "access": "<ACCESS_TOKEN>"
  },
  "user": {
    "id": 2,
    "username": "alice"
  }
}
```

---

## 2. Posts
### 2.1 Create a Post
Request
```bash
curl -X POST http://localhost:8000/api/posts/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "content=Hello world from Alice!" \
  -F "media_files=@/path/to/photo.jpg" \
  -F "hashtags=[\"welcome\",\"firstpost\"]"
```
Response
```json
{
  "id": 5,
  "user": { "id": 2, "username": "alice", … },
  "content": "Hello world from Alice!",
  "group": null,
  "visibility": "public",
  "medias": [
    {
      "id": 12,
      "media_url": "https://.../photo.jpg",
      "media_type": "image",
      "thumbnail_url": "https://.../thumb_photo.jpg",
      "order_index": 0,
      "created_at": "2025-06-16T10:00:00Z"
    }
  ],
  "created_at": "2025-06-16T10:00:00Z",
  "updated_at": "2025-06-16T10:00:00Z",
  "comments": [],
  "reactions": [],
  "comments_count": 0,
  "reactions_count": 0,
  "hashtags_display": [
    { "id": 3, "name": "welcome", "posts_count": 1, "posts": [...] },
    { "id": 4, "name": "firstpost", "posts_count": 1, "posts": [...] }
  ],
  "share_count": 0,
  "tags": ["welcome","firstpost"]
}
```

### 2.2 Fetch Personalized Feed
Request
```bash
curl -X GET "http://localhost:8000/api/posts/feed/?sort=chronological&page=1" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Response
```json
{
  "count": 10,
  "next": "http://.../feed/?page=2",
  "results": [
    {
      "id": 5,
      "item_type": "post",
      "content": "...",
      …
    },
    {
      "id": 1,
      "item_type": "shared",
      …
    }
  ]
}
```

---

## 3. Connections (Friends & Followers)
### 3.1 Send Friend Request
Request
```bash
curl -X POST http://localhost:8000/api/connections/request/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"target": 3, "connection_type": "friend"}'
```
Response
```json
{ "message": "Request sent" }
```

### 3.2 List Received Requests
Request
```bash
curl -X GET http://localhost:8000/api/connections/received/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Response
```json
[
  { "id": 7, "requester_details": { … }, "status": "pending", … }
]
```

---

## 4. Groups
### 4.1 Create a Group
Request
```bash
curl -X POST http://localhost:8000/api/groups/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Book Club",
    "description": "Discussing books every week",
    "privacy": "private"
  }'
```
Response
```json
{
  "id": 4,
  "created_by": { "id": 2, "username": "alice", … },
  "name": "Book Club",
  "description": "Discussing books every week",
  "privacy": "private",
  …
}
```

### 4.2 Join a Group
Request
```bash
curl -X POST http://localhost:8000/api/groups/4/join/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Response
```json
{
  "detail": "Join request sent. Awaiting admin approval.",
  "membership": { "id": 9, "role": "member", "status": "pending", … }
}
```

---

## 5. Stories
### 5.1 Create a Story
Request
```bash
curl -X POST http://localhost:8000/api/stories/create/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "media_files=@/path/to/story.jpg" \
  -F "content=Sunny day!"
```
Response
```json
{
  "id": 2,
  "user": 2,
  "media_url": "https://…/story.jpg",
  "content": "Sunny day!",
  "created_at": "2025-06-16T10:05:00Z",
  "expires_at": "2025-06-17T10:05:00Z",
  "seen_count": 0,
  "reaction_count": 0,
  "is_seen": false
}
```

### 5.2 Mark Story as Seen
Request
```bash
curl -X POST http://localhost:8000/api/stories/2/seen/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Response
```json
{ "message": "Story marked as seen", "seen_count": 1 }
```

---

## 6. Notifications
### 6.1 List Notifications
Request
```bash
curl -X GET http://localhost:8000/api/notifications/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Response
```json
[
  {
    "id": 15,
    "type": "comment",
    "message": "bob commented on your post.",
    "is_read": false,
    "created_at": "2025-06-16T10:10:00Z"
  },
  …
]
```

### 6.2 WebSocket Real‑Time Notifications
1. Connect
```nginx
wscat -c "ws://localhost:8000/ws/notifications/?token=<ACCESS_TOKEN>"
```
2. On new notifications you’ll receive JSON objects:
```json
{
  "id": 15,
  "type": "comment",
  "message": "bob commented on your post."
}
```

---

*You've now seen example requests for all core modules. For full endpoint reference, see `docs/api_reference.md`. Enjoy building with this backend.*