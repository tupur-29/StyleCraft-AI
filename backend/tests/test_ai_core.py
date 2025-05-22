import pytest
import os
from unittest import mock # For mock.Mock if needed directly


from app import ai_core

# --- Helper to temporarily set USE_MOCK_AI ---
@pytest.fixture
def mock_ai_env_toggle(monkeypatch):
    """Fixture to control ai_core.USE_MOCK_AI for tests and restore afterwards."""
    original_use_mock_ai = ai_core.USE_MOCK_AI
    def _set_mock_ai(use_mock: bool):
        monkeypatch.setattr(ai_core, "USE_MOCK_AI", use_mock)
        
    yield _set_mock_ai
    monkeypatch.setattr(ai_core, "USE_MOCK_AI", original_use_mock_ai) # Restore

# --- Tests for MOCKED AI Path (USE_MOCK_AI = True) ---

def test_generate_responses_mock_specific_queries(mock_ai_env_toggle):
    mock_ai_env_toggle(True)
    queries_and_expected_keywords = {
        "python 2 and python 3": {
            "casual": "Python 3 is like the cool", "formal_summary_keyword": "python 2 is eol"
        },
        "climate change": {
            "casual": "Earth getting a bit of a fever", "formal_summary_keyword": "mitigation and adaptation are crucial"
        },
        "blockchain": {
            "casual": "super secure digital notebook", "formal_summary_keyword": "supply chain tracking"
        },
    }
    for query, details in queries_and_expected_keywords.items():
        casual_resp, formal_resp = ai_core.generate_responses(query)
        assert details["casual"].lower() in casual_resp.lower(), f"Casual response for '{query}' mismatch"
        assert details["formal_summary_keyword"].lower() in formal_resp.lower(), \
               f"Formal summarized response for '{query}' mismatch. Got: '{formal_resp}'"

def test_generate_responses_mock_generic_query(mock_ai_env_toggle):
    mock_ai_env_toggle(True)
    query = "Tell me about ancient philosophy."
    casual_resp, formal_resp = ai_core.generate_responses(query)
    assert "mocked casual response" in casual_resp.lower()
    assert "mocked summary" in formal_resp.lower()

def test_generate_responses_mock_formal_chaining_logic(mock_ai_env_toggle, mocker):
    mock_ai_env_toggle(True)
    query = "A unique test query for chaining."
    spy_mock_call = mocker.spy(ai_core, "_query_hf_model_mock")
    ai_core.generate_responses(query) 
    assert spy_mock_call.call_count >= 3
    call_args_list = spy_mock_call.call_args_list
    casual_call = next(c for c in call_args_list if c.args[1] == "casual")
    assert casual_call.args[0] == query
    formal_generate_call = next(c for c in call_args_list if c.args[1] == "formal_generate")
    assert formal_generate_call.args[0] == query
    formal_summarize_call = next(c for c in call_args_list if c.args[1] == "formal_summarize")
    assert formal_summarize_call.args[0] != query
    assert "initial mocked formal generation" in formal_summarize_call.args[0].lower()

def test_mock_query_hf_model_mock_unknown_style(mock_ai_env_toggle):
    mock_ai_env_toggle(True)
    response = ai_core._query_hf_model_mock("test query", "unknown_style")
    assert "error: mock ai could not determine" in response[0]["generated_text"].lower()

# --- Fixture for setting up REAL AI Path Logic for generate_responses tests ---
@pytest.fixture
def generate_responses_real_path_logic_setup(mock_ai_env_toggle, mocker):
    """
    Sets USE_MOCK_AI=False and mocks dependencies for generate_responses.
    Yields the mock for _query_hf_model_real.
    """
    mock_ai_env_toggle(False)
    # Mock os.getenv to control HF_API_TOKEN value during the test
    # Default to a valid token for general structure tests
    mocker.patch.object(os, 'getenv', return_value="test_token_123_xyz")
    # Ensuring ai_core.load_dotenv is a callable mock, simulating successful import
    mocker.patch.object(ai_core, 'load_dotenv', mocker.MagicMock())
    
    mocked_core_real_call = mocker.patch('app.ai_core._query_hf_model_real')
    return mocked_core_real_call

def test_generate_responses_real_path_structure(generate_responses_real_path_logic_setup):
    mocked_real_api_call = generate_responses_real_path_logic_setup
    mocked_real_api_call.side_effect = [
        [{"generated_text": "Real casual response."}],
        [{"generated_text": "Real detailed formal text."}],
        [{"generated_text": "Real summarized formal text."}]
    ]
    query = "Test query for real path"
    casual_resp, formal_resp = ai_core.generate_responses(query)
    assert mocked_real_api_call.call_count == 3
    # ... (detailed assertions for call_args_list as before)
    casual_call_args = mocked_real_api_call.call_args_list[0].args
    assert "casual, friendly" in casual_call_args[2]['inputs'].lower()
    formal_generate_call_args = mocked_real_api_call.call_args_list[1].args
    assert "comprehensive, formal" in formal_generate_call_args[2]['inputs'].lower()
    formal_summarize_call_args = mocked_real_api_call.call_args_list[2].args
    assert "summarize the following formal text" in formal_summarize_call_args[2]['inputs'].lower()
    assert casual_resp == "Real casual response."
    assert formal_resp == "Real summarized formal text."


