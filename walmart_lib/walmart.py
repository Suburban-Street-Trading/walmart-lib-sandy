import time
import httpx
import json
from pydantic import BaseModel
from typing import Any, List, Optional
import asyncio
from functools import wraps
import base64
import uuid
import os

from walmart_lib.order import WalmartOrder


class BulkPriceUpdate(BaseModel):
    # Define the fields according to the JSON structure
    pass


class BulkPriceUpdateResponse(BaseModel):
    # Define the fields according to the JSON structure
    pass


class BulkInventoryUpdate(BaseModel):
    # Define the fields according to the JSON structure
    pass


class BulkInventoryUpdateResponse(BaseModel):
    # Define the fields according to the JSON structure
    pass

class ItemPrice(BaseModel):
    currency: str
    amount: str

class Item(BaseModel):
    mart: str
    sku: str
    condition: str
    wpid: str
    upc: str
    gtin: str
    productName: str
    shelf: str
    productType: str
    price: ItemPrice
    publishedStatus: str
    unpublishedReasons: Any
    variantGroupId: Any
    variantGroupInfo: Any
    lifecycleStatus: str

class OrderShipment(BaseModel):
    # Define the fields according to the JSON structure
    pass


class AllItemsResponse(BaseModel):
    itemResponse: List[Item]
    nextCursor: Optional[str]

class AllReleasedOrdersResponse(BaseModel):
    
    class ResponseList(BaseModel):
        
        class Meta(BaseModel):
            totalCount: int
            limit: int
            nextCursor: Optional[str]
    
        class Elements(BaseModel):
            order: List[WalmartOrder]
        
        meta: Meta
        elements: Elements
    
    list: ResponseList


class SingleOrderResponse(BaseModel):
    order: WalmartOrder


class WalmartClientException(Exception):
    def __init__(self, message, status_code, error_body):
        super().__init__(message)
        self.status_code = status_code
        self.error_body = error_body


class WalmartAuthInjector:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_expires_at = None
        self.access_token = None

    async def inject_auth_headers(self, request):
        if self.token_needs_refresh():
            await self.refresh_access_token()
        request.headers['WM_QOS.CORRELATION_ID'] = str(uuid.uuid4())
        request.headers['WM_SVC.NAME'] = 'automation-backend'
        request.headers['WM_SEC.ACCESS_TOKEN'] = self.access_token
        return request

    def token_needs_refresh(self):
        return self.token_expires_at is None or self.access_token is None or self.token_expires_at <= int(time.time())

    async def refresh_access_token(self):
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v3/token",
                params={"grant_type": "client_credentials"},
                headers={
                    "Authorization": f"Basic {auth}",
                    "Accept": "application/json",
                    "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
                    "WM_SVC.NAME": "automation-backend",
                },
            )
            response_data = response.json()
            self.access_token = response_data['access_token']
            self.token_expires_at = int(time.time()) + response_data['expires_in'] - 30  # subtract 30 seconds for clock skew


