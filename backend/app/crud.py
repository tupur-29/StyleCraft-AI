from sqlalchemy.orm import Session
from typing import Optional, List 
import uuid


from . import database as db_module
from . import schemas

def get_interaction(db: Session, interaction_id: uuid.UUID) -> Optional[db_module.PromptInteraction]:
    """
    Retrieves a single prompt interaction by its ID.
    """
    return db.query(db_module.PromptInteraction).filter(db_module.PromptInteraction.id == interaction_id).first()

def get_interactions(db: Session, skip: int = 0, limit: int = 100) -> List[db_module.PromptInteraction]:
    """
    Retrieves a list of prompt interactions, with pagination.
    Orders by creation date descending (newest first).
    """
    return db.query(db_module.PromptInteraction).order_by(db_module.PromptInteraction.created_at.desc()).offset(skip).limit(limit).all()

def get_interactions_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[db_module.PromptInteraction]:
    """
    Retrieves a list of prompt interactions for a specific user, with pagination.
    Orders by creation date descending.
    """
    return db.query(db_module.PromptInteraction).filter(db_module.PromptInteraction.user_id == user_id).order_by(db_module.PromptInteraction.created_at.desc()).offset(skip).limit(limit).all()

def create_interaction(db: Session, interaction: schemas.InteractionCreateInternal) -> db_module.PromptInteraction:
    """
    Creates a new prompt interaction in the database.
    """
    db_interaction_instance = db_module.PromptInteraction(
        user_id=interaction.user_id,
        query=interaction.query,
        casual_response=interaction.casual_response,
        formal_response=interaction.formal_response
    )
    db.add(db_interaction_instance)
    db.commit()
    db.refresh(db_interaction_instance)
    return db_interaction_instance

def update_interaction(
    db: Session, 
    interaction_id: uuid.UUID, 
    interaction_update: schemas.InteractionUpdate
) -> Optional[db_module.PromptInteraction]:
    """
    Updates an existing prompt interaction.
    Only fields present in interaction_update will be changed.
    """
    db_interaction = get_interaction(db, interaction_id=interaction_id)
    if db_interaction:
        # Get data from Pydantic model, excluding unset fields to only update provided values
        update_data = interaction_update.model_dump(exclude_unset=True)
        
        
        for key, value in update_data.items():
            setattr(db_interaction, key, value)
        
        db.commit()
        db.refresh(db_interaction)
    return db_interaction

def delete_interaction(db: Session, interaction_id: uuid.UUID) -> Optional[db_module.PromptInteraction]:
    """
    Deletes a prompt interaction by its ID.
    Returns the deleted interaction object, or None if not found.
    """
    db_interaction = get_interaction(db, interaction_id=interaction_id)
    if db_interaction:
        db.delete(db_interaction)
        db.commit()
    return db_interaction # Returns the object that was deleted (now detached from session) or None
