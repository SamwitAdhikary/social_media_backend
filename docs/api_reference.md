# API Reference

Base URL: `http://localhost:8000/api/`

---

## 1. Accounts

| Endpoint                         | Method | Auth Required | Description                                 |
|----------------------------------|--------|---------------|---------------------------------------------|
| `/accounts/register/`            | POST   | No            | Register a new user (sends OTP)             |
| `/accounts/verify-email-otp/`    | POST   | No            | Verify email with OTP                       |
| `/accounts/login/`               | POST   | No            | Login and receive JWT tokens                |
| `/accounts/check-username/`      | GET    | No            | Check if a username is available (query: `?username=`) |
| `/accounts/password-reset/`      | POST   | No            | Request password reset link via email       |
| `/accounts/password-reset-confirm/` | POST | No           | Confirm password reset with `uid` & `token` |
| `/accounts/change-password/`     | PUT    | Yes           | Change password for authenticated user      |
| `/accounts/enable-2fa/`          | POST   | Yes           | Enable two-factor authentication (email OTP)|
| `/accounts/delete-account/`      | DELETE | Yes           | Delete own user account                     |
| `/accounts/download-data/`       | GET    | Yes           | Download all personal data as JSON          |
| `/accounts/token/`               | POST   | No            | Obtain JWT (same as login)                  |
| `/accounts/token/refresh/`       | POST   | No            | Refresh JWT                                  |
| `/accounts/token/verify/`        | POST   | No            | Verify validity of JWT                      |
| `/accounts/check-username/`      | GET    | No            | Check if username exists (`?username=`)     |

---

## 2. Posts

| Endpoint                           | Method | Auth Required | Description                                    |
|------------------------------------|--------|---------------|------------------------------------------------|
| `/posts/`                          | POST   | Yes           | Create a new post (multipart/form-data)        |
| `/posts/feed/`                     | GET    | Yes           | Retrieve personalized feed (`?sort=&page=`)    |
| `/posts/{pk}/`                     | GET    | No            | Retrieve a single post (increments view count) |
| `/posts/{pk}/delete/`              | DELETE | Yes           | Delete own post                                |
| `/posts/{post_id}/react/`          | POST   | Yes           | React or update reaction on post (`type`)      |
| `/posts/{post_id}/comment/`        | POST   | Yes           | Add comment to post (`content`, optional `parent`) |
| `/posts/comments/{comment_id}/toggle-visibility/` | PATCH | Yes   | Hide/unhide a comment on own post              |
| `/posts/{post_id}/save/`           | POST   | Yes           | Bookmark a post                                |
| `/posts/{post_id}/unsave/`         | DELETE | Yes           | Remove bookmark                                |
| `/posts/saved-posts/`              | GET    | Yes           | List saved posts                               |
| `/posts/hashtag/search/`           | GET    | Yes           | Search hashtags (`?search=`)                   |
| `/posts/user/{username}/posts/`    | GET    | Yes           | User’s posts (`?limit=&page=`)                 |
| `/posts/{post_id}/top-fan/`        | GET    | Yes           | Get user with most interactions on a post      |
| `/posts/{post_id}/share/`          | POST   | Yes           | Share a post (`share_text`, query `is_shared`) |
| `/posts/user/{user_id}/shared/`    | GET    | Yes           | List posts shared by a user                    |
| `/posts/shared/{shared_post_id}/comment/` | POST | Yes    | Comment on a shared post (`content`)           |
| `/posts/shared/{shared_post_id}/react/`  | POST | Yes    | React to a shared post (`type`)                |
| `/posts/comment/{comment_id}/react/`     | POST | Yes    | React to a comment (`type`)                    |
| `/posts/shared-comment/{shared_comment_id}/react/` | POST | Yes | React to a shared-post comment (`type`)        |
| `/posts/{pk}/click/`               | POST   | No            | Increment click count                          |
| `/posts/{post_id}/engagement/`     | GET    | No            | Get engagement metrics (reactions, comments, shares, views, clicks) |

