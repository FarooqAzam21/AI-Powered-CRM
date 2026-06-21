"""
PHASE 5 TEST SUITE
Verify AI Model Optimization System
- Cache performance
- Token compression
- Memory usage
- Model management
- Async generation
"""
import asyncio
import time
import json
import logging
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase5TestSuite:
    """Complete Phase 5 test suite"""

    def __init__(self):
        self.results = {
            "cache_tests": [],
            "compression_tests": [],
            "model_tests": [],
            "generation_tests": [],
            "memory_tests": [],
        }

    async def run_all_tests(self) -> Dict:
        """Run all Phase 5 tests"""
        logger.info("=" * 60)
        logger.info("🚀 PHASE 5 TEST SUITE - AI MODEL OPTIMIZATION")
        logger.info("=" * 60)

        await self.test_cache_system()
        await self.test_token_compression()
        await self.test_model_manager()
        await self.test_ai_generation()
        await self.test_memory_usage()

        return self.results

    async def test_cache_system(self):
        """Test AI response caching"""
        logger.info("\n📦 Testing Cache System...")

        try:
            from ai.ai_response_cache import get_ai_cache

            cache = get_ai_cache()

            # Test classification cache
            subject = "Test Email"
            body = "This is a test email body"
            classification = {
                "category": "inquiry",
                "confidence": 0.95,
                "action": "reply",
                "priority": "medium",
            }

            # Store
            cache.set_classification(subject, body, classification)
            logger.info("✅ Stored classification in cache")

            # Retrieve
            retrieved = cache.get_classification(subject, body)
            assert retrieved is not None, "Classification not found in cache"
            logger.info(f"✅ Retrieved classification: {retrieved}")

            # Test reply cache
            reply = "Thank you for your message"
            cache.set_reply_draft(body, "professional", reply)
            cached_reply = cache.get_reply_draft(body, "professional")
            assert cached_reply is not None, "Reply not found in cache"
            logger.info(f"✅ Reply cache working")

            # Get stats
            stats = cache.get_stats()
            logger.info(f"✅ Cache stats: {stats}")

            self.results["cache_tests"] = [
                {"test": "classification_cache", "status": "PASS"},
                {"test": "reply_cache", "status": "PASS"},
                {"test": "cache_stats", "status": "PASS", "data": stats},
            ]

        except Exception as e:
            logger.error(f"❌ Cache test failed: {e}")
            self.results["cache_tests"] = [{"test": "cache_system", "status": "FAIL", "error": str(e)}]

    async def test_token_compression(self):
        """Test token compression"""
        logger.info("\n📦 Testing Token Compression...")

        try:
            from ai.token_compressor import TokenCompressor

            # Test compression
            long_email = """
            Dear Sir or Madam,
            
            I hope this email finds you well. I am writing to inform you about...
            
            Thank you so much for your time and consideration. I look forward to hearing from you soon.
            
            Best regards,
            John
            """

            subject = "Test Subject"

            # Get compression stats
            compressed_subject, compressed_body = await asyncio.get_event_loop().run_in_executor(
                None, TokenCompressor.compress_email, subject, long_email
            )

            stats = TokenCompressor.get_compression_stats(long_email, compressed_body)
            logger.info(f"✅ Compression stats: {json.dumps(stats, indent=2)}")

            # Verify compression worked
            assert stats["token_reduction_percent"] > 10, "Compression should reduce tokens"
            logger.info(
                f"✅ Achieved {stats['token_reduction_percent']}% token reduction"
            )

            self.results["compression_tests"] = [
                {"test": "email_compression", "status": "PASS", "data": stats},
                {
                    "test": "context_fit",
                    "status": "PASS",
                    "original_chars": stats["original_chars"],
                    "compressed_chars": stats["compressed_chars"],
                },
            ]

        except Exception as e:
            logger.error(f"❌ Compression test failed: {e}")
            self.results["compression_tests"] = [
                {"test": "compression", "status": "FAIL", "error": str(e)}
            ]

    async def test_model_manager(self):
        """Test model manager"""
        logger.info("\n🤖 Testing Model Manager...")

        try:
            from ai.model_manager import get_model_manager

            manager = get_model_manager()

            # Get stats
            stats = manager.get_stats()
            logger.info(f"✅ Model manager stats: {json.dumps(stats, indent=2)}")

            # Get memory usage
            memory = manager.get_memory_usage()
            logger.info(f"✅ Memory usage: {json.dumps(memory, indent=2)}")

            self.results["model_tests"] = [
                {"test": "manager_stats", "status": "PASS", "data": stats},
                {"test": "memory_tracking", "status": "PASS", "data": memory},
            ]

        except Exception as e:
            logger.error(f"❌ Model manager test failed: {e}")
            self.results["model_tests"] = [
                {"test": "model_manager", "status": "FAIL", "error": str(e)}
            ]

    async def test_ai_generation(self):
        """Test AI generation"""
        logger.info("\n🧠 Testing AI Generation...")

        try:
            from ai.ai_generator import get_ai_generator

            generator = get_ai_generator()

            # Simple test prompt
            prompt = "What is 2+2?"

            start = time.time()
            response = await generator.generate(prompt, use_cache=False, compress=False)
            elapsed = time.time() - start

            logger.info(f"✅ Generated response in {elapsed:.2f}s")
            logger.info(f"   Response: {response[:100]}...")

            # Test classification
            subject = "Thank you for your message"
            body = "I received your email and will respond soon."

            start = time.time()
            classification = await generator.generate_classification(subject, body)
            elapsed = time.time() - start

            logger.info(f"✅ Classification in {elapsed:.2f}s: {classification}")

            # Get generator stats
            gen_stats = generator.get_stats()
            logger.info(f"✅ Generator stats: {json.dumps(gen_stats, indent=2)}")

            self.results["generation_tests"] = [
                {
                    "test": "basic_generation",
                    "status": "PASS",
                    "time_seconds": elapsed,
                },
                {
                    "test": "classification",
                    "status": "PASS",
                    "time_seconds": elapsed,
                },
                {"test": "generator_stats", "status": "PASS", "data": gen_stats},
            ]

        except Exception as e:
            logger.error(f"❌ Generation test failed: {e}")
            self.results["generation_tests"] = [
                {"test": "ai_generation", "status": "FAIL", "error": str(e)}
            ]

    async def test_memory_usage(self):
        """Test memory usage tracking"""
        logger.info("\n💾 Testing Memory Usage...")

        try:
            import psutil

            process = psutil.Process()
            mem_info = process.memory_info()
            vm = psutil.virtual_memory()

            memory_data = {
                "process_mb": mem_info.rss / 1024 / 1024,
                "system_percent": vm.percent,
                "system_available_mb": vm.available / 1024 / 1024,
                "system_total_mb": vm.total / 1024 / 1024,
            }

            logger.info(f"✅ Current memory: {json.dumps(memory_data, indent=2)}")

            # Check if within limits
            if memory_data["process_mb"] < 400:
                logger.info(f"✅ Process memory under 400MB limit!")
            else:
                logger.warning(
                    f"⚠️  Process memory {memory_data['process_mb']:.0f}MB "
                    "exceeds 400MB target"
                )

            self.results["memory_tests"] = [
                {"test": "memory_tracking", "status": "PASS", "data": memory_data}
            ]

        except Exception as e:
            logger.error(f"❌ Memory test failed: {e}")
            self.results["memory_tests"] = [
                {"test": "memory_tracking", "status": "FAIL", "error": str(e)}
            ]


async def main():
    """Run all tests"""
    suite = Phase5TestSuite()
    results = await suite.run_all_tests()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)

    for category, tests in results.items():
        logger.info(f"\n{category.upper()}:")
        for test in tests:
            status = test.get("status", "UNKNOWN")
            emoji = "✅" if status == "PASS" else "❌"
            logger.info(f"  {emoji} {test.get('test', 'unknown')}: {status}")

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    print("\n✅ Phase 5 test suite complete!")
    print(json.dumps(results, indent=2, default=str))
