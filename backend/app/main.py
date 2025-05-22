from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional 
import uuid 
import logging


from . import crud, schemas, database, ai_core

app = FastAPI(
    title="StyleCraft AI Backend",
    description="API for StyleCraft AI to generate styled responses and manage interactions.",
    version="0.1.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Session Dependency ---
def get_db_session():
    """
    Dependency to get a new database session for each request.
    Ensures the session is closed after the request is finished.
    """
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Application Lifecycle Events ---
@app.on_event("startup")
async def on_startup():
    """
    Actions to perform when the application starts up.
    Currently, it attempts to create database tables.
    """
    logger.info("Application startup: attempting to create DB tables if they don't exist.")
    try:
        database.create_db_tables()
        logger.info("Database tables checked/created successfully on startup.")
    except Exception as e:
        logger.error(f"CRITICAL: Error creating database tables during startup: {e}", exc_info=True)
        

# --- API Endpoints ---

@app.get("/", summary="Root Endpoint", description="A simple welcome message for the API.")
async def root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to StyleCraft AI Backend!"}

@app.post(
    "/generate/",
    response_model=schemas.InteractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Styled Responses and Create Interaction",
    description="Takes a user query, generates casual and formal responses using AI, and saves the interaction."
)
async def handle_generate_request(
    request: schemas.InteractionCreateRequest,
    db: Session = Depends(get_db_session)
):
    """
    - **request**: Contains `user_id` and `query`.
    - Generates AI responses.
    - Creates and stores a new `PromptInteraction` record.
    - Returns the created interaction.
    """
    logger.info(f"POST /generate/ - User: '{request.user_id}', Query: '{request.query[:50]}...'")
    try:
        casual_resp, formal_resp = ai_core.generate_responses(request.query)
        if casual_resp is None and formal_resp is None:
            logger.error("AI core failed to generate any response for query.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI response generation failed or returned no content."
            )
    except HTTPException as http_exc: 
        raise http_exc
    except Exception as e:
        logger.error(f"Error during AI response generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation error: {str(e)}"
        )

    interaction_to_create = schemas.InteractionCreateInternal(
        user_id=request.user_id,
        query=request.query,
        casual_response=casual_resp,
        formal_response=formal_resp
    )
    
    try:
        db_interaction = crud.create_interaction(db=db, interaction=interaction_to_create)
        logger.info(f"Successfully created interaction ID: {db_interaction.id}")
        return db_interaction
    except Exception as e:
        logger.error(f"Error saving interaction to database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while saving interaction: {str(e)}"
        )

@app.get(
    "/interactions/",
    response_model=List[schemas.InteractionResponse], 
    summary="List All Interactions",
    description="Retrieves a list of all prompt interactions with pagination."
)
async def read_all_interactions(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
    db: Session = Depends(get_db_session)
):
    """
    Retrieves a paginated list of all interactions.
    """
    logger.info(f"GET /interactions/ - Skip: {skip}, Limit: {limit}")
    try:
        interactions = crud.get_interactions(db, skip=skip, limit=limit)
        return interactions
    except Exception as e:
        logger.error(f"Error fetching all interactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching interactions: {str(e)}"
        )

@app.get(
    "/interactions/user/{user_id}",
    response_model=List[schemas.InteractionResponse],
    summary="List Interactions by User ID",
    description="Retrieves a list of prompt interactions for a specific user with pagination."
)
async def read_interactions_for_user(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
    db: Session = Depends(get_db_session)
):
    """
    Retrieves a paginated list of interactions for a given `user_id`.
    """
    logger.info(f"GET /interactions/user/{user_id} - Skip: {skip}, Limit: {limit}")
    try:
        interactions = crud.get_interactions_by_user(db, user_id=user_id, skip=skip, limit=limit)
        if not interactions:
            logger.info(f"No interactions found for user_id: {user_id}")
            
        return interactions
    except Exception as e:
        logger.error(f"Error fetching interactions for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching interactions for user: {str(e)}"
        )


@app.get(
    "/interactions/{interaction_id}",
    response_model=schemas.InteractionResponse,
    summary="Get Specific Interaction",
    description="Retrieves a single prompt interaction by its unique ID."
)
async def read_single_interaction(
    interaction_id: uuid.UUID, 
    db: Session = Depends(get_db_session)
):
    """
    Retrieves a specific interaction by its `interaction_id`.
    Returns 404 if not found.
    """
    logger.info(f"GET /interactions/{interaction_id}")
    db_interaction = crud.get_interaction(db, interaction_id=interaction_id)
    if db_interaction is None:
        logger.warning(f"Interaction with ID {interaction_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    return db_interaction

@app.put(
    "/interactions/{interaction_id}",
    response_model=schemas.InteractionResponse,
    summary="Update Interaction",
    description="Updates an existing prompt interaction by its ID. Only provided fields are updated."
)
async def update_existing_interaction(
    interaction_id: uuid.UUID,
    interaction_update: schemas.InteractionUpdate,
    db: Session = Depends(get_db_session)
):
    """
    Updates an interaction specified by `interaction_id`.
    - **interaction_update**: Pydantic model containing fields to update.
    Returns the updated interaction or 404 if not found.
    """
    logger.info(f"PUT /interactions/{interaction_id} - Data: {interaction_update.model_dump(exclude_unset=True)}")
    db_interaction = crud.update_interaction(db, interaction_id=interaction_id, interaction_update=interaction_update)
    if db_interaction is None:
        logger.warning(f"Attempted to update non-existent interaction ID: {interaction_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found for update")
    logger.info(f"Successfully updated interaction ID: {interaction_id}")
    return db_interaction

@app.delete(
    "/interactions/{interaction_id}",
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Delete Interaction",
    description="Deletes a prompt interaction by its ID."
)
async def delete_existing_interaction(
    interaction_id: uuid.UUID,
    db: Session = Depends(get_db_session)
):
    """
    Deletes an interaction specified by `interaction_id`.
    Returns 204 No Content on success, or 404 if not found.
    """
    logger.info(f"DELETE /interactions/{interaction_id}")
    db_interaction = crud.delete_interaction(db, interaction_id=interaction_id)
    if db_interaction is None: 
        logger.warning(f"Attempted to delete non-existent interaction ID: {interaction_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found for deletion")
    logger.info(f"Successfully deleted interaction ID: {interaction_id}")

    return None 
