from pydantic import BaseModel
from typing import List, Optional


class TaxAmount(BaseModel):
    currency: str
    amount: float


class Tax(BaseModel):
    taxName: str
    taxAmount: TaxAmount


class ChargeAmount(BaseModel):
    currency: str
    amount: float


class Charge(BaseModel):
    chargeType: str
    chargeName: str
    chargeAmount: ChargeAmount
    tax: Tax


class Charges(BaseModel):
    charge: List[Charge]


class OrderLineQuantity(BaseModel):
    unitOfMeasurement: str
    amount: str


class ShipNode(BaseModel):
    type: str


class PostalAddress(BaseModel):
    name: str
    address1: str
    address2: Optional[str] = None
    city: str
    state: str
    postalCode: str
    country: str
    addressType: str


class ShippingInfo(BaseModel):
    phone: str
    estimatedDeliveryDate: int
    estimatedShipDate: int
    methodCode: str
    postalAddress: PostalAddress


class Item(BaseModel):
    productName: str
    sku: str


class CarrierName(BaseModel):
    carrier: str


class TrackingInfo(BaseModel):
    shipDateTime: int
    carrierName: CarrierName
    methodCode: str
    trackingNumber: str
    trackingURL: str


class StatusQuantity(BaseModel):
    unitOfMeasurement: str
    amount: int


class OrderLineStatus(BaseModel):
    status: str
    statusQuantity: StatusQuantity
    trackingInfo: Optional[TrackingInfo] = None
    subSellerId: Optional[str] = None
    cancellationReason: Optional[str] = None
    returnCenterAddress: Optional[str] = None


class OrderLineStatuses(BaseModel):
    orderLineStatus: List[OrderLineStatus]


class Fulfillment(BaseModel):
    fulfillmentOption: str
    shipMethod: str
    pickUpDateTime: int
    storeId: Optional[str] = None


class WalmartOrderLine(BaseModel):
    lineNumber: str
    item: Item
    charges: Charges
    orderLineQuantity: OrderLineQuantity
    statusDate: int
    orderLineStatuses: OrderLineStatuses
    fulfillment: Fulfillment
    intentToCancel: Optional[str] = None


class OrderLines(BaseModel):
    orderLine: List[WalmartOrderLine]


class WalmartOrder(BaseModel):
    purchaseOrderId: str
    customerOrderId: str
    customerEmailId: str
    orderDate: int
    shippingInfo: ShippingInfo
    orderLines: OrderLines
    shipNode: ShipNode
