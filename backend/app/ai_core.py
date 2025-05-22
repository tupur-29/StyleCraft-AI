import os
import time
import logging

# --- Conditional import for 'openai' library ---
try:
    import openai
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    openai = None # Ensuring 'openai' is defined even if import fails
    OPENAI_SDK_AVAILABLE = False
# -----------------------------------------------

logger = logging.getLogger(__name__)

# --- Configuration ---
# Set to False to use Ollama.
# Ensuring Ollama is running and the OLLAMA_MODEL and OLLAMA_BASE_URL are set in .env
USE_MOCK_AI = False  

# --- Ollama Configuration (loaded from environment variables) ---

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:0.5b") 

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama") # Placeholder


ollama_client = None
if OPENAI_SDK_AVAILABLE and not USE_MOCK_AI:
    if not OLLAMA_BASE_URL or not OLLAMA_MODEL:
        logger.error(
            "Ollama configuration (OLLAMA_BASE_URL, OLLAMA_MODEL) is missing. "
            "Ollama integration will not work."
        )
    else:
        try:
            ollama_client = openai.OpenAI(
                base_url=OLLAMA_BASE_URL,
                api_key=OLLAMA_API_KEY, 
            )
            logger.info(f"OpenAI client initialized for Ollama: base_url='{OLLAMA_BASE_URL}', model='{OLLAMA_MODEL}'")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for Ollama: {e}", exc_info=True)
            ollama_client = None # Ensuring it's None if initialization fails
elif not OPENAI_SDK_AVAILABLE and not USE_MOCK_AI:
    logger.error(
        "OpenAI SDK ('openai' library) not installed, but USE_MOCK_AI is False. "
        "Ollama integration requires the 'openai' library. Please install it: pip install openai"
    )

# --- Mock AI Implementation ---
def _query_hf_model_mock(payload_inputs: str, style: str) -> list[dict[str, str]]:
    """
    Mocks an API call for different styles and steps.

    """
    logger.debug(f"MOCK AI: Simulating API call for style '{style}'. Query snippet: '{payload_inputs[:70]}...'")
    time.sleep(0.1)

    response_text = ""
    if style == "casual":
        response_text = f"Hey there! This is a MOCKED CASUAL response to: {payload_inputs}"
    elif style == "formal_generate": # Simulating the first step of formal generation
        response_text = f"This is an initial MOCKED FORMAL generation for '{payload_inputs}'. It is intended to be detailed and academic, ready for a summarization step."
    elif style == "formal_summarize": # Simulating the summarization of a formal text
        words = payload_inputs.split()
        if len(words) > 10: # If the input (detailed formal text) is long enough
            response_text = " ".join(words[:8]) + "... (MOCKED FORMAL SUMMARY)"
        else:
            response_text = payload_inputs + " (MOCKED FORMAL SUMMARY - input was short)"
    else:
        response_text = "Error: Mock AI could not determine the requested style or step."
        logger.error(f"MOCK AI: Unknown style '{style}' requested.")
    return [{"generated_text": response_text}]

# --- Ollama Integration ---
def _query_ollama_model(client: openai.OpenAI | None, model_name: str, query_text: str, style_description: str) -> str | None:
    """
    Helper function to query an Ollama model using the OpenAI-compatible API.
    """
    if client is None:
        logger.error("Ollama client is not initialized. Cannot query Ollama model.")
        return "Error: Ollama client not initialized." # Return error string

    system_prompt = f"You are an AI assistant. Your task is to rephrase the user's input into a {style_description} tone. Provide only the rephrased text, without any preamble or conversational filler."
    logger.debug(f"OLLAMA Query: Style='{style_description}', Model='{model_name}', Prompt='{system_prompt}', UserQuery='{query_text[:70]}...'")

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query_text}
            ],
            max_tokens=250,  
            temperature=0.7  
        )
        response_text = completion.choices[0].message.content.strip()
        logger.info(f"Ollama ({style_description} for model {model_name}) generated: {response_text[:100]}...")
        return response_text
    except openai.APIConnectionError as e:
        logger.error(f"Ollama API Connection Error ({style_description}, model {model_name}): {e}. Is Ollama running at {OLLAMA_BASE_URL}?", exc_info=True)
        return f"Error: Could not connect to Ollama at {OLLAMA_BASE_URL}."
    except openai.APIError as e:
        logger.error(f"Ollama API Error ({style_description}, model {model_name}): {e}", exc_info=True)
        return f"Error: Ollama API returned an error ({e.status_code})." 
    except Exception as e:
        logger.critical(f"Ollama Error: An unexpected error occurred ({style_description}, model {model_name}): {e}", exc_info=True)
        return "Error: An unexpected error occurred with the Ollama model."


