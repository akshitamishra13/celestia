# Phase 1: Authentication and dashboard

## Implemented

- User signup and login with validated email and password input
- Argon2 password hashing
- Seven-day HTTP-only session cookie
- Current-user and logout endpoints
- SQLAlchemy user persistence with SQLite for local development
- Responsive login and signup screens
- Client session restoration and dashboard access guard
- Authenticated dashboard greeting, avatar, email, and logout
- Integration tests for signup, session restoration, logout, and rejected credentials

## Deferred

- Password reset and email verification
- Production PostgreSQL configuration and migrations
- Authentication rate limiting
- Profile birth details
- Kundli and compatibility data integrations

Before deployment, set a strong `JWT_SECRET`, enable secure cookies over HTTPS, and configure the exact frontend origin.
