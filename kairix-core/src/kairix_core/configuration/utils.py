from kairix_core.configuration.types import ProviderName


def model_for_provider(provider_name: ProviderName, model: str)->str:
    if provider_name == "openai":
        return model
    return f"{provider_name}/{model}"
