from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product, ProductStatus, ProductVariant
from app.repositories.audit_repository import AuditRepository
from app.repositories.brand_repository import BrandRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.category import BrandCreate, BrandResponse, BrandUpdate, CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.utils.helpers import slugify


class CatalogService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.category_repo = CategoryRepository(db)
        self.brand_repo = BrandRepository(db)
        self.product_repo = ProductRepository(db)
        self.audit_repo = AuditRepository(db)

    # ------------------ CATEGORY OPERATIONS ------------------
    async def create_category(self, data: CategoryCreate, actor: Dict[str, Any]) -> CategoryResponse:
        slug = data.slug or slugify(data.name)
        existing = await self.category_repo.get_by_slug(slug)
        if existing:
            raise ConflictException(f"Category slug '{slug}' already in use.")

        if data.parent_id:
            parent = await self.category_repo.get_by_id(data.parent_id)
            if not parent:
                raise NotFoundException("Parent Category", data.parent_id)

        category = Category(
            name=data.name,
            slug=slug,
            description=data.description,
            parent_id=data.parent_id,
            image_url=data.image_url,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        created = await self.category_repo.create(category)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CREATE_CATEGORY",
            resource_type="category",
            resource_id=str(created.id),
            details={"name": created.name, "slug": created.slug},
        )
        return CategoryResponse(**created.model_dump(by_alias=False))

    async def update_category(self, category_id: str, data: CategoryUpdate, actor: Dict[str, Any]) -> CategoryResponse:
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundException("Category", category_id)

        patch = data.model_dump(exclude_unset=True)
        if "slug" in patch and patch["slug"]:
            slug = slugify(patch["slug"])
            existing = await self.category_repo.get_by_slug(slug)
            if existing and str(existing.id) != category_id:
                raise ConflictException(f"Category slug '{slug}' already exists.")
            patch["slug"] = slug

        if "parent_id" in patch and patch["parent_id"]:
            if patch["parent_id"] == category_id:
                raise BadRequestException("Category cannot be its own parent.")
            parent = await self.category_repo.get_by_id(patch["parent_id"])
            if not parent:
                raise NotFoundException("Parent Category", patch["parent_id"])

        updated = await self.category_repo.update(category_id, patch)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_CATEGORY",
            resource_type="category",
            resource_id=category_id,
            details=patch,
        )
        return CategoryResponse(**updated.model_dump(by_alias=False))

    async def delete_category(self, category_id: str, actor: Dict[str, Any]) -> None:
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundException("Category", category_id)

        # Check if has subcategories
        has_children = await self.category_repo.exists({"parent_id": category_id})
        if has_children:
            raise BadRequestException("Cannot delete category with nested subcategories. Reassign or delete children first.")

        # Check if products exist in category
        has_products = await self.product_repo.exists({"category_id": category_id})
        if has_products:
            raise BadRequestException("Cannot delete category with associated products. Reassign products first.")

        await self.category_repo.delete(category_id)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="DELETE_CATEGORY",
            resource_type="category",
            resource_id=category_id,
            details={"name": category.name},
        )

    async def get_category_tree(self) -> List[Dict[str, Any]]:
        return await self.category_repo.get_tree()

    async def list_categories(self, is_active: Optional[bool] = None) -> List[CategoryResponse]:
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        cats = await self.category_repo.find_many(query, limit=500, sort=[("sort_order", 1)])
        return [CategoryResponse(**c.model_dump(by_alias=False)) for c in cats]

    # ------------------ BRAND OPERATIONS ------------------
    async def create_brand(self, data: BrandCreate, actor: Dict[str, Any]) -> BrandResponse:
        slug = data.slug or slugify(data.name)
        existing = await self.brand_repo.get_by_slug(slug)
        if existing:
            raise ConflictException(f"Brand slug '{slug}' already exists.")

        brand = Brand(
            name=data.name,
            slug=slug,
            description=data.description,
            logo_url=data.logo_url,
            website=data.website,
            is_active=data.is_active,
        )
        created = await self.brand_repo.create(brand)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CREATE_BRAND",
            resource_type="brand",
            resource_id=str(created.id),
            details={"name": created.name, "slug": created.slug},
        )
        return BrandResponse(**created.model_dump(by_alias=False))

    async def update_brand(self, brand_id: str, data: BrandUpdate, actor: Dict[str, Any]) -> BrandResponse:
        brand = await self.brand_repo.get_by_id(brand_id)
        if not brand:
            raise NotFoundException("Brand", brand_id)

        patch = data.model_dump(exclude_unset=True)
        if "slug" in patch and patch["slug"]:
            slug = slugify(patch["slug"])
            existing = await self.brand_repo.get_by_slug(slug)
            if existing and str(existing.id) != brand_id:
                raise ConflictException(f"Brand slug '{slug}' already in use.")
            patch["slug"] = slug

        updated = await self.brand_repo.update(brand_id, patch)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_BRAND",
            resource_type="brand",
            resource_id=brand_id,
            details=patch,
        )
        return BrandResponse(**updated.model_dump(by_alias=False))

    async def delete_brand(self, brand_id: str, actor: Dict[str, Any]) -> None:
        brand = await self.brand_repo.get_by_id(brand_id)
        if not brand:
            raise NotFoundException("Brand", brand_id)

        await self.brand_repo.delete(brand_id)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="DELETE_BRAND",
            resource_type="brand",
            resource_id=brand_id,
            details={"name": brand.name},
        )

    async def list_brands(self, is_active: Optional[bool] = None) -> List[BrandResponse]:
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        brands = await self.brand_repo.find_many(query, limit=500, sort=[("name", 1)])
        return [BrandResponse(**b.model_dump(by_alias=False)) for b in brands]

    # ------------------ PRODUCT OPERATIONS ------------------
    async def create_product(self, data: ProductCreate, actor: Dict[str, Any]) -> ProductResponse:
        # Check SKU uniqueness
        sku = data.sku.strip().upper()
        existing_sku = await self.product_repo.get_by_sku(sku)
        if existing_sku:
            raise ConflictException(f"Product SKU '{sku}' is already registered.")

        # Check Slug uniqueness
        slug = data.slug or slugify(data.title)
        existing_slug = await self.product_repo.get_by_slug(slug)
        if existing_slug:
            slug = f"{slug}-{str(ObjectId())[:6]}"

        # Process variants
        processed_variants: List[ProductVariant] = []
        total_variant_stock = 0
        for v in data.variants:
            v_id = v.id or str(ObjectId())
            v_sku = v.sku.strip().upper()
            processed_variants.append(
                ProductVariant(
                    id=v_id,
                    title=v.title,
                    sku=v_sku,
                    barcode=v.barcode,
                    price=v.price,
                    compare_at_price=v.compare_at_price,
                    cost_price=v.cost_price,
                    stock_quantity=v.stock_quantity,
                    attributes=v.attributes,
                    image_url=v.image_url,
                )
            )
            total_variant_stock += v.stock_quantity

        # If variants are defined, total stock can be governed by variants
        final_stock = total_variant_stock if processed_variants else data.stock_quantity

        product = Product(
            title=data.title,
            slug=slug,
            description=data.description,
            short_description=data.short_description,
            status=data.status,
            sku=sku,
            barcode=data.barcode,
            base_price=data.base_price,
            compare_at_price=data.compare_at_price,
            cost_price=data.cost_price,
            stock_quantity=final_stock,
            low_stock_threshold=data.low_stock_threshold,
            category_id=data.category_id,
            brand_id=data.brand_id,
            tags=data.tags,
            images=data.images,
            variants=processed_variants,
            is_featured=data.is_featured,
            weight_kg=data.weight_kg,
            metadata=data.metadata,
        )
        created = await self.product_repo.create(product)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CREATE_PRODUCT",
            resource_type="product",
            resource_id=str(created.id),
            details={"title": created.title, "sku": created.sku, "price": created.base_price},
        )
        return ProductResponse(**created.model_dump(by_alias=False))

    async def update_product(self, product_id: str, data: ProductUpdate, actor: Dict[str, Any]) -> ProductResponse:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Product", product_id)

        patch = data.model_dump(exclude_unset=True)

        if "sku" in patch and patch["sku"]:
            sku = patch["sku"].strip().upper()
            existing_sku = await self.product_repo.get_by_sku(sku)
            if existing_sku and str(existing_sku.id) != product_id:
                raise ConflictException(f"Product SKU '{sku}' is already in use.")
            patch["sku"] = sku

        if "slug" in patch and patch["slug"]:
            slug = slugify(patch["slug"])
            existing_slug = await self.product_repo.get_by_slug(slug)
            if existing_slug and str(existing_slug.id) != product_id:
                raise ConflictException(f"Product slug '{slug}' is already in use.")
            patch["slug"] = slug

        if "variants" in patch and patch["variants"]:
            processed_variants = []
            variant_stock_sum = 0
            for v in patch["variants"]:
                v_dict = v if isinstance(v, dict) else v.model_dump()
                if not v_dict.get("id"):
                    v_dict["id"] = str(ObjectId())
                processed_variants.append(v_dict)
                variant_stock_sum += v_dict.get("stock_quantity", 0)
            patch["variants"] = processed_variants
            if "stock_quantity" not in patch:
                patch["stock_quantity"] = variant_stock_sum

        updated = await self.product_repo.update(product_id, patch)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_PRODUCT",
            resource_type="product",
            resource_id=product_id,
            details=patch,
        )
        return ProductResponse(**updated.model_dump(by_alias=False))

    async def delete_product(self, product_id: str, actor: Dict[str, Any]) -> None:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Product", product_id)

        await self.product_repo.delete(product_id)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="DELETE_PRODUCT",
            resource_type="product",
            resource_id=product_id,
            details={"title": product.title, "sku": product.sku},
        )

    async def get_product_by_id(self, product_id: str) -> ProductResponse:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Product", product_id)
        return ProductResponse(**product.model_dump(by_alias=False))

    async def search_products(
        self,
        q: Optional[str] = None,
        category_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        status: Optional[ProductStatus] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> Tuple[List[ProductResponse], int]:
        products, total = await self.product_repo.search_products(
            q=q,
            category_id=category_id,
            brand_id=brand_id,
            status=status,
            min_price=min_price,
            max_price=max_price,
            is_featured=is_featured,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        responses = [ProductResponse(**p.model_dump(by_alias=False)) for p in products]
        return responses, total

    async def bulk_update_status(
        self,
        product_ids: List[str],
        status: ProductStatus,
        actor: Dict[str, Any],
    ) -> int:
        modified_count = await self.product_repo.bulk_update_status(product_ids, status)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="BULK_UPDATE_PRODUCT_STATUS",
            resource_type="product",
            details={"product_ids": product_ids, "status": status.value, "modified_count": modified_count},
        )
        return modified_count
