package com.shora.service;

import com.shora.dto.ForgotPasswordRequest;
import com.shora.dto.LoginRequest;
import com.shora.dto.SignupRequest;
import com.shora.model.User;
import com.shora.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@Service
@Transactional
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    public AuthService(UserRepository userRepository,
                       PasswordEncoder passwordEncoder,
                       JwtTokenProvider jwtTokenProvider) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
    }

    public Map<String, Object> signup(SignupRequest request) {
        String name = request.getName() == null ? null : request.getName().trim();
        String email = request.getEmail() == null ? null : request.getEmail().trim();
        String password = request.getPassword();
        String confirmPassword = request.getConfirmPassword();

        if (name == null || name.isEmpty()) {
            throw new RuntimeException("Name is required");
        }

        if (email == null || email.isEmpty()) {
            throw new RuntimeException("Email is required");
        }

        if (password == null || password.length() < 6) {
            throw new RuntimeException("Password must be at least 6 characters");
        }

        if (confirmPassword == null || !password.equals(confirmPassword)) {
            throw new RuntimeException("Password and confirm password must match");
        }

        if (userRepository.existsByEmail(email)) {
            throw new RuntimeException("Email already registered");
        }

        User user = new User();
        user.setName(name);
        user.setEmail(email);
        user.setPassword(passwordEncoder.encode(password));

        User savedUser = userRepository.save(user);
        String token = jwtTokenProvider.generateToken(savedUser.getEmail());

        Map<String, Object> response = new HashMap<>();
        response.put("token", token);
        response.put("user", buildUserResponse(savedUser));
        return response;
    }

    public Map<String, Object> login(LoginRequest request) {
        String email = request.getEmail() == null ? null : request.getEmail().trim();
        String password = request.getPassword();

        if (email == null || email.isEmpty() || password == null || password.isEmpty()) {
            throw new RuntimeException("Email and password are required");
        }

        Optional<User> userOptional = userRepository.findByEmail(email);
        if (!userOptional.isPresent()) {
            throw new RuntimeException("Invalid email or password");
        }

        User user = userOptional.get();
        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new RuntimeException("Invalid email or password");
        }

        String token = jwtTokenProvider.generateToken(user.getEmail());

        Map<String, Object> response = new HashMap<>();
        response.put("token", token);
        response.put("user", buildUserResponse(user));
        return response;
    }

    public Optional<User> getUserByEmail(String email) {
        return userRepository.findByEmail(email);
    }

    public Map<String, String> forgotPassword(ForgotPasswordRequest request) {
        String email = request.getEmail() == null ? null : request.getEmail().trim();
        if (email == null || email.isEmpty()) {
            throw new RuntimeException("Email is required");
        }

        userRepository.existsByEmail(email);

        Map<String, String> response = new HashMap<>();
        response.put("message", "If the email exists, a reset link has been sent.");
        return response;
    }

    private Map<String, Object> buildUserResponse(User user) {
        Map<String, Object> userResponse = new HashMap<>();
        userResponse.put("id", user.getId());
        userResponse.put("name", user.getName());
        userResponse.put("email", user.getEmail());
        return userResponse;
    }
}
