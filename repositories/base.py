"""
Base Repository
Provides common database operations with tenant isolation
"""

from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with tenant-aware CRUD operations.

    All queries are automatically filtered by tenant_id to ensure
    multi-tenant data isolation.
    """

    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def _get_base_query(self, tenant_id: Optional[str] = None):
        """Get base query with optional tenant filter"""
        query = self.db.query(self.model)
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.filter(self.model.tenant_id == tenant_id)
        return query

    def get_all(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """Get all records with pagination and filters"""
        query = self._get_base_query(tenant_id)

        # Apply additional filters
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        return query.offset(skip).limit(limit).all()

    def get_by_id(
        self,
        id: int,
        tenant_id: Optional[str] = None
    ) -> Optional[ModelType]:
        """Get single record by primary key ID"""
        query = self._get_base_query(tenant_id)
        return query.filter(self.model.id == id).first()

    def get_count(
        self,
        tenant_id: Optional[str] = None,
        **filters
    ) -> int:
        """Get total count of records"""
        query = self._get_base_query(tenant_id)

        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        return query.count()

    def create(self, obj_data: dict, tenant_id: Optional[str] = None) -> ModelType:
        """Create a new record"""
        if tenant_id and hasattr(self.model, 'tenant_id'):
            obj_data['tenant_id'] = tenant_id

        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(
        self,
        id: int,
        obj_data: dict,
        tenant_id: Optional[str] = None
    ) -> Optional[ModelType]:
        """Update an existing record"""
        db_obj = self.get_by_id(id, tenant_id)
        if not db_obj:
            return None

        for key, value in obj_data.items():
            if hasattr(db_obj, key) and value is not None:
                setattr(db_obj, key, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int, tenant_id: Optional[str] = None) -> bool:
        """Delete a record (hard delete)"""
        db_obj = self.get_by_id(id, tenant_id)
        if not db_obj:
            return False

        self.db.delete(db_obj)
        self.db.commit()
        return True

    def soft_delete(
        self,
        id: int,
        tenant_id: Optional[str] = None
    ) -> Optional[ModelType]:
        """Soft delete by setting status to inactive/deleted"""
        db_obj = self.get_by_id(id, tenant_id)
        if not db_obj:
            return None

        if hasattr(db_obj, 'status'):
            db_obj.status = 'deleted'
        elif hasattr(db_obj, 'is_active'):
            db_obj.is_active = False

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def exists(self, id: int, tenant_id: Optional[str] = None) -> bool:
        """Check if record exists"""
        query = self._get_base_query(tenant_id)
        return query.filter(self.model.id == id).first() is not None

    def bulk_create(
        self,
        objects_data: List[dict],
        tenant_id: Optional[str] = None
    ) -> List[ModelType]:
        """Create multiple records"""
        db_objects = []
        for obj_data in objects_data:
            if tenant_id and hasattr(self.model, 'tenant_id'):
                obj_data['tenant_id'] = tenant_id
            db_objects.append(self.model(**obj_data))

        self.db.add_all(db_objects)
        self.db.commit()
        for obj in db_objects:
            self.db.refresh(obj)
        return db_objects
