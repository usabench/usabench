"""Production LiteLLM client integration for USABench."""

from dataclasses import dataclass
import logging
import time
from typing import Any, Dict, List, Optional, Union

try:
    import litellm
    from litellm import acompletion, completion
except ImportError:
    raise ImportError("litellm is required. Install with: pip install litellm")

logger = logging.getLogger(__name__)

@dataclass
class ModelResponse:
    """Response from a model evaluation."""
    content: str
    model: str
    usage: Dict[str, int]
    execution_time_ms: float
    error: Optional[str] = None
    traces: Optional[Dict] = None

@dataclass
class EvaluationPrompt:
    """Structured prompt for evaluation."""
    system_message: str
    user_message: str
    context: Optional[str] = None

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to OpenAI message format."""
        messages = [
            {"role": "system", "content": self.system_message}
        ]

        if self.context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{self.context}\n\nQuery:\n{self.user_message}"
            })
        else:
            messages.append({"role": "user", "content": self.user_message})

        return messages

class ProductionLLMClient:
    """Production LiteLLM client for USABench."""

    def __init__(self,
                 default_model: str = "gpt-4o",
                 temperature: float = 0.0,
                 max_tokens: int = 500,
                 timeout: float = 30.0):
        """Initialize production LiteLLM client."""
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # Track usage
        self.total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }

    def generate(self,
                 prompt: Union[str, EvaluationPrompt],
                 model: Optional[str] = None,
                 **kwargs) -> ModelResponse:
        """Generate response from model."""
        model = model or self.default_model
        start_time = time.time()

        try:
            # Prepare messages
            if isinstance(prompt, str):
                messages = [{"role": "user", "content": prompt}]
            elif isinstance(prompt, EvaluationPrompt):
                messages = prompt.to_messages()
            else:
                messages = [{"role": "user", "content": str(prompt)}]

            # Prepare parameters
            params = {
                "model": model,
                "messages": messages,
                "timeout": kwargs.get("timeout", self.timeout),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature)
            }

            logger.debug(f"Calling {model} with {len(messages)} messages")

            # Make API call
            response = completion(**params)

            execution_time = (time.time() - start_time) * 1000

            # Extract content
            content = response.choices[0].message.content

            # Track usage
            usage = response.usage.model_dump() if hasattr(response.usage, 'model_dump') else response.usage.__dict__
            self._update_usage(usage)

            return ModelResponse(
                content=content,
                model=model,
                usage=usage,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Error with {model}: {e}")

            return ModelResponse(
                content="",
                model=model,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                execution_time_ms=execution_time,
                error=str(e)
            )

    def _update_usage(self, usage: Dict[str, Any]):
        """Update usage statistics."""
        self.total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        self.total_usage["total_tokens"] += usage.get("total_tokens", 0)
