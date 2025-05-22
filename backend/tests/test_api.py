import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import uuid


from app.main import app, get_db_session 
from app.database import Base, DATABASE_URL , engine as main_engine
from app import schemas, crud 
from app import ai_core 

# --- Test Database Setup ---
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=main_engine)

# Creating tables for the test session if they don't exist (idempotent)
Base.metadata.create_all(bind=main_engine)

# --- Fixtures ---

@pytest.fixture(scope="function")
def db_session_for_tests() -> Generator[Session, None, None]:
    """
    Provides a transactional database session for tests.
    Rolls back any changes after the test.
    """
    connection = main_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    yield db

    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session_for_tests: Session) -> Generator[TestClient, None, None]:
    """
    Provides a TestClient instance with the database dependency overridden.
    """
    def override_get_db():
        try:
            yield db_session_for_tests
        finally:
            pass 

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db_session] 


@pytest.fixture
def mock_aicore_generate(mocker):
    """Mocks the ai_core.generate_responses function."""
    return mocker.patch('app.ai_core.generate_responses')

# --- Helper to create interaction for tests ---
def create_test_interaction(db: Session, user_id: str, query: str = "Test query",
                            casual: str = "Casual test.", formal: str = "Formal test."):
    interaction_data = schemas.InteractionCreateInternal(
        user_id=user_id,
        query=query,
        casual_response=casual,
        formal_response=formal
    )
    return crud.create_interaction(db=db, interaction=interaction_data)

# --- Test Cases ---

def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Welcome to StyleCraft AI Backend!"}

# --- /generate/ Endpoint Tests ---

