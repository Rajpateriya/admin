from typing import List
from pydantic import BaseModel


class OrderStatusCount(BaseModel):
    status: str
    count: int


class SalesTrendItem(BaseModel):
    date: str  # YYYY-MM-DD
    revenue: float
    orders_count: int


class TopProductItem(BaseModel):
    product_id: str
    title: str
    sku: str
    units_sold: int
    revenue: float


class DashboardOverviewResponse(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    total_customers: int
    total_products: int
    low_stock_products_count: int
    pending_orders_count: int
    orders_by_status: List[OrderStatusCount]
    recent_sales_trend: List[SalesTrendItem]
    top_selling_products: List[TopProductItem]
