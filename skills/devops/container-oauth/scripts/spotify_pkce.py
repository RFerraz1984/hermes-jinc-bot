#!/usr/bin/env python3
"""
Spotify PKCE token exchange - Manual flow for Umbrel/container environments
Usage:
  python3 spotify_pkce.py                    # Generate auth URL + code_verifier
  python3 spotify_pkce.py <code> <verifier>  # Exchange code for tokens
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import requests

CLIENT_ID = "29211866598740e891275a6076add397"
REDIRECT_URI = "http://127.0.0.1:43827/spotify/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-library-read user-library-modify"
AUTH_FILE = "/opt/data/auth_spotify.json"

def gen_code_verifier():
    return secrets.token_urlsafe(64)[:128]

def gen_code_challenge(verifier):
    sha256 = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(sha256).decode().rstrip("=")

def build_auth_url(verifier):
    challenge = gen_code_challenge(verifier)
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": secrets.token_urlsafe(16)
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}", challenge

def exchange_code(code, verifier):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def save_tokens(token_data):
    # Add expiry timestamp
    import time
    token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
    with open(AUTH_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"Tokens saved to {AUTH_FILE}")
    # Also update Hermes auth.json via internal API
    update_hermes_auth(token_data)

def update_hermes_auth(token_data):
    """Update Hermes auth.json with Spotify tokens"""
    import sys
    sys.path.insert(0, '/opt/hermes')
    from hermes_cli.auth import _store_provider_state, _load_auth_store, _save_auth_store
    
    auth_store = _load_auth_store()
    spotify_state = {
        'access_token': token_data['access_token'],
        'refresh_token': token_data['refresh_token'],
        'token_type': token_data.get('token_type', 'Bearer'),
        'expires_at': token_data['expires_at'],
        'scope': token_data.get('scope', ''),
        'granted_scope': token_data.get('scope', ''),
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'api_base_url': 'https://api.spotify.com/v1',
        'accounts_base_url': 'https://accounts.spotify.com',
        'auth_type': 'oauth_pkce',
    }
    _store_provider_state(auth_store, 'spotify', spotify_state, set_active=False)
    _save_auth_store(auth_store)
    print("Updated Hermes auth.json")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        verifier = gen_code_verifier()
        auth_url, challenge = build_auth_url(verifier)
        print("=== NOVA URL DE AUTORIZAÇÃO ===")
        print(auth_url)
        print()
        print("=== CODE VERIFIER (GUARDE!) ===")
        print(verifier)
        print()
        print("Abra a URL acima no navegador, autorize, copie o 'code' da URL de retorno,")
        print("depois rode: python3 spotify_pkce.py <code> <code_verifier>")
        sys.exit(0)

    code = sys.argv[1]
    verifier = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not verifier:
        print("ERRO: Precisa do code_verifier. Rode sem args para gerar novo par.")
        sys.exit(1)

    print("Trocando code por tokens...")
    tokens = exchange_code(code, verifier)
    save_tokens(tokens)
    print("Sucesso!")
    print(json.dumps(tokens, indent=2))