# Shora - Educational Platform

A full-stack educational application with modern authentication and user dashboard.

## Project Structure

```
Shora/
├── frontend/
│   ├── index.html          (Sign Up Page)
│   ├── login.html          (Login Page)
│   ├── dashboard.html      (User Dashboard)
│   ├── css/
│   │   ├── style.css       (Global Styles)
│   │   ├── auth.css        (Auth Pages Styles)
│   │   └── dashboard.css   (Dashboard Styles)
│   ├── js/
│   │   └── script.js       (JavaScript Logic)
│   └── assets/
│       ├── images/
│       │   ├── logo.png
│       │   └── google-icon.png
│       └── icons/
│
└── backend/
    ├── pom.xml             (Maven Configuration)
    └── src/main/
        ├── java/com/shora/
        │   ├── ShoraApplication.java
        │   ├── controller/
        │   │   └── AuthController.java
        │   ├── service/
        │   │   ├── AuthService.java
        │   │   └── JwtTokenProvider.java
        │   ├── repository/
        │   │   └── UserRepository.java
        │   ├── model/
        │   │   └── User.java
        │   ├── dto/
        │   │   ├── LoginRequest.java
        │   │   └── SignupRequest.java
        │   └── config/
        │       └── SecurityConfig.java
        └── resources/
            └── application.properties
```

## Frontend Setup

### Prerequisites
- Modern web browser
- Node.js (optional, for local server)

### Installation

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Option A - Using Live Server (VS Code Extension)
   - Install "Live Server" extension in VS Code
   - Right-click on `index.html` → "Open with Live Server"
   - Default: `http://127.0.0.1:5500`

3. Option B - Using Python's HTTP Server
```bash
python -m http.server 8000
# Visit: http://localhost:8000
```

4. Option C - Using Node.js HTTP Server
```bash
npx http-server
# Visit: http://localhost:8080
```

### Frontend Features
- **Sign Up Page**: Create new account with email validation
- **Login Page**: Authenticate existing users
- **Dashboard**: View courses and progress (after login)
- **Responsive Design**: Works on desktop and mobile

## Backend Setup

### Prerequisites
- Java 17+
- Maven 3.6+
- MySQL 8.0+

### Installation

1. Navigate to backend directory:
```bash
cd backend
```

2. Create MySQL Database:
```sql
CREATE DATABASE shora_db;
```

3. Update `application.properties`:
```properties
spring.datasource.url=jdbc:mysql://localhost:3306/shora_db
spring.datasource.username=root
spring.datasource.password=your_password
```

4. Install dependencies:
```bash
mvn clean install
```

5. Run the application:
```bash
mvn spring-boot:run
```

Or build and run:
```bash
mvn clean package
java -jar target/shora-app-1.0.0.jar
```

Backend will run on `http://localhost:8080`

## API Endpoints

### Authentication

#### Sign Up
```
POST /api/auth/signup
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "confirmPassword": "password123"
}

Response: 201 Created
{
  "token": "eyJhbGciOiJIUzUxMiJ9...",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

#### Login
```
POST /api/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "password123"
}

Response: 200 OK
{
  "token": "eyJhbGciOiJIUzUxMiJ9...",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

#### Validate Token
```
GET /api/auth/validate
Authorization: Bearer <token>

Response: 200 OK
{
  "valid": true
}
```

## Technologies Used

### Frontend
- HTML5
- CSS3 (Responsive Design)
- Vanilla JavaScript (ES6+)
- Fetch API for HTTP requests

### Backend
- Spring Boot 3.1.5
- Spring Security with JWT
- Spring Data JPA
- MySQL 8.0
- Maven
- Lombok

## Features

### Current
✅ User Sign Up with validation
✅ User Login with JWT authentication
✅ Password encryption with BCrypt
✅ CORS configuration
✅ Dashboard page
✅ Responsive design

### Coming Soon
- Google OAuth integration
- User profile management
- Course management
- Progress tracking
- Search functionality
- Admin panel

## Security Features

- Password encryption (BCrypt)
- JWT token-based authentication
- CORS enabled
- Input validation
- SQL injection prevention (JPA)
- Session-less architecture

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Environment Configuration

### Frontend (.env or application settings)
```
VITE_API_URL=http://localhost:8080
```

### Backend (application.properties)
```
spring.datasource.url=jdbc:mysql://localhost:3306/shora_db
spring.datasource.username=root
spring.datasource.password=your_password
jwt.secret=your_secret_key
jwt.expiration=86400000
```

## Running Both Together

### Terminal 1 - Backend
```bash
cd backend
mvn spring-boot:run
```

### Terminal 2 - Frontend
```bash
cd frontend
# Using Python
python -m http.server 8000
# OR using Node
npx http-server
```

Then visit: `http://localhost:8000` or `http://localhost:8080`

## Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :8080
kill -9 <PID>
```

### Database Connection Error
- Ensure MySQL is running
- Check credentials in `application.properties`
- Verify database exists

### CORS Issues
- Frontend and Backend CORS are configured
- Ensure frontend URL matches in SecurityConfig

## Future Enhancements

1. Email verification
2. Password reset functionality
3. Social login (Google, GitHub)
4. Role-based access control
5. Payment integration
6. Real-time notifications
7. Video streaming
8. Mobile app (React Native)

## License

MIT License

## Support

For issues or questions, please create an issue in the repository.

---

**Happy Learning with Shora! 🎓**
