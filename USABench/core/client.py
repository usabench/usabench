import os

from litellm import completion


class LLMClient:
    """Unified LLM client using LiteLLM for multiple providers."""

    def __init__(self, model: str = "gpt-4o", **kwargs):
        self.model = model
        self.default_params = {
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "timeout": kwargs.get("timeout", 30)
        }

        # Set up API keys from environment
        self._setup_api_keys()

    def _setup_api_keys(self):
        """Set up API keys for various providers."""
        api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "COHERE_API_KEY": os.getenv("COHERE_API_KEY")
        }

        for key, value in api_keys.items():
            if value:
                os.environ[key] = value

    def generate(
        self,
        messages: list,
        **kwargs
    ) -> str:
        """
        Generate response using LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters to override defaults
        
        Returns:
            str: Generated response content
        """
        # Merge default params with provided kwargs
        params = {**self.default_params, **kwargs}

        try:
            response = completion(
                model=self.model,
                messages=messages,
                **params
            )
            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    def generate_with_system(
        self,
        user_message: str,
        system_message: str,
        **kwargs
    ) -> str:
        """
        Generate response with system and user messages.
        
        Args:
            user_message: User message content
            system_message: System message content
            **kwargs: Additional parameters
            
        Returns:
            str: Generated response content
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        return self.generate(messages, **kwargs)

    def set_model(self, model: str):
        """Change the model for subsequent calls."""
        self.model = model

    def update_defaults(self, **kwargs):
        """Update default parameters."""
        self.default_params.update(kwargs)