def test_handle_generate_request_success(client: TestClient, db_session_for_tests: Session, mock_aicore_generate):
    mock_aicore_generate.return_value = ("Mocked Casual", "Mocked Formal")
    user_id = "testuser123"
    query = "Explain FastAPI testing."
    request_data = {"user_id": user_id, "query": query}

    response = client.post("/generate/", json=request_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user_id"] == user_id
    assert data["query"] == query
    assert data["casual_response"] == "Mocked Casual"
    assert data["formal_response"] == "Mocked Formal"
    assert "id" in data
    assert "created_at" in data

    mock_aicore_generate.assert_called_once_with(query)

    # Verify in DB
    db_interaction = crud.get_interaction(db_session_for_tests, interaction_id=uuid.UUID(data["id"]))
    assert db_interaction is not None
    assert db_interaction.user_id == user_id
    assert db_interaction.query == query


def test_handle_generate_request_aicore_failure_returns_none(client: TestClient, mock_aicore_generate):
    mock_aicore_generate.return_value = (None, None) # Simulating AI core returning no content
    request_data = {"user_id": "testuser", "query": "A query that fails AI."}
    response = client.post("/generate/", json=request_data)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "AI response generation failed" in response.json()["detail"]

def test_handle_generate_request_aicore_exception(client: TestClient, mock_aicore_generate):
    mock_aicore_generate.side_effect = Exception("Simulated AI Core Explosion")
    request_data = {"user_id": "testuser", "query": "A query that breaks AI."}
    response = client.post("/generate/", json=request_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "AI generation error: Simulated AI Core Explosion" in response.json()["detail"]


def test_handle_generate_request_validation_error(client: TestClient):
    response = client.post("/generate/", json={"user_id": "testuser"}) # Missing query
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# --- /interactions/ Endpoint Tests (GET all, GET by user, GET by ID) ---

def test_read_all_interactions_empty(client: TestClient):
    response = client.get("/interactions/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_read_all_interactions_with_data(client: TestClient, db_session_for_tests: Session):
    interaction1 = create_test_interaction(db_session_for_tests, user_id="user1")
    interaction2 = create_test_interaction(db_session_for_tests, user_id="user2", query="Query 2")

    response = client.get("/interactions/?limit=5") # Adding limit to get all
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    
    returned_ids = [item["id"] for item in data]
    assert str(interaction1.id) in returned_ids
    assert str(interaction2.id) in returned_ids


def test_read_interactions_for_user_found(client: TestClient, db_session_for_tests: Session):
    user_id = "specific_user"
    create_test_interaction(db_session_for_tests, user_id="other_user") # decoy
    interaction1 = create_test_interaction(db_session_for_tests, user_id=user_id, query="User query 1")
    interaction2 = create_test_interaction(db_session_for_tests, user_id=user_id, query="User query 2")

    response = client.get(f"/interactions/user/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    for item in data:
        assert item["user_id"] == user_id
    returned_ids = [item["id"] for item in data]
    assert str(interaction1.id) in returned_ids
    assert str(interaction2.id) in returned_ids


def test_read_interactions_for_user_not_found_returns_empty_list(client: TestClient):
    response = client.get("/interactions/user/nonexistent_user")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [] 

def test_read_single_interaction_found(client: TestClient, db_session_for_tests: Session):
    interaction = create_test_interaction(db_session_for_tests, user_id="user_for_single_get")
    response = client.get(f"/interactions/{interaction.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(interaction.id)
    assert data["user_id"] == "user_for_single_get"

def test_read_single_interaction_not_found(client: TestClient):
    non_existent_id = uuid.uuid4()
    response = client.get(f"/interactions/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- /interactions/{interaction_id} (PUT and DELETE) ---

def test_update_existing_interaction_success(client: TestClient, db_session_for_tests: Session):
    interaction = create_test_interaction(db_session_for_tests, user_id="user_to_update", query="Old query")
    update_data = {"query": "Updated query text", "formal_response": "Updated formal response"}

    response = client.put(f"/interactions/{interaction.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(interaction.id)
    assert data["query"] == "Updated query text"
    assert data["formal_response"] == "Updated formal response"
    assert data["casual_response"] == interaction.casual_response 

    # Verify in DB
    db_session_for_tests.refresh(interaction) 
    assert interaction.query == "Updated query text"
    assert interaction.formal_response == "Updated formal response"

def test_update_existing_interaction_partial_success(client: TestClient, db_session_for_tests: Session):
    interaction = create_test_interaction(db_session_for_tests, user_id="user_partial_update", query="Original Q", casual="Original C")
    update_data = {"query": "Partially Updated Query"} 

    response = client.put(f"/interactions/{interaction.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["query"] == "Partially Updated Query"
    assert data["casual_response"] == "Original C" 

    db_session_for_tests.refresh(interaction)
    assert interaction.query == "Partially Updated Query"
    assert interaction.casual_response == "Original C"

def test_update_existing_interaction_not_found(client: TestClient):
    non_existent_id = uuid.uuid4()
    update_data = {"query": "Attempt to update non-existent"}
    response = client.put(f"/interactions/{non_existent_id}", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_existing_interaction_success(client: TestClient, db_session_for_tests: Session):
    interaction = create_test_interaction(db_session_for_tests, user_id="user_to_delete")
    interaction_id = interaction.id

    response = client.delete(f"/interactions/{interaction_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify in DB
    deleted_interaction = crud.get_interaction(db_session_for_tests, interaction_id=interaction_id)
    assert deleted_interaction is None

def test_delete_existing_interaction_not_found(client: TestClient):
    non_existent_id = uuid.uuid4()
    response = client.delete(f"/interactions/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- Pagination tests for /interactions/ ---
def test_read_all_interactions_pagination(client: TestClient, db_session_for_tests: Session):
    user_id = "pagination_user"
    # Creating several interactions
    all_ids = []
    for i in range(15): # Creating 15 interactions
        interaction = create_test_interaction(db_session_for_tests, user_id=user_id, query=f"Page query {i}")
        all_ids.append(str(interaction.id))
    db_session_for_tests.commit() # Commiting to ensure they are queryable in order for this test

    # Test limit
    response_limit_5 = client.get("/interactions/?limit=5")
    assert response_limit_5.status_code == status.HTTP_200_OK
    data_limit_5 = response_limit_5.json()
    assert len(data_limit_5) == 5

    # Test skip and limit
    response_skip_5_limit_5 = client.get("/interactions/?skip=5&limit=5")
    assert response_skip_5_limit_5.status_code == status.HTTP_200_OK
    data_skip_5_limit_5 = response_skip_5_limit_5.json()
    assert len(data_skip_5_limit_5) == 5

    # Ensuring items are different between pages
    ids_page1 = {item["id"] for item in data_limit_5}
    ids_page2 = {item["id"] for item in data_skip_5_limit_5}
    assert len(ids_page1.intersection(ids_page2)) == 0

    # Test retrieving all (or up to default/max limit if not all 15 are fetched by default)
    response_all_default_limit = client.get("/interactions/") 
    assert response_all_default_limit.status_code == status.HTTP_200_OK
    data_all_default_limit = response_all_default_limit.json()
    assert len(data_all_default_limit) == 10 

    # Test retrieving more than default limit
    response_limit_15 = client.get("/interactions/?limit=15")
    assert response_limit_15.status_code == status.HTTP_200_OK
    data_limit_15 = response_limit_15.json()
    assert len(data_limit_15) == 15 
