from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from pydantic import BaseModel

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """base class for all repositories providing common crud operations"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get_by_id(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """get a record by id"""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """get all records with optional filtering"""
        query = select(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType, **extra_data) -> ModelType:
        """create a new record"""
        obj_in_data = obj_in.dict(exclude_unset=True)
        obj_in_data.update(extra_data)
        
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: ModelType, 
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """update a record"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: Any) -> bool:
        """delete a record by id"""
        query = delete(self.model).where(self.model.id == id)
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
