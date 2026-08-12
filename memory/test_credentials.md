# Test Credentials

## Admin / Owner Account
- Email: mateus.ferreira@camainbox.com.br
- Password: Nfe@2026Admin
- Role: admin

## Auth Endpoints
- POST /api/auth/register  (name, email, password)
- POST /api/auth/login     (email, password) -> returns access_token + user
- POST /api/auth/logout
- GET  /api/auth/me        (Bearer token)

## Notes
- Frontend stores JWT in localStorage and sends via Authorization: Bearer header.
- Register a new account from the UI to create additional users.
