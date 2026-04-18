"""
LLM Client abstraction layer supporting multiple providers.
Supports OpenAI, Groq, and Anthropic with unified interface.
"""

import json
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str = None, **kwargs) -> Dict:
        """Generate structured JSON output."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generate text from a prompt."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2000),
        )
        
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, system_prompt: str = None, **kwargs) -> Dict:
        """Generate structured JSON output."""
        system_prompt = (system_prompt or "") + "\n\nRespond ONLY with valid JSON. No markdown, no explanations."
        
        response_text = self.generate(prompt, system_prompt, **kwargs)
        
        # Try to parse JSON from response
        try:
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_str = "\n".join(lines[1:-1])  # Skip first and last line
            else:
                json_str = response_text
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Fallback: try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON: {e}")


class GroqClient(BaseLLMClient):
    """Groq API client (fast inference)."""
    
    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768"):
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Please install groq: pip install groq")
    
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generate text from a prompt."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2000),
        )
        
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, system_prompt: str = None, **kwargs) -> Dict:
        """Generate structured JSON output."""
        system_prompt = (system_prompt or "") + "\n\nRespond ONLY with valid JSON. No markdown, no explanations."
        
        response_text = self.generate(prompt, system_prompt, **kwargs)
        
        try:
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_str = "\n".join(lines[1:-1])
            else:
                json_str = response_text
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
    
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generate text from a prompt."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 2000),
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        
        return message.content[0].text
    
    def generate_json(self, prompt: str, system_prompt: str = None, **kwargs) -> Dict:
        """Generate structured JSON output."""
        system_prompt = (system_prompt or "") + "\n\nRespond ONLY with valid JSON. No markdown, no explanations."
        
        response_text = self.generate(prompt, system_prompt, **kwargs)
        
        try:
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_str = "\n".join(lines[1:-1])
            else:
                json_str = response_text
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise


def get_llm_client(provider: str, api_key: str, model: str = None) -> BaseLLMClient:
    """
    Factory function to get appropriate LLM client.
    
    Args:
        provider: One of 'openai', 'groq', 'anthropic'
        api_key: API key for the provider
        model: Model name (optional, uses default if not specified)
    
    Returns:
        Configured LLM client instance
    """
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIClient(api_key, model or "gpt-4o-mini")
    elif provider == "groq":
        return GroqClient(api_key, model or "mixtral-8x7b-32768")
    elif provider == "anthropic":
        return AnthropicClient(api_key, model or "claude-3-haiku-20240307")
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai', 'groq', or 'anthropic'.")
