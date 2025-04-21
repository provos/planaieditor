import traceback
from typing import List

# Attempt to import PlanAI components. Handle gracefully if not found initially.
from planai import llm_from_config


def list_models_for_provider(provider_name: str) -> List[str]:
    """
    Attempts to list available models for a given PlanAI provider.

    Note: This function attempts to instantiate the LLM interface.
    If the provider requires API keys (like OpenAI, Anthropic), these must be
    present in the environment where this code runs (e.g., the backend server's env).
    Listing might fail if keys are missing for required providers.

    Args:
        provider_name: The name of the provider (e.g., 'ollama', 'openai').

    Returns:
        A list of model names.

    Raises:
        Exception: For other unexpected errors during listing.
    """
    llm = None
    if not llm_from_config:
        raise ValueError(
            "llm_from_config function not found. PlanAI might be missing or outdated."
        )

    llm = None
    try:
        # Instantiate with minimal, non-key args where possible.
        # llm_from_config will handle key checks internally.
        # We need a placeholder model_name for some providers during init.
        placeholder_model = "placeholder-model-for-listing"
        if provider_name == "ollama" or provider_name == "remote_ollama":
            # Ollama might not strictly need a model name upfront for listing, depends on implementation
            # Let's try without one first if llm_from_config allows default/None
            try:
                llm = llm_from_config(provider=provider_name, use_cache=False)
            except TypeError:  # If model_name is required
                llm = llm_from_config(
                    provider=provider_name,
                    model_name=placeholder_model,
                    use_cache=False,
                )
        elif provider_name in ["openai", "anthropic", "gemini", "openrouter"]:
            # These likely require keys, llm_from_config will raise ValueError if missing
            llm = llm_from_config(
                provider=provider_name, model_name=placeholder_model, use_cache=False
            )
        else:
            raise ValueError(f"Unsupported provider for model listing: {provider_name}")

        if not llm or not hasattr(llm, "list"):
            raise ValueError(
                f"Could not instantiate or find list method for provider: {provider_name}"
            )

        list_response = llm.list()

        if list_response and hasattr(list_response, "models") and list_response.models:
            # Ensure model attribute exists and is not None before adding
            return [
                item.model
                for item in list_response.models
                if hasattr(item, "model") and item.model is not None
            ]
        else:
            print(
                f"No models found or unexpected response format for provider {provider_name}."
            )
            return []

    except ValueError as ve:
        # Re-raise ValueErrors (likely missing keys or invalid provider)
        raise ve
    except Exception as e:
        print(f"Error listing models for provider {provider_name}: {e}")
        traceback.print_exc()  # Log the full traceback for debugging
        # Raise a more generic exception for other errors
        raise Exception(
            f"Failed to list models for {provider_name} due to an internal error."
        ) from e
