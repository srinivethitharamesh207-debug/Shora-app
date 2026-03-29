package com.shora.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.WeakKeyException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtTokenProvider {
    
    @Value("${jwt.secret:MyVerySecureSecretKeyThatIsLongEnoughForHS512AlgorithmAndCanBeUsedForJWTGeneration}")
    private String secretKey;
    
    @Value("${jwt.expiration:86400000}")
    private long expirationTime;

    private SecretKey signingKey;

    @PostConstruct
    public void init() {
        // Support both raw string secrets and explicit base64 secrets via "base64:" prefix.
        try {
            byte[] keyBytes;
            if (secretKey != null && secretKey.startsWith("base64:")) {
                keyBytes = Decoders.BASE64.decode(secretKey.substring("base64:".length()));
            } else {
                keyBytes = (secretKey == null ? "" : secretKey).getBytes(StandardCharsets.UTF_8);
            }
            this.signingKey = Keys.hmacShaKeyFor(keyBytes);
        } catch (WeakKeyException e) {
            throw new IllegalStateException(
                    "JWT secret is too short for HMAC signing. Use a longer secret (or set jwt.secret as base64:... with enough bytes).",
                    e
            );
        } catch (IllegalArgumentException e) {
            throw new IllegalStateException("Invalid jwt.secret configuration.", e);
        }
    }
    
    public String generateToken(String email) {
        return Jwts.builder()
                .subject(email)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + expirationTime))
                .signWith(signingKey)
                .compact();
    }
    
    public String getEmailFromToken(String token) {
        Claims claims = Jwts.parser()
                .verifyWith(signingKey)
                .build()
                .parseSignedClaims(stripBearerPrefix(token))
                .getPayload();
        
        return claims.getSubject();
    }
    
    public boolean validateToken(String token) {
        try {
            Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(stripBearerPrefix(token));
            return true;
        } catch (io.jsonwebtoken.JwtException | IllegalArgumentException e) {
            return false;
        }
    }

    private static String stripBearerPrefix(String token) {
        if (token == null) {
            return null;
        }
        String trimmed = token.trim();
        return trimmed.startsWith("Bearer ") ? trimmed.substring(7).trim() : trimmed;
    }
}