def retry_on_error(retries=5, delay=1):
    def retry_decorator(f):
        @wraps(f)
        async def wrapped(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return await f(*args, **kwargs)
                except WalmartClientException as e:
                    if 400 <= e.status_code < 500:
                        raise
                    await asyncio.sleep(delay * (2 ** attempt))
            raise
        return wrapped
    return retry_decorator


class WalmartClient:
    def __init__(self, base_url, auth_injector):
        self.base_url = base_url
        self.auth_injector = auth_injector

    @retry_on_error(retries=20, delay=5)
    async def bulk_update_price(self, update: BulkPriceUpdate) -> BulkPriceUpdateResponse:
        endpoint = "/v3/feeds"
        file_path = "price_updates.json"
        with open(file_path, 'w') as f:
            f.write(update.json())
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            request = client.build_request("POST", f"{self.base_url}{endpoint}", headers=headers)
            request = await self.auth_injector.inject_auth_headers(request)
            with open(file_path, 'rb') as f:
                request.content = f.read()
            response = await client.send(request)
        os.remove(file_path)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while updating price", response.status_code, error_body)
        return BulkPriceUpdateResponse.model_validate_json(response.text)

    @retry_on_error(retries=20, delay=5)
    async def bulk_update_inventory(self, update: BulkInventoryUpdate) -> BulkInventoryUpdateResponse:
        endpoint = "/v3/feeds"
        file_path = "inventory_updates.json"
        with open(file_path, 'w') as f:
            f.write(update.json())
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            request = client.build_request("POST", f"{self.base_url}{endpoint}", headers=headers)
            request = await self.auth_injector.inject_auth_headers(request)
            with open(file_path, 'rb') as f:
                request.content = f.read()
            response = await client.send(request)
        os.remove(file_path)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while updating inventory", response.status_code, error_body)
        return BulkInventoryUpdateResponse.model_validate_json(response.text)

    async def get_all_items(self) -> List[Item]:
        items = []
        cursor = ""
        while True:
            response = await self.get_item_list_page(cursor)
            items.extend(response.itemResponse)
            if response.nextCursor:
                cursor = response.nextCursor
            else:
                break
        return items

    async def get_item_list_page(self, cursor: str) -> AllItemsResponse:
        endpoint = "/v3/items"
        async with httpx.AsyncClient() as client:
            params = {"limit": "200", "nextCursor": cursor or "*"}
            request = client.build_request("GET", f"{self.base_url}{endpoint}", params=params)
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        return AllItemsResponse.model_validate_json(response.text)

    @retry_on_error(retries=20, delay=5)
    async def ship_order(self, purchase_order_id: str, order_shipment: OrderShipment) -> WalmartOrder:
        endpoint = f"/v3/order/{purchase_order_id}/shipping"
        async with httpx.AsyncClient() as client:
            request = client.build_request("GET", f"{self.base_url}{endpoint}", headers={"Accept": "application/json"})
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while shipping order", response.status_code, error_body)
        return WalmartOrder.model_validate_json(response.text)

    @retry_on_error(retries=20, delay=5)
    async def get_all_released_orders(self) -> List[WalmartOrder]:
        endpoint = "/v3/orders/released"
        async with httpx.AsyncClient() as client:
            request = client.build_request("GET", f"{self.base_url}{endpoint}", headers={"Accept": "application/json"})
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while fetching orders", response.status_code, error_body)
        return AllReleasedOrdersResponse.model_validate_json(response.text).orders

    @retry_on_error(retries=20, delay=5)
    async def get_order(self, purchase_order_id: str) -> SingleOrderResponse:
        endpoint = f"/v3/orders/{purchase_order_id}"
        async with httpx.AsyncClient() as client:
            request = client.build_request("GET", f"{self.base_url}{endpoint}", headers={"Accept": "application/json"})
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while fetching order", response.status_code, error_body)
        return SingleOrderResponse.model_validate_json(response.text)

    @retry_on_error(retries=20, delay=5)
    async def acknowledge_order(self, purchase_order_id: str) -> str:
        endpoint = f"/v3/orders/{purchase_order_id}/acknowledge"
        async with httpx.AsyncClient() as client:
            request = client.build_request("POST", f"{self.base_url}{endpoint}", headers={"Accept": "application/json"})
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while acknowledging order", response.status_code, error_body)
        return response.text


    async def process_return_refund(self, purchase_order_id: str, return_data: dict) -> str:
        """
        Process returns and refunds for Walmart orders.

        Args:
            purchase_order_id (str): The purchase order ID for which return/refund is to be processed.
            return_data (dict): Data containing information about the return/refund request.

        Returns:
            str: Confirmation message or status of the return/refund processing.
        """
        endpoint = f"/v3/orders/{purchase_order_id}/return-refund"
        async with httpx.AsyncClient() as client:
            request = client.build_request("POST", f"{self.base_url}{endpoint}", json=return_data)
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while processing return/refund", response.status_code, error_body)
        return response.text

    async def manage_product_listing(self, product_data: dict, action: str) -> str:
        """
        Manage product listings on Walmart Marketplace.

        Args:
            product_data (dict): Data containing information about the product listing.
            action (str): Action to perform - 'add', 'update', or 'remove'.

        Returns:
            str: Confirmation message or status of the product listing management.
        """
        if action not in ['add', 'update', 'remove']:
            raise ValueError("Invalid action. Allowed actions are 'add', 'update', or 'remove'.")
        
        endpoint = "/v3/products"
        if action == 'update':
            endpoint += f"/{product_data['sku']}"

        async with httpx.AsyncClient() as client:
            method = "POST" if action != 'update' else "PUT"
            request = client.build_request(method, f"{self.base_url}{endpoint}", json=product_data)
            request = await self.auth_injector.inject_auth_headers(request)
            response = await client.send(request)
        
        if response.status_code >= 400:
            error_body = response.text
            raise WalmartClientException("Error while managing product listing", response.status_code, error_body)
        return response.text