def test_generate_responses_real_path_no_hf_token(mock_ai_env_toggle, mocker):
    mock_ai_env_toggle(False)
    mocker.patch.object(os, 'getenv', return_value=None) # Simulating missing token
    mocker.patch.object(ai_core, 'load_dotenv', mocker.MagicMock()) # Ensuring load_dotenv is callable

    casual_resp, formal_resp = ai_core.generate_responses("A query")
    assert "error: huggingface_api_token not configured" in casual_resp.lower()
    assert "error: huggingface_api_token not configured" in formal_resp.lower()

def test_generate_responses_real_path_missing_dotenv_module(mock_ai_env_toggle, mocker):
    mock_ai_env_toggle(False)
    mocker.patch.object(os, 'getenv', return_value="fake_token_for_this_test")
    mocker.patch.object(ai_core, 'load_dotenv', None) # Simulating load_dotenv was not imported
    
    casual_resp, formal_resp = ai_core.generate_responses("A query")
    assert "error: missing dotenv for api config" in casual_resp.lower()
    assert "error: missing dotenv for api config" in formal_resp.lower()

# --- Fixture for testing _query_hf_model_real internals ---
@pytest.fixture
def mock_aicore_requests_module_for_query_real(mocker, mock_ai_env_toggle):
    mock_ai_env_toggle(False)
    mocked_requests = mocker.patch('app.ai_core.requests')
    
    mocked_requests.exceptions = mock.MagicMock()
    # Defining a basic TimeoutException for testing
    mocked_requests.exceptions.Timeout = type('TimeoutFromMock', (IOError,), {})

    # Defining a RequestException that can take a 'response' kwarg
    def init_request_exception(self, message="Mock Request Exception", response=None):
        super(type(self), self).__init__(message)
        self.response = response
        self.message = message # Storing message for str(e)

    RequestExceptionFromMock = type(
        'RequestExceptionFromMock', (Exception,), {'__init__': init_request_exception}
    )
    mocked_requests.exceptions.RequestException = RequestExceptionFromMock
    return mocked_requests

def test_query_hf_model_real_success(mock_aicore_requests_module_for_query_real):
    mock_requests = mock_aicore_requests_module_for_query_real
    mock_response = mock.Mock()
    mock_response.json.return_value = [{"generated_text": "Successful API response"}]
    mock_response.raise_for_status = mock.Mock()
    mock_requests.post.return_value = mock_response

    result = ai_core._query_hf_model_real("url", {}, {"inputs": "test"})
    mock_requests.post.assert_called_once_with("url", headers={}, json={"inputs": "test"}, timeout=45)
    assert result == [{"generated_text": "Successful API response"}]

def test_query_hf_model_real_timeout(mock_aicore_requests_module_for_query_real):
    mock_requests = mock_aicore_requests_module_for_query_real
    mock_requests.post.side_effect = mock_requests.exceptions.Timeout("Fake Timeout")
    result = ai_core._query_hf_model_real("url", {}, {})
    assert "error: request to hugging face model timed out" in result[0]["generated_text"].lower()

def test_query_hf_model_real_request_exception_json_error(mock_aicore_requests_module_for_query_real):
    mock_requests = mock_aicore_requests_module_for_query_real
    mock_http_error_resp = mock.Mock()
    mock_http_error_resp.json.return_value = {"error": "Model is loading", "estimated_time": 20.5}
    # Simulating requests.post raising RequestException with a response object
    mock_requests.post.side_effect = mock_requests.exceptions.RequestException(
        response=mock_http_error_resp
    )
    result = ai_core._query_hf_model_real("url", {}, {})
    assert "error: model is loading" in result[0]["generated_text"].lower()
    assert "est. 20s" in result[0]["generated_text"].lower()

def test_query_hf_model_real_request_exception_non_json_error(mock_aicore_requests_module_for_query_real):
    mock_requests = mock_aicore_requests_module_for_query_real
    mock_http_error_resp = mock.Mock()
    mock_http_error_resp.json.side_effect = ValueError("No JSON")
    mock_http_error_resp.status_code = 503
    mock_http_error_resp.text = "Service Unavailable Text"
    mock_requests.post.side_effect = mock_requests.exceptions.RequestException(
        response=mock_http_error_resp
    )
    result = ai_core._query_hf_model_real("url", {}, {})
    assert "error: raw error response (status 503): service unavailable text" in result[0]["generated_text"].lower()

def test_query_hf_model_real_request_exception_no_response_attr(mock_aicore_requests_module_for_query_real):
    mock_requests = mock_aicore_requests_module_for_query_real
    exception_message = "Network error, no response object given"
    # Instantiating with response=None (default for our mock exception)
    exception_instance = mock_requests.exceptions.RequestException(exception_message)
    assert exception_instance.response is None # Verify our mock exception's behavior
    mock_requests.post.side_effect = exception_instance

    result = ai_core._query_hf_model_real("url", {}, {})

    assert f"error: {exception_message}".lower() in result[0]["generated_text"].lower()


def test_query_hf_model_real_generic_exception(mock_aicore_requests_module_for_query_real):
    mock_requests = mock_aicore_requests_module_for_query_real
    mock_requests.post.side_effect = Exception("Something totally unexpected")
    result = ai_core._query_hf_model_real("url", {}, {})
    assert "error: an unexpected error occurred with the ai model" in result[0]["generated_text"].lower()

def test_query_hf_model_real_missing_requests_module_in_aicore(mocker, mock_ai_env_toggle):
    mock_ai_env_toggle(False)
    mocker.patch.object(ai_core, 'requests', None) # Simulate requests module itself is None
    result = ai_core._query_hf_model_real("url", {}, {})
    assert "error: 'requests' library missing for api call" in result[0]["generated_text"].lower()



