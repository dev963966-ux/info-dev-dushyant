"""
Free Fire Player Info API
Complete version with all features
"""

import asyncio
import time
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import custom modules
from utils.crypto import CryptoManager
from utils.token_manager import TokenManager
from utils.cache_manager import CacheManager
from proto import FreeFire_pb2, AccountPersonalShow_pb2

app = Flask(__name__)
CORS(app)

# Initialize managers
crypto = CryptoManager()
token_mgr = TokenManager()
cache = CacheManager()

# Configuration
SUPPORTED_REGIONS = {"IND", "BR", "US", "SAC", "NA", "SG", "RU", "ID", 
                     "TW", "VN", "TH", "ME", "PK", "CIS", "BD", "EUROPE"}

@app.route('/')
def home():
    return jsonify({
        "name": "Free Fire Player Info API",
        "version": "2.0",
        "author": "Your Name",
        "endpoints": {
            "/player-info": "GET - Get player info by UID",
            "/player-info?uid=123&region=IND": "With specific region",
            "/refresh": "POST - Refresh tokens",
            "/health": "GET - Check API status",
            "/stats": "GET - API statistics"
        },
        "supported_regions": list(SUPPORTED_REGIONS)
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "cache_size": cache.size(),
        "tokens_available": token_mgr.count()
    })

@app.route('/stats')
def stats():
    return jsonify({
        "total_requests": cache.get_request_count(),
        "cache_hits": cache.get_hits(),
        "cache_misses": cache.get_misses(),
        "active_tokens": token_mgr.count()
    })

@app.route('/player-info')
def get_player_info():
    """Main endpoint to get player info"""
    uid = request.args.get('uid')
    region = request.args.get('region', '').upper()
    
    if not uid:
        return jsonify({"error": "Please provide UID"}), 400
    
    # Check cache first
    cache_key = f"{uid}_{region}"
    cached_data = cache.get(cache_key)
    if cached_data:
        cache.record_hit()
        return jsonify(cached_data)
    
    cache.record_miss()
    
    # If region specified, try only that region
    if region and region in SUPPORTED_REGIONS:
        try:
            data = asyncio.run(fetch_player_data(uid, region))
            cache.set(cache_key, data)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": f"Region {region} failed: {str(e)}"}), 404
    
    # Try all regions
    for reg in SUPPORTED_REGIONS:
        try:
            data = asyncio.run(fetch_player_data(uid, reg))
            cache.set(f"{uid}_{reg}", data)
            cache.set_region(uid, reg)  # Remember region for this UID
            return jsonify(data)
        except:
            continue
    
    return jsonify({"error": "UID not found in any region"}), 404

@app.route('/refresh', methods=['POST'])
def refresh_tokens():
    """Manually refresh tokens"""
    try:
        asyncio.run(token_mgr.refresh_all())
        return jsonify({"message": "Tokens refreshed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def fetch_player_data(uid: str, region: str):
    """Fetch player data from Free Fire servers"""
    # Get token for region
    token = await token_mgr.get_token(region)
    
    # Build request
    from google.protobuf.json_format import ParseDict
    request_msg = AccountPersonalShow_pb2.AccountPersonalShowInfo()
    
    # Encrypt request
    encrypted_data = crypto.encrypt(request_msg.SerializeToString())
    
    # Make HTTP request
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token.server_url + "/GetPlayerPersonalShow",
            content=encrypted_data,
            headers={
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 13; CPH2095)',
                'Authorization': f"Bearer {token.value}",
                'Content-Type': 'application/octet-stream',
                'ReleaseVersion': 'OB52'
            }
        )
        
        # Decrypt response
        decrypted = crypto.decrypt(response.content)
        
        # Parse protobuf
        result = AccountPersonalShow_pb2.AccountPersonalShowInfo()
        result.ParseFromString(decrypted)
        
        # Convert to JSON
        from google.protobuf.json_format import MessageToJson
        return json.loads(MessageToJson(result))

if __name__ == '__main__':
    # Initialize tokens on startup
    asyncio.run(token_mgr.initialize())
    app.run(host='0.0.0.0', port=5000, debug=True)