---

## 3. Connections

| Endpoint                             | Method | Auth Required | Description                               |
|--------------------------------------|--------|---------------|-------------------------------------------|
| `/connections/request/`              | POST   | Yes           | Send friend or follower request (`target`, `connection_type`) |
| `/connections/respond/`              | POST   | Yes           | Accept/decline a connection (`connection_id`, `status`)      |
| `/connections/received/`             | GET    | Yes           | List incoming pending requests            |
| `/connections/sent/`                 | GET    | Yes           | List sent requests (`?status=`)           |
| `/connections/friends/`              | GET    | Yes           | List all accepted friends                 |
| `/connections/follow/`               | POST   | Yes           | Follow a user (`target_id`)               |
| `/connections/unfollow/`             | POST   | Yes           | Unfollow a user (`target_id`)             |
| `/connections/followers/`            | GET    | Yes           | List followers                            |
| `/connections/following/`            | GET    | Yes           | List users current user is following      |

---

## 4. Groups

| Endpoint                              | Method | Auth Required | Description                                  |
|---------------------------------------|--------|---------------|----------------------------------------------|
| `/groups/`                            | GET/POST | Yes         | List or create groups (`?search=&page=`)     |
| `/groups/{pk}/`                       | GET    | Yes           | Retrieve group details                       |
| `/groups/{group_id}/join/`            | POST   | Yes           | Join a group (auto‑approve for public)       |
| `/groups/membership/{membership_id}/approve/` | POST | Yes      | Approve membership (admin only)              |
| `/groups/{group_id}/members/`         | GET    | Yes           | List approved members                        |
| `/groups/search/`                     | GET    | Yes           | Search groups by name/description (`?search=`) |
| `/groups/{group_id}/most-active-member/` | GET  | Yes          | Get the most active member in a group        |
| `/groups/{group_id}/posts/`           | GET    | Yes           | List posts in group (privacy enforced)       |

---

## 5. Stories

| Endpoint                               | Method | Auth Required | Description                         |
|----------------------------------------|--------|---------------|-------------------------------------|
| `/stories/create/`                     | POST   | Yes           | Create a story (multipart/form-data) |
| `/stories/list/`                       | GET    | Yes           | List active (non‑expired) stories    |
| `/stories/{pk}/detail/`                | GET    | Yes           | Retrieve a single story’s details    |
| `/stories/{pk}/delete/`                | DELETE | Yes           | Delete own story (before expiry)     |
| `/stories/{story_id}/seen/`            | POST   | Yes           | Mark story as seen                   |
| `/stories/{story_id}/react/`           | POST   | Yes           | React to a story (`type=love`)       |

---

## 6. Notifications

| Endpoint                               | Method | Auth Required | Description                           |
|----------------------------------------|--------|---------------|---------------------------------------|
| `/notifications/`                      | GET    | Yes           | List all notifications (paginated)     |
| `/notifications/{notification_id}/read/` | PUT  | Yes           | Mark a notification as read           |
| `/notifications/mark-all-read/`        | POST   | Yes           | Mark all as read                      |
| `/notifications/mark-all-unread/`      | POST   | Yes           | Mark all as unread                    |

---

## 7. Authentication Endpoints (JWT)

| Endpoint              | Method | Auth Required | Description                   |
|-----------------------|--------|---------------|-------------------------------|
| `/accounts/token/`    | POST   | No            | Obtain JWT (`username`, `password` or `email`, `password`) |
| `/accounts/token/refresh/` | POST | No         | Refresh JWT (`refresh` token) |
| `/accounts/token/verify/`  | POST | No         | Verify JWT (`token`)          |

---

Refer to the **Usage Guide** (`docs/usage.md`) for full request/response examples. For any questions, check the code comments or reach out via the support channel.  
