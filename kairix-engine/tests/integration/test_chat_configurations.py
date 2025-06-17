import asyncio
import os

import pytest
import requests
from dotenv import load_dotenv

from kairix_engine.engine import KairixEngine


class TestChatConfigurations:
    """Test Chat functionality with different model configurations."""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment based on ENV variable."""
        env_name = os.environ.get("ENV", "mac")
        env_path = f"env/{env_name}.env"
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
        else:
            load_dotenv()

    def check_environment_readiness(self) -> tuple[bool, list[str]]:
        """Check if environment is ready for chat testing."""
        missing = []
        
        required_vars = [
            "KAIRIX_AGENT_CONFIG_SET",
            "NEO4J_URL",
            "KAIRIX_N_SUMMARIES_PER_MESSAGE",
            "KAIRIX_USER_NAME",
            "KAIRIX_PERSONA_NAME",
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        # Check provider-specific requirements
        config_set = os.getenv("KAIRIX_AGENT_CONFIG_SET")
        if config_set == "openai" and not os.getenv("OPENAI_API_KEY"):
            missing.append("OPENAI_API_KEY")
        
        return len(missing) == 0, missing

    @pytest.mark.asyncio
    async def test_basic_chat_interaction(self):
        """Test basic chat interaction with configured models."""
        ready, missing = self.check_environment_readiness()
        if not ready:
            pytest.skip(f"Missing required environment variables: {missing}")
        
        # Get chat instance
        chat = KairixEngine.get_chat_for_environment()
        
        # Initialize chat
        await chat.initialize()
        
        # Test prompts
        test_prompts = [
            "Hello! How are you today?",
            "What's 2 + 2?",
            "Tell me a very short joke.",
            "What's the capital of France?",
            "Goodbye!",
        ]
        
        responses = []
        for prompt in test_prompts:
            print(f"\nUser: {prompt}")
            try:
                response = await chat.chat(prompt)
                truncated = response[:200]
                suffix = '...' if len(response) > 200 else ''
                print(f"Assistant: {truncated}{suffix}")
                
                # Verify we got a non-empty response
                assert response and response.strip(), (
                    f"Empty response for prompt: {prompt}"
                )
                responses.append((prompt, True, response))
                
            except Exception as e:
                print(f"Error: {e}")
                responses.append((prompt, False, str(e)))
        
        # At least 80% of prompts should succeed
        successful = [r for r in responses if r[1]]
        success_rate = len(successful) / len(responses)
        assert success_rate >= 0.8, (
            f"Too many failures. Success rate: {success_rate:.0%}"
        )
        
        print(f"\nSuccess rate: {len(successful)}/{len(responses)}")

    @pytest.mark.asyncio
    async def test_conversation_continuity(self):
        """Test that conversation maintains context."""
        ready, missing = self.check_environment_readiness()
        if not ready:
            pytest.skip(f"Missing required environment variables: {missing}")
        
        chat = KairixEngine.get_chat_for_environment()
        await chat.initialize()
        
        # Test conversation with context
        conversation = [
            ("My name is TestUser and I like pizza.", "greeting"),
            ("What's my name?", "name_recall"),
            ("What food do I like?", "preference_recall"),
            ("Tell me more about that food.", "context_continuation"),
        ]
        
        context_maintained = True
        for prompt, test_type in conversation:
            print(f"\n[{test_type}] User: {prompt}")
            try:
                response = await chat.chat(prompt)
                truncated = response[:200]
                suffix = '...' if len(response) > 200 else ''
                print(f"Assistant: {truncated}{suffix}")
                
                # Basic validation
                assert response and response.strip(), f"Empty response for {test_type}"
                
                # Context-specific validation
                if test_type == "name_recall":
                    # Should mention the name or acknowledge it
                    lower_resp = response.lower()
                    if "testuser" not in lower_resp and "don't know" not in lower_resp:
                        print("Warning: Name not recalled")
                        context_maintained = False
                
                elif test_type == "preference_recall":
                    # Should mention pizza or food preference
                    lower_resp = response.lower()
                    if "pizza" not in lower_resp and "food" not in lower_resp:
                        print("Warning: Food preference not recalled")
                        context_maintained = False
                
            except Exception as e:
                print(f"Error in {test_type}: {e}")
                context_maintained = False
        
        print(f"\nContext maintained: {context_maintained}")

    @pytest.mark.asyncio
    async def test_model_specific_capabilities(self):
        """Test capabilities specific to the configured model."""
        ready, missing = self.check_environment_readiness()
        if not ready:
            pytest.skip(f"Missing required environment variables: {missing}")
        
        config_set = os.getenv("KAIRIX_AGENT_CONFIG_SET")
        print(f"\nTesting model capabilities for: {config_set}")
        
        chat = KairixEngine.get_chat_for_environment()
        await chat.initialize()
        
        # Model-specific test prompts
        capability_tests = {
            "reasoning": (
                "If I have 3 apples and give away 2, then buy 4 more, "
                "how many do I have?"
            ),
            "creativity": "Write a haiku about coding.",
            "instruction_following": "Reply with exactly 5 words only.",
            "knowledge": "What year was Python created?",
        }
        
        results = {}
        for capability, prompt in capability_tests.items():
            print(f"\n[{capability}] {prompt}")
            try:
                response = await chat.chat(prompt)
                truncated = response[:150]
                suffix = '...' if len(response) > 150 else ''
                print(f"Response: {truncated}{suffix}")
                
                # Basic success check
                success = bool(response and response.strip())
                
                # Capability-specific validation
                if capability == "instruction_following" and success:
                    word_count = len(response.strip().split())
                    if word_count == 5:
                        print("✓ Followed instruction correctly")
                    else:
                        print(f"✗ Word count: {word_count} (expected 5)")
                        success = False
                
                results[capability] = success
                
            except Exception as e:
                print(f"Error: {e}")
                results[capability] = False
        
        # Summary
        print(f"\nCapability test results for {config_set}:")
        for cap, success in results.items():
            print(f"  {cap}: {'✓' if success else '✗'}")
        
        # At least basic capabilities should work
        assert results.get("reasoning", False) or results.get("knowledge", False), \
            "Model failed basic capability tests"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test chat error handling with edge cases."""
        ready, missing = self.check_environment_readiness()
        if not ready:
            pytest.skip(f"Missing required environment variables: {missing}")
        
        chat = KairixEngine.get_chat_for_environment()
        await chat.initialize()
        
        # Edge case prompts
        edge_cases = [
            ("", "empty_prompt"),
            (" " * 100, "whitespace_only"),
            ("🎨🎭🎪🎯🎲", "emojis_only"),
            ("a" * 1000, "very_long_single_word"),
            ("Repeat this 100 times: test", "repetition_request"),
        ]
        
        handled_gracefully = 0
        for prompt, case_type in edge_cases:
            print(f"\n[{case_type}] Testing edge case...")
            try:
                response = await chat.chat(prompt)
                if response and response.strip():
                    print(f"✓ Handled gracefully: {response[:100]}...")
                    handled_gracefully += 1
                else:
                    print("✗ Empty response")
                    
            except Exception as e:
                print(f"✗ Exception: {e}")
        
        # Should handle at least some edge cases gracefully
        assert handled_gracefully > 0, "Failed to handle any edge cases gracefully"
        print(f"\nHandled {handled_gracefully}/{len(edge_cases)} edge cases gracefully")

    @pytest.mark.asyncio 
    async def test_concurrent_chats(self):
        """Test multiple concurrent chat sessions."""
        ready, missing = self.check_environment_readiness()
        if not ready:
            pytest.skip(f"Missing required environment variables: {missing}")
        
        print("\nTesting concurrent chat sessions...")
        
        # Create multiple chat instances
        async def chat_session(session_id: int, prompt: str):
            """Run a single chat session."""
            try:
                chat = KairixEngine.get_chat_for_environment()
                await chat.initialize()
                response = await chat.chat(prompt)
                return session_id, True, response[:100]
            except Exception as e:
                return session_id, False, str(e)
        
        # Run concurrent sessions
        prompts = [
            "What's the weather like?",
            "Tell me about Python.",
            "What's 10 + 20?",
            "Describe the color blue.",
            "What's your name?",
        ]
        
        tasks = [
            chat_session(i, prompt) 
            for i, prompt in enumerate(prompts)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful = [r for r in results if r[1]]
        print(f"\nConcurrent sessions: {len(successful)}/{len(results)} succeeded")
        
        for session_id, success, response in results:
            status = "✓" if success else "✗"
            print(f"  Session {session_id}: {status} - {response}")
        
        # At least some concurrent sessions should succeed
        assert len(successful) > 0, "All concurrent sessions failed"

    def test_environment_info(self):
        """Display current environment configuration for debugging."""
        env_name = os.environ.get("ENV", "mac")
        config_set = os.getenv("KAIRIX_AGENT_CONFIG_SET", "not-set")
        
        print(f"\n{'='*50}")
        print("Environment Configuration Summary")
        print(f"{'='*50}")
        print(f"Environment: {env_name}")
        print(f"Agent Config Set: {config_set}")
        print(f"User Name: {os.getenv('KAIRIX_USER_NAME', 'not-set')}")
        print(f"Persona Name: {os.getenv('KAIRIX_PERSONA_NAME', 'not-set')}")
        print(f"Neo4j URL: {'✓' if os.getenv('NEO4J_URL') else '✗'}")
        print(f"OpenAI API Key: {'✓' if os.getenv('OPENAI_API_KEY') else '✗'}")
        n_summaries = os.getenv('KAIRIX_N_SUMMARIES_PER_MESSAGE', 'not-set')
        print(f"Summaries per Message: {n_summaries}")
        
        # Test endpoint connectivity
        print("\nEndpoint Connectivity:")
        
        # Neo4j
        neo4j_url = os.getenv("NEO4J_URL")
        if neo4j_url:
            try:
                from neo4j import GraphDatabase
                driver = GraphDatabase.driver(neo4j_url)
                driver.verify_connectivity()
                driver.close()
                print("  Neo4j: ✓")
            except Exception as e:
                print(f"  Neo4j: ✗ ({e})")
        
        # Model endpoints based on config
        if config_set == "ollama-local":
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=2)
                print(f"  Ollama Local: ✓ ({len(r.json().get('models', []))} models)")
            except Exception:
                print("  Ollama Local: ✗")
                
        elif config_set == "ollama-remote":
            try:
                r = requests.get("https://ollama.kairix.net/api/tags", timeout=5)
                print(f"  Ollama Remote: ✓ ({len(r.json().get('models', []))} models)")
            except Exception:
                print("  Ollama Remote: ✗")
                
        elif config_set == "openai" and os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                client = openai.OpenAI()
                models = list(client.models.list())
                print(f"  OpenAI: ✓ ({len(models)} models)")
            except Exception:
                print("  OpenAI: ✗")
        
        print(f"{'='*50}\n")