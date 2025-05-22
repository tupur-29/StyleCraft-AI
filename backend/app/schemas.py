from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
import uuid
from datetime import datetime

# --- Base Schemas (Common attributes) ---

class InteractionBase(BaseModel):
    """
    Base schema for prompt interaction attributes.
    """
    query: str = Field(..., min_length=1, description="The user's query or input text.")
    casual_response: Optional[str] = Field(None, description="The AI-generated casual response.")
    formal_response: Optional[str] = Field(None, description="The AI-generated formal response.")
    user_id: str = Field(..., description="Identifier for the user who made the query.")

# --- Schemas for API Requests ---

class InteractionCreateRequest(BaseModel):
    """
    Schema for the request body when creating a new prompt interaction.
    The user_id can be provided, or a default can be used.
    """
    user_id: str = Field(default="default_user", description="User ID, defaults to 'default_user'.")
    query: str = Field(..., min_length=1, description="The user's query or input text.")

class InteractionUpdate(BaseModel):
    """
    Schema for updating an existing prompt interaction.
    All fields are optional; only provided fields will be updated.
    """
    query: Optional[str] = Field(None, min_length=1, description="Updated user query.")
    casual_response: Optional[str] = Field(None, description="Updated AI-generated casual response.")
    formal_response: Optional[str] = Field(None, description="Updated AI-generated formal response.")
    user_id: Optional[str] = Field(None, description="Updated user ID (if changing ownership is allowed).")

    
    model_config = ConfigDict(
        from_attributes=True,  
        extra='ignore'         
    )
    


# --- Schemas for Internal Use (e.g., by CRUD functions) ---

class InteractionCreateInternal(InteractionBase):
    """
    Schema used internally by CRUD functions to create an interaction in the database.
    Inherits all fields from InteractionBase.
    """
    pass 


# --- Schemas for API Responses ---

class InteractionResponse(InteractionBase):
    """
    Schema for representing a prompt interaction in API responses.
    Includes database-generated fields like id and created_at.
    """
    id: uuid.UUID = Field(..., description="Unique identifier for the prompt interaction.")
    created_at: datetime = Field(..., description="Timestamp of when the interaction was created.")

    
    model_config = ConfigDict(
        from_attributes=True,  
        json_encoders={       
            datetime: lambda dt: dt.isoformat()
        }
    )
    


class PaginatedInteractionResponse(BaseModel):
    """
    Schema for a paginated list of interactions.
    """
    total: int
    skip: int
    limit: int
    items: List[InteractionResponse]

    model_config = ConfigDict(from_attributes=True)