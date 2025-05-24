# /Users/cidiacowalker/Zsoon app/omnilock/client.py
import asyncio
import logging
from typing import Optional, Callable
from bleak import BleakClient, BleakScanner
from .protocol import Command, Status, LockResponse, OmniLockProtocol
from .errors import *

# UUIDs for BLE characteristics
SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # UART service
TX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write characteristic
RX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Notify characteristic

class OmniLock:
    """den här klassen använder vi för att kontakta omnilock."""
    
    def __init__(self, device_uuid: str, pin: str = "1234"):
        self.device_uuid = device_uuid
        self.pin = pin
        self.client = None
        self.is_connected = False
        self.is_authenticated = False
        self._response_event = asyncio.Event()
        self._last_response = None
        self._notification_handlers = []
        self._lock = asyncio.Lock()
        
    async def connect(self, timeout: float = 10.0) -> bool:
        """den här delen connect med låset."""
        if self.is_connected:
            return True
            
        try:
            device = await BleakScanner.find_device_by_address(
                self.device_uuid, 
                timeout=timeout
            )
            if not device:
                raise DeviceNotFoundError(f"Device {self.device_uuid} not found")
                
            self.client = BleakClient(device, disconnected_callback=self._on_disconnect)
            await self.client.connect(timeout=timeout)
            
            # Get UART service and characteristics
            services = await self.client.get_services()
            uart_service = services.get_service(SERVICE_UUID)
            if not uart_service:
                raise ConnectionError("UART service not found")
                
            self.tx_char = uart_service.get_characteristic(TX_CHAR_UUID)
            self.rx_char = uart_service.get_characteristic(RX_CHAR_UUID)
            
            if not self.tx_char or not self.rx_char:
                raise ConnectionError("Required characteristics not found")
                
            # Enable notifications
            await self.client.start_notify(self.rx_char.uuid, self._notification_handler)
            
            self.is_connected = True
            return True
            
        except Exception as e:
            await self.disconnect()
            if not isinstance(e, OmniLockError):
                raise ConnectionError(str(e)) from e
            raise
            
    async def disconnect(self):
        """koppla ifrån låset."""
        if self.client and self.is_connected:
            if hasattr(self, 'rx_char') and self.rx_char:
                await self.client.stop_notify(self.rx_char.uuid)
            await self.client.disconnect()
        self.is_connected = False
        self.is_authenticated = False
        
    async def verify_key(self) -> bool:
        """verifierar pin koden med låset."""
        if not self.is_connected:
            raise ConnectionError("inte kopplad till låset")
            
        try:
            key_bytes = self.pin.encode('ascii')
            if len(key_bytes) != 4:
                raise ValueError("PIN kåden måste vara 4a siffror")
                
            response = await self._send_command(Command.VERIFY_KEY, key_bytes)
            self.is_authenticated = (response.status == Status.SUCCESS)
            return self.is_authenticated
            
        except Exception as e:
            self.is_authenticated = False
            raise AuthenticationError("Key verification failed") from e
            
    async def lock(self) -> bool:
        """Lock the device."""
        return await self._send_operational_command(Command.LOCK)
        
    async def unlock(self) -> bool:
        """Unlock the device."""
        return await self._send_operational_command(Command.UNLOCK)
        
    async def _send_operational_command(self, operation: int) -> bool:
        """Send an operational command (lock/unlock)."""
        if not self.is_authenticated and not await self.verify_key():
            raise AuthenticationError("Not authenticated")
            
        response = await self._send_command(Command.OPERATIONAL, bytes([operation]))
        return response.status == Status.SUCCESS
        
    async def _send_command(self, cmd: int, data: bytes = None, timeout: float = 5.0) -> LockResponse:
        """Send a command to the lock and wait for response."""
        if not self.is_connected:
            raise ConnectionError("Not connected to device")
            
        async with self._lock:
            packet = OmniLockProtocol.build_packet(cmd, data)
            self._response_event.clear()
            
            try:
                await self.client.write_gatt_char(self.tx_char.uuid, packet)
                await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
                return self._last_response
            except asyncio.TimeoutError:
                raise TimeoutError(f"Command {cmd:02X} timed out")
                
    def _notification_handler(self, sender, data: bytearray):
        """Handle incoming notifications from the lock."""
        try:
            response = OmniLockProtocol.parse_packet(data)
            if response:
                self._last_response = response
                self._response_event.set()
                for handler in self._notification_handlers:
                    try:
                        handler(response)
                    except Exception as e:
                        logging.error(f"Error in notification handler: {e}")
        except Exception as e:
            logging.error(f"Error processing notification: {e}")
                        
    def _on_disconnect(self, client):
        """Handle disconnection from the device."""
        self.is_connected = False
        self.is_authenticated = False
        self._response_event.set()