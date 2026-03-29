package com.shora.controller;

import com.shora.dto.LoginRequest;
import com.shora.dto.SignupRequest;
import com.shora.service.AuthService;
import com.shora.service.JwtTokenProvider;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    
    private final AuthService authService;
    private final JwtTokenProvider jwtTokenProvider;

    public AuthController(AuthService authService, JwtTokenProvider jwtTokenProvider) {
        this.authService = authService;
        this.jwtTokenProvider = jwtTokenProvider;
    }
    
    @PostMapping("/signup")
    public ResponseEntity<?> signup(@Valid @RequestBody SignupRequest request) {
        try {
            Map<String, Object> response = authService.signup(request);
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (RuntimeException e) {
            Map<String, String> error = new HashMap<>();
            error.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
        }
    }
    
    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest request) {
        try {
            Map<String, Object> response = authService.login(request);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            Map<String, String> error = new HashMap<>();
            error.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }
    }
    
    @GetMapping("/validate")
    public ResponseEntity<?> validateToken(@RequestHeader("Authorization") String token) {
        try {
            if (token != null && token.startsWith("Bearer ")) {
                token = token.substring(7);
            }
            
            if (token == null || token.isEmpty()) {
                return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of("valid", false, "message", "Token is missing"));
            }
            
            boolean isValid = jwtTokenProvider.validateToken(token);
            return ResponseEntity.ok(Map.of("valid", isValid));
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("valid", false, "message", e.getMessage()));
        }
    }
}
