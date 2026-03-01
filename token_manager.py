"""
Token management for different regions
"""

import asyncio
import time
import httpx
from typing import Dict, Optional
from dataclasses import dataclass
from .crypto import CryptoManager
from proto import FreeFire_pb2
from google.protobuf.json_format import ParseDict, MessageToJson
import json

@dataclass
class TokenInfo:
    value: str
    region: str
    server_url: str
    expires_at: float

class TokenManager:
    def __init__(self):
        self.tokens: Dict[str, TokenInfo] = {}
        self.crypto = CryptoManager()
        self.user_agent = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"
        
        # Guest accounts from accounts.txt
        self.accounts = self._load_accounts()
        
        # Supported regions
        self.regions = {"IND", "BR", "US", "SAC", "NA", "SG", "RU", "ID", 
                        "TW", "VN", "TH", "ME", "PK", "CIS", "BD", "EUROPE"}
    
    def _load_accounts(self):
        """Load guest accounts from file"""
        accounts = {}
        try:
            with open('accounts.txt', 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        uid, token = line.strip().split()
                        accounts[uid] = token
        except:
            # Default accounts if file not found
            accounts = {
                "3933356115": "CA6DDAEE7F32A95D6BC17B15B8D5C59E091338B4609F25A1728720E8E4C107C4",
                "4044223479": "EB067625F1E2CB705C7561747A46D502480DC5D41497F4C90F3FDBC73B8082ED",
            }
        return accounts
    
    def get_account_for_region(self, region: str) -> tuple:
        """Get account credentials for region"""
        accounts_list = list(self.accounts.items())
        # Simple round-robin based on region hash
        idx = hash(region) % len(accounts_list)
        return accounts_list[idx]
    
    async def get_access_token(self, account_uid: str, account_token: str) -> tuple:
        """Get access token from guest account"""
        url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
        payload = f"uid={account_uid}&password={account_token}&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
        
        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload, headers=headers)
            data = resp.json()
            return data.get("access_token", "0"), data.get("open_id", "0")
    
    async def create_jwt(self, region: str):
        """Create JWT token for region"""
        account_uid, account_token = self.get_account_for_region(region)
        access_token, open_id = await self.get_access_token(account_uid, account_token)
        
        # Build login request
        login_req = FreeFire_pb2.LoginReq()
        login_req.open_id = open_id
        login_req.open_id_type = "4"
        login_req.login_token = access_token
        login_req.orign_platform_type = "4"
        
        # Encrypt
        encrypted = self.crypto.encrypt(login_req.SerializeToString())
        
        # Send login request
        url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/octet-stream',
            'ReleaseVersion': 'OB52'
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=encrypted, headers=headers)
            
            # Parse response
            login_res = FreeFire_pb2.LoginRes()
            login_res.ParseFromString(self.crypto.decrypt(resp.content))
            
            # Store token
            self.tokens[region] = TokenInfo(
                value=login_res.token,
                region=login_res.lock_region,
                server_url=login_res.server_url,
                expires_at=time.time() + 25200  # 7 hours
            )
    
    async def get_token(self, region: str) -> TokenInfo:
        """Get token for region, refresh if expired"""
        token = self.tokens.get(region)
        if token and time.time() < token.expires_at:
            return token
        
        await self.create_jwt(region)
        return self.tokens[region]
    
    async def initialize(self):
        """Initialize tokens for all regions"""
        tasks = [self.create_jwt(r) for r in self.regions]
        await asyncio.gather(*tasks)
    
    async def refresh_all(self):
        """Refresh all tokens"""
        await self.initialize()
    
    def count(self) -> int:
        """Get number of active tokens"""
        return len(self.tokens)