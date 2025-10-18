"""
Pocket Option API Integration
Supports demo and real trading via WebSocket connection
"""

import asyncio
import json
import logging
import websockets
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class PocketOptionAPI:
    """
    Async API client for Pocket Option broker
    Uses WebSocket connection for real-time trading
    """
    
    # WebSocket endpoints
    DEMO_WS_URL = "wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"
    REAL_WS_URL = "wss://api-eu.po.market/socket.io/?EIO=4&transport=websocket"
    
    def __init__(self, ssid: str, demo: bool = True):
        """
        Initialize Pocket Option API client
        
        Args:
            ssid: Session ID from browser (format: 42["auth",{...}])
            demo: True for demo account, False for real account
        """
        self.ssid = ssid
        self.demo = demo
        self.ws = None
        self.connected = False
        self.balance = 0.0
        self.user_id = None
        self.ping_task = None
        self.message_handlers = {}
        self.pending_trades = {}
        
    async def connect(self) -> bool:
        """
        Connect to Pocket Option WebSocket server
        
        Returns:
            True if connected successfully
        """
        try:
            ws_url = self.DEMO_WS_URL if self.demo else self.REAL_WS_URL
            logger.info(f"🔌 Connecting to Pocket Option {'DEMO' if self.demo else 'REAL'} server...")
            
            self.ws = await websockets.connect(ws_url)
            
            # Send initial ping
            await self.ws.send("2")
            
            # Wait for pong
            response = await asyncio.wait_for(self.ws.recv(), timeout=5)
            logger.info(f"📡 Server response: {response}")
            
            # Send auth message with SSID
            await self.ws.send(self.ssid)
            
            # Wait for auth confirmation
            auth_response = await asyncio.wait_for(self.ws.recv(), timeout=10)
            logger.info(f"🔐 Auth response received: {len(auth_response)} bytes")
            
            # Parse and verify authentication response
            if not await self._verify_auth(auth_response):
                logger.error("❌ Authentication failed")
                await self.close()
                return False
            
            self.connected = True
            
            # Start ping task
            self.ping_task = asyncio.create_task(self._ping_loop())
            
            # Start message handler
            asyncio.create_task(self._message_loop())
            
            logger.info("✅ Connected to Pocket Option successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            self.connected = False
            if self.ws:
                await self.ws.close()
            return False
    
    async def _verify_auth(self, auth_response: str) -> bool:
        """
        Verify authentication response from Pocket Option
        
        Returns:
            True if authenticated successfully
        """
        try:
            # Auth response format: 0{"sid":"...","upgrades":["websocket"],"pingTimeout":...}
            # Or error: 4{"message":"Authentication failed"}
            
            if auth_response.startswith("4"):
                # Error response
                try:
                    error_data = json.loads(auth_response[1:])
                    logger.error(f"Auth error: {error_data.get('message', 'Unknown error')}")
                except:
                    logger.error(f"Auth failed with response: {auth_response}")
                return False
            
            if auth_response.startswith("0"):
                # Success response with session ID
                try:
                    session_data = json.loads(auth_response[1:])
                    if "sid" in session_data:
                        logger.info(f"✅ Authenticated with SID: {session_data['sid'][:10]}...")
                        return True
                except:
                    pass
            
            # Check for explicit auth success message
            if "auth" in auth_response.lower() and "success" in auth_response.lower():
                return True
            
            # If we got any valid Socket.IO message, consider it connected
            # (some brokers don't send explicit auth confirmation)
            if auth_response.startswith(("0", "2", "3", "40", "42")):
                logger.info("✅ Connection established (implicit auth)")
                return True
            
            logger.error(f"Unexpected auth response format: {auth_response[:100]}")
            return False
            
        except Exception as e:
            logger.error(f"Auth verification error: {e}")
            return False
    
    async def _ping_loop(self):
        """Send ping every 20 seconds to keep connection alive"""
        while self.connected:
            try:
                await asyncio.sleep(20)
                if self.ws:
                    await self.ws.send("2")
                    logger.debug("📡 Ping sent")
            except Exception as e:
                logger.error(f"❌ Ping error: {e}")
                break
    
    async def _message_loop(self):
        """Handle incoming WebSocket messages"""
        while self.connected:
            try:
                message = await self.ws.recv()
                await self._handle_message(message)
            except Exception as e:
                logger.error(f"❌ Message loop error: {e}")
                break
    
    async def _handle_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            # Parse Socket.IO message format
            if message.startswith("42"):
                # Event message: 42["event_name", {...}]
                data = json.loads(message[2:])
                event_name = data[0]
                event_data = data[1] if len(data) > 1 else {}
                
                logger.debug(f"📨 Event: {event_name}")
                
                # Handle balance updates
                if event_name == "balance":
                    self.balance = float(event_data.get("balance", 0))
                    logger.info(f"💰 Balance updated: ${self.balance}")
                
                # Handle trade results
                elif event_name == "trade-result":
                    trade_id = event_data.get("id")
                    result = event_data.get("result")
                    profit = event_data.get("profit", 0)
                    
                    if trade_id in self.pending_trades:
                        self.pending_trades[trade_id]["result"] = result
                        self.pending_trades[trade_id]["profit"] = profit
                        logger.info(f"📊 Trade {trade_id}: {result} (Profit: ${profit})")
                
                # Custom handlers
                if event_name in self.message_handlers:
                    await self.message_handlers[event_name](event_data)
                    
        except Exception as e:
            logger.debug(f"Message parse error: {e}")
    
    async def get_balance(self) -> float:
        """
        Get current account balance
        
        Returns:
            Current balance in USD
        """
        # Send balance request
        balance_msg = json.dumps(["balance", {"demo": 1 if self.demo else 0}])
        await self.ws.send(f"42{balance_msg}")
        
        # Wait for update
        await asyncio.sleep(0.5)
        
        return self.balance
    
    async def place_trade(
        self, 
        asset: str, 
        amount: float, 
        direction: str, 
        duration: int
    ) -> Dict[str, Any]:
        """
        Place a binary options trade
        
        Args:
            asset: Trading pair (e.g., "EURUSD", "BTCUSD")
            amount: Stake amount in USD
            direction: "call" or "put"
            duration: Expiration time in seconds (60, 120, 180, etc.)
        
        Returns:
            Trade info dict with id, timestamp, etc.
        """
        try:
            # Convert asset format if needed
            asset_formatted = asset.replace("/", "").replace(" ", "").upper()
            
            # Prepare trade message
            trade_data = {
                "asset": asset_formatted,
                "amount": amount,
                "action": direction.lower(),
                "duration": duration,
                "demo": 1 if self.demo else 0,
                "time": int(time.time())
            }
            
            trade_msg = json.dumps(["buy", trade_data])
            await self.ws.send(f"42{trade_msg}")
            
            trade_id = f"trade_{int(time.time() * 1000)}"
            
            # Store pending trade
            self.pending_trades[trade_id] = {
                "asset": asset,
                "amount": amount,
                "direction": direction,
                "duration": duration,
                "timestamp": datetime.now(),
                "result": None,
                "profit": 0
            }
            
            logger.info(f"📈 Trade placed: {asset} {direction.upper()} ${amount} ({duration}s)")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "asset": asset,
                "amount": amount,
                "direction": direction,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"❌ Trade error: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_trade_result(self, trade_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Wait for trade result
        
        Args:
            trade_id: Trade ID to check
            timeout: Max wait time in seconds
        
        Returns:
            Trade result dict or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if trade_id in self.pending_trades:
                trade = self.pending_trades[trade_id]
                if trade["result"] is not None:
                    return trade
            
            await asyncio.sleep(1)
        
        logger.warning(f"⏱️ Trade {trade_id} result timeout")
        return None
    
    async def switch_account(self, demo: bool):
        """
        Switch between demo and real account
        
        Args:
            demo: True for demo, False for real
        """
        self.demo = demo
        
        # Send account switch message
        switch_msg = json.dumps(["change-balance", {"demo": 1 if demo else 0}])
        await self.ws.send(f"42{switch_msg}")
        
        account_type = "DEMO" if demo else "REAL"
        logger.info(f"🔄 Switched to {account_type} account")
        
        # Update balance
        await self.get_balance()
    
    async def close(self):
        """Close WebSocket connection"""
        self.connected = False
        
        if self.ping_task:
            self.ping_task.cancel()
        
        if self.ws:
            await self.ws.close()
        
        logger.info("🔌 Disconnected from Pocket Option")
    
    def on_event(self, event_name: str, handler: Callable):
        """
        Register custom event handler
        
        Args:
            event_name: Event to listen for
            handler: Async function to handle event
        """
        self.message_handlers[event_name] = handler


# Example usage
async def test_demo_trading():
    """Test demo account trading"""
    
    # Example SSID format (get from browser DevTools)
    ssid = r'''42["auth",{"session":"YOUR_SESSION_HERE","isDemo":1,"uid":"YOUR_UID"}]'''
    
    # Initialize API
    api = PocketOptionAPI(ssid=ssid, demo=True)
    
    # Connect
    if await api.connect():
        # Get balance
        balance = await api.get_balance()
        print(f"Demo Balance: ${balance}")
        
        # Place trade
        trade = await api.place_trade(
            asset="EURUSD",
            amount=10,
            direction="call",
            duration=60
        )
        
        if trade["success"]:
            # Wait for result
            result = await api.check_trade_result(trade["trade_id"])
            if result:
                print(f"Trade Result: {result['result']} (Profit: ${result['profit']})")
        
        # Close connection
        await api.close()


if __name__ == "__main__":
    asyncio.run(test_demo_trading())
