import unittest
import os
from dotenv import load_dotenv
from walmart_lib.walmart import WalmartAuthInjector, WalmartClient
import asyncio

load_dotenv()

class TestClient(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        
        base_url = os.getenv("BASE_URL")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        
        auth_injector = WalmartAuthInjector(base_url, client_id, client_secret)
        self.client = WalmartClient(base_url, auth_injector=auth_injector)
        
    async def test_get_all_items(self):
        response = await self.client.get_order('108915114139071')
        self.assertIsNotNone(response)
        
    async def test_get_all_released_orders(self):
        response = await self.client.get_all_released_orders()
        self.assertIsNotNone(response)
        
if __name__ == "__main__":
    unittest.main()