def generate_responses(query: str) -> tuple[str | None, str | None]:
    """
    Generates a casual and a formal response for a given query.
    
    """
    if not query:
        logger.warning("generate_responses called with empty query.")
        return "Query was empty.", "Query was empty."

    casual_response_text: str | None = None
    formal_response_text: str | None = None

    if USE_MOCK_AI:
        logger.info("--- Using MOCKED AI Responses ---")
        mock_casual_api_response = _query_hf_model_mock(query, "casual")
        casual_response_text = mock_casual_api_response[0].get("generated_text", "Mock casual error").strip()

        # Mock formal (two steps)
        detailed_formal_mock = _query_hf_model_mock(query, "formal_generate")[0].get("generated_text", "Mock formal generate error")
        formal_response_text = _query_hf_model_mock(detailed_formal_mock, "formal_summarize")[0].get("generated_text", "Mock formal summarize error").strip()

    else: # Real API Path (Ollama)
        logger.info(f"--- Attempting OLLAMA API Call (Model: {OLLAMA_MODEL}) ---")
        if not OPENAI_SDK_AVAILABLE:
            logger.error("Ollama (Real AI) Error: 'openai' SDK is not available.")
            return "Error: OpenAI SDK missing for Ollama.", "Error: OpenAI SDK missing for Ollama."
        if ollama_client is None:
            logger.error("Ollama (Real AI) Error: Ollama client failed to initialize.")
            return "Error: Ollama client not ready.", "Error: Ollama client not ready."

        # Casual Response - Ollama
        casual_response_text = _query_ollama_model(
            client=ollama_client,
            model_name=OLLAMA_MODEL,
            query_text=query,
            style_description="casual, friendly, and engaging"
        )
        if casual_response_text is None or "Error:" in casual_response_text : # Checks if helper returned an error string or None
            logger.error(f"Ollama casual response generation failed. Fallback or error: {casual_response_text}")
            # casual_response_text will retain the error message from _query_ollama_model

        # Formal Response - Ollama
        formal_response_text = _query_ollama_model(
            client=ollama_client,
            model_name=OLLAMA_MODEL,
            query_text=query,
            style_description="strictly formal, professional, and highly articulate"
        )
        if formal_response_text is None or "Error:" in formal_response_text: # Checks if helper returned an error string or None
            logger.error(f"Ollama formal response generation failed. Fallback or error: {formal_response_text}")
            # formal_response_text will retain the error message from _query_ollama_model

    # Ensuring we always return a tuple of two strings, even if they are error messages.
    return (
        casual_response_text if casual_response_text is not None else "Failed to generate casual response.",
        formal_response_text if formal_response_text is not None else "Failed to generate formal response."
    )

# --- Main execution block for direct testing of this file ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info(f"Testing AI Core (USE_MOCK_AI is currently set to: {USE_MOCK_AI})")


    queries_to_test = [
        "What are the main differences between Python 2 and Python 3?",
        "Tell me about climate change.",
        "Explain blockchain technology.",
    ]

    for i, test_query in enumerate(queries_to_test):
        print(f"\n--- Test Query #{i+1} ---")
        casual, formal = generate_responses(test_query)
        print(f"Query: {test_query}")
        print("----- Casual Response -----")
        print(casual)
        print("\n----- Formal Response -----")
        print(formal)
