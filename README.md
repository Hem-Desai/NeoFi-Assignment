# NeoFi Backend Challenge: Collaborative Event Management System

A RESTful API for an event scheduling application with collaborative editing features, built with FastAPI.

## Features

### Authentication and Authorization
- Token-based authentication with JWT
- Role-based access control (RBAC) with Owner, Editor, and Viewer roles
- User registration, login, token refresh, and logout

### Event Management
- CRUD operations for events
- Support for recurring events with customizable patterns
- Conflict detection for overlapping events
- Batch operations for creating multiple events

### Collaboration Features
- Sharing system with granular permissions
- Real-time notifications for changes
- Edit history with attribution

### Advanced Features
- Versioning system with rollback capability
- Changelog with diff visualization
- Event conflict resolution strategies
- Transaction system for atomic operations

## Technical Implementation

- **FastAPI**: Modern, high-performance web framework with automatic OpenAPI documentation
- **SQLAlchemy**: ORM for database operations with async support
- **Pydantic**: Data validation and settings management
- **JWT**: Secure token-based authentication
- **MessagePack**: Alternative serialization format support alongside JSON
- **Alembic**: Database migration tool
- **Redis** (optional): For caching and real-time notifications

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables (copy `.env.example` to `.env` and modify as needed)
4. Run database migrations:
   ```
   alembic upgrade head
   ```
5. Initialize the database with a superuser (optional):
   ```
   python -m app.db.init_db
   ```
6. Start the server:
   ```
   python run.py
   ```
   or
   ```
   uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

A Postman collection is included for testing the API endpoints. Import `postman_collection.json` into Postman to get started.

To run the automated tests:
```
pytest tests/
```

## Project Structure

```
app/
├── api/                # API endpoints
│   ├── auth/           # Authentication endpoints
│   ├── events/         # Event management endpoints
│   └── notifications/  # Notification endpoints
├── core/               # Core application components
│   ├── config.py       # Application configuration
│   ├── security.py     # Security utilities
│   └── exceptions.py   # Custom exceptions
├── db/                 # Database related code
│   ├── base.py         # Base database setup
│   ├── models/         # SQLAlchemy models
│   └── repositories/   # Database repositories
├── schemas/            # Pydantic schemas for validation
├── services/           # Business logic services
│   └── notification.py # Notification service
└── main.py            # Application entry point
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and receive an authentication token
- `POST /api/auth/refresh` - Refresh an authentication token
- `POST /api/auth/logout` - Invalidate the current token

### Event Management
- `POST /api/events` - Create a new event
- `GET /api/events` - List all events the user has access to
- `GET /api/events/{id}` - Get a specific event by ID
- `PUT /api/events/{id}` - Update an event by ID
- `DELETE /api/events/{id}` - Delete an event by ID
- `POST /api/events/batch` - Create multiple events in a single request

### Collaboration
- `POST /api/events/{id}/share` - Share an event with other users
- `GET /api/events/{id}/permissions` - List all permissions for an event
- `PUT /api/events/{id}/permissions/{userId}` - Update permissions for a user
- `DELETE /api/events/{id}/permissions/{userId}` - Remove access for a user

### Version History
- `GET /api/events/{id}/history/{versionId}` - Get a specific version of an event
- `POST /api/events/{id}/rollback/{versionId}` - Rollback to a previous version
- `GET /api/events/{id}/changelog` - Get a chronological log of all changes
- `GET /api/events/{id}/diff/{versionId1}/{versionId2}` - Get a diff between versions

### Notifications
- `GET /api/notifications` - Get all notifications for the current user
- `POST /api/notifications/read` - Mark all notifications as read
- `POST /api/notifications/{id}/read` - Mark a specific notification as read

## Security Features

- JWT token-based authentication
- Password hashing with bcrypt
- Role-based access control
- Input validation with Pydantic
- Rate limiting middleware
- CORS protection

## Data Models

- **User**: Authentication and user information
- **Event**: Core event data with recurrence support
- **EventPermission**: Permissions for event sharing
- **EventVersion**: Version history for events

## Additional Notes

- The application uses SQLite by default for development but can be configured to use PostgreSQL for production
- Redis can be enabled for more robust caching and real-time notifications
- The notification system works in-memory by default but can use Redis for production
