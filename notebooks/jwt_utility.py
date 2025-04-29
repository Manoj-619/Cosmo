#!/usr/bin/env python3
"""
JWT Utility Script - For generating and verifying JWT tokens using RSA keys
"""

import os
import time
import jwt
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import load_dotenv

# Load environment variables if needed
load_dotenv(override=True)

def generate_rsa_key_pair():
    """Generate a new RSA key pair"""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Convert to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key in PEM format
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_key, private_key_pem, public_key_pem

def create_jwt_token(payload, private_key_pem, algorithm="RS256", kid="MebFunzP8Kq4D3HocG4b0PSSOEOglwgMEfLA_dscTVo", expiration_hours=1):
    """Create a JWT token with the given payload and private key"""
    # Add standard claims if not present
    if "exp" not in payload:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
    if "iat" not in payload:
        payload["iat"] = datetime.now(timezone.utc)
    
    # Encode the JWT
    token = jwt.encode(
        payload,
        private_key_pem,
        algorithm=algorithm,
        headers={
            "kid": kid
        }
    )
    
    return token

def verify_jwt_token(token, public_key_pem, algorithms=["RS256"], audience=None, issuer=None):
    """Verify a JWT token using the public key"""
    try:
        # Load the public key
        public_key = serialization.load_pem_public_key(public_key_pem)
        
        # Verify and decode the token
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=algorithms,
            audience=audience,
            issuer=issuer,
            options={"verify_signature": True}
        )
        
        return True, decoded
    except jwt.ExpiredSignatureError:
        return False, "Token has expired"
    except jwt.InvalidTokenError as e:
        return False, f"Invalid token: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Example usage of the JWT utilities"""
    # Generate key pair
    private_key, private_key_pem, public_key_pem = generate_rsa_key_pair()
    
    # Create a payload
    payload = {
        "iss": "https://login.zavmo.ai/auth/realms/Zavmo",
        "aud": "account",
        "sub": "user123",
        "name": "Test User",
        "email": "testuser@zavmo.ai",
        # Add other claims as needed
    }
    
    # Create token
    token = create_jwt_token(payload, private_key_pem)
    print("Encoded token:")
    print(token)
    
    # Verify token
    is_valid, result = verify_jwt_token(
        token, 
        public_key_pem,
        audience="account",
        issuer="https://login.zavmo.ai/auth/realms/Zavmo"
    )
    
    if is_valid:
        print("\nToken is valid!")
        print("Decoded payload:")
        print(result)
    else:
        print(f"\nToken verification failed: {result}")

if __name__ == "__main__":
